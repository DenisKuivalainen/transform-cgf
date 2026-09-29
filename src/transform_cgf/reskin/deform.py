"""Deforming the shared patch-5.x body back onto a race-specific old body.

Patch 5.x gave both playable races the same body mesh.  Older clients expect
the Asmodian ("dark") body to be its own shape, so every vertex of a dark
model has to be moved from where it sits on the shared body to where the
equivalent point sat on the old one.

The field that does that is reconstructed from the control points in
:mod:`.profiles`, per bone, as:

* an **anchor** term - if the vertex is close to a seam control point it is
  snapped towards that point's recorded displacement, with influence falling
  off over :data:`ANCHOR_RADIUS`;
* a **neighbourhood** term - otherwise the vertex keeps its offset relative
  to each of the :data:`NEAREST_COUNT` nearest control points, and those
  predictions are blended with a Gaussian weight.

The two are mixed by the anchor's influence, so seams stay exact and the
rest of the surface deforms smoothly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from .profiles import BoneProfile, ControlPoint, ProfileLibrary

__all__ = [
    "VertexBone",
    "ReskinDeformer",
    "ANCHOR_RADIUS",
    "NEAREST_COUNT",
    "SIGMA",
]

#: Distance (world units) over which an anchor's pull falls off to nothing.
ANCHOR_RADIUS = 2.0

#: How many non-anchor control points vote on a vertex's new position.
NEAREST_COUNT = 4

#: Gaussian falloff width for the neighbourhood vote.
SIGMA = 2.0

#: Below this distance a vertex is considered to *be* the anchor.
_COINCIDENT = 1e-4

#: Guard against dividing by a vanishing weight sum.
_WEIGHT_EPSILON = 1e-6

#: How many nearest control points survive the cheap vectorised pass.
#: Comfortably larger than NEAREST_COUNT so the shortlist can never miss a
#: point that would have made the final four.
_SHORTLIST = 32

#: Same idea for anchors, of which only the nearest is ever used.
_ANCHOR_SHORTLIST = 8


@dataclass(frozen=True)
class VertexBone:
    """One entry of a vertex's skin weighting."""

    bone_name: str
    weight: float


@dataclass(frozen=True)
class _LocalPoints:
    """A bone's control points expressed in one (possibly other) bone's frame.

    Transforming every control point into the frame of the bone being
    evaluated does not depend on the vertex, so it is done once per
    (frame bone, source bone) pair and reused for the whole mesh.  This is
    the single change that makes a full-body reskin finish in seconds
    rather than minutes; the arithmetic is unchanged.
    """

    old_local: np.ndarray  # (n, 3)
    new_local: np.ndarray  # (n, 3)
    is_anchor: np.ndarray  # (n,) bool
    # rot.T @ (old_pos - new_pos): the displacement of a coincident anchor,
    # rotated directly rather than via two separate frame changes, which is
    # what keeps a seam vertex landing exactly on its recorded old position.
    direct_offset: np.ndarray  # (n, 3)


class ReskinDeformer:
    """Applies the reskin displacement field for one gender."""

    def __init__(self, profiles: ProfileLibrary) -> None:
        self._profiles = profiles
        self._local_cache: dict[tuple[str, str], _LocalPoints] = {}

    @property
    def profiles(self) -> ProfileLibrary:
        return self._profiles

    def has_profile(self, bone_name: str) -> bool:
        return bone_name in self._profiles

    def anchors_for(self, bone_name: str) -> tuple[ControlPoint, ...]:
        """Anchor control points of ``bone_name``, or empty if it has none."""
        profile = self._profiles.get(bone_name)
        return profile.anchors if profile is not None else ()

    def distance_to_closest_control_point(
        self,
        point: Sequence[float],
        bone_names: Iterable[str],
        is_dark: bool,
    ) -> float:
        """Distance from ``point`` to the nearest control point of any bone.

        Used by the glove inflation to taper off as it approaches skin that
        the reskin already pinned down.  Returns ``inf`` when none of the
        named bones has a profile.
        """
        vertex = np.asarray(point, dtype=float)
        min_dist = float("inf")

        for bone_name in bone_names:
            profile = self._profiles.get(bone_name)
            if profile is None:
                continue

            for cp in profile.control_points:
                control_pos = np.asarray(cp.reference(is_dark), dtype=float)
                dist = np.linalg.norm(vertex - control_pos)
                if dist < min_dist:
                    min_dist = dist

        return min_dist

    def transform_vertex(
        self,
        vertex_pos: Sequence[float],
        bones: Sequence[VertexBone],
    ) -> list[float]:
        """Return ``vertex_pos`` displaced onto the old body.

        Bones with no profile or a non-positive weight take no part.  If
        that leaves nothing, the vertex is returned unchanged - it belongs
        to a region the reskin has no information about (the head, say).
        """
        vertex = np.asarray(vertex_pos, dtype=float)

        contributing = [
            bone
            for bone in bones
            if bone.weight > 0.0 and bone.bone_name in self._profiles
        ]
        if not contributing:
            return list(vertex_pos)

        source_names = [bone.bone_name for bone in contributing]
        if not any(self._profiles[name].control_points for name in source_names):
            return list(vertex_pos)

        total_offset = np.zeros(3, dtype=float)
        for bone in contributing:
            offset = self._bone_offset(
                vertex, self._profiles[bone.bone_name], source_names
            )
            total_offset += offset * bone.weight

        return (vertex + total_offset).tolist()

    # -- internals ------------------------------------------------------

    def _locals(self, frame: BoneProfile, source_name: str) -> _LocalPoints:
        """``source_name``'s control points in ``frame``'s local space."""
        key = (frame.bone_name, source_name)
        cached = self._local_cache.get(key)
        if cached is not None:
            return cached

        rot = frame.rotation
        bone_pos = frame.position
        points = self._profiles[source_name].control_points

        if points:
            old = np.asarray([cp.old_pos for cp in points], dtype=float)
            new = np.asarray([cp.new_pos for cp in points], dtype=float)
            old_local = (old - bone_pos) @ rot
            new_local = (new - bone_pos) @ rot
            direct_offset = (old - new) @ rot
            flags = np.asarray([cp.is_anchor for cp in points], dtype=bool)
        else:  # pragma: no cover - a profile with no points is malformed data
            old_local = np.zeros((0, 3))
            new_local = np.zeros((0, 3))
            direct_offset = np.zeros((0, 3))
            flags = np.zeros(0, dtype=bool)

        local = _LocalPoints(
            old_local=old_local,
            new_local=new_local,
            is_anchor=flags,
            direct_offset=direct_offset,
        )
        self._local_cache[key] = local
        return local

    def _bone_offset(
        self,
        vertex_world: np.ndarray,
        profile: BoneProfile,
        source_names: Sequence[str],
    ) -> np.ndarray:
        """This bone's contribution to the vertex displacement."""
        rot = profile.rotation
        vertex_local = rot.T @ (vertex_world - profile.position)

        old_local, new_local, is_anchor, direct_offset = self._gather(
            profile, source_names
        )
        if len(new_local) == 0:  # pragma: no cover - guarded by the caller
            return np.zeros(3)

        distances, order = self._rank(new_local, is_anchor, vertex_local)

        anchor_slot = next((i for i in order if is_anchor[i]), None)

        anchor_k, anchor_local_offset = self._anchor_term(
            anchor_slot, distances, direct_offset, old_local, new_local
        )

        neighbours = [i for i in order if i != anchor_slot][:NEAREST_COUNT]
        offset_local = self._neighbourhood_term(
            neighbours, distances, old_local, new_local, vertex_local
        )

        return rot @ (anchor_local_offset * anchor_k + offset_local * (1.0 - anchor_k))

    @staticmethod
    def _rank(
        new_local: np.ndarray,
        is_anchor: np.ndarray,
        vertex_local: np.ndarray,
    ) -> tuple[np.ndarray, list[int]]:
        """Order the control points by distance, nearest first.

        Only a handful of points can possibly matter - one anchor and
        :data:`NEAREST_COUNT` neighbours - so this narrows the field with a
        cheap vectorised pass and then measures just the survivors exactly.

        The two passes are not interchangeable: a whole-array norm and a
        single-vector norm take different code paths inside NumPy and can
        disagree in the last bit or two.  Those last bits reach the output
        through the Gaussian weights, so the numbers that are *used* all come
        from the scalar path, and the vectorised pass only ever decides which
        points are worth measuring - a decision no plausible rounding can
        change, given the shortlist is several times larger than it needs
        to be.
        """
        deltas = new_local - vertex_local
        approx = np.linalg.norm(deltas, axis=1)
        count = len(approx)

        shortlist: set[int] = set(_smallest(approx, _SHORTLIST))

        anchor_indices = np.flatnonzero(is_anchor)
        if anchor_indices.size:
            nearest_anchors = _smallest(approx[anchor_indices], _ANCHOR_SHORTLIST)
            shortlist.update(int(anchor_indices[i]) for i in nearest_anchors)

        distances = approx.copy()
        for i in shortlist:
            distances[i] = np.linalg.norm(deltas[i])

        # Sorting the ascending index list with a distance-only key reproduces
        # the original's stable "sort every candidate in table order" tie-break.
        order = sorted(sorted(shortlist), key=lambda i: distances[i])
        return distances, order

    def _gather(
        self, profile: BoneProfile, source_names: Sequence[str]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """All source bones' control points in ``profile``'s frame."""
        if len(source_names) == 1:
            local = self._locals(profile, source_names[0])
            return (
                local.old_local,
                local.new_local,
                local.is_anchor,
                local.direct_offset,
            )

        parts = [self._locals(profile, name) for name in source_names]
        return (
            np.concatenate([p.old_local for p in parts]),
            np.concatenate([p.new_local for p in parts]),
            np.concatenate([p.is_anchor for p in parts]),
            np.concatenate([p.direct_offset for p in parts]),
        )

    @staticmethod
    def _anchor_term(
        anchor_slot: int | None,
        distances: np.ndarray,
        direct_offset: np.ndarray,
        old_local: np.ndarray,
        new_local: np.ndarray,
    ) -> tuple[float, np.ndarray]:
        """Influence and displacement of the nearest seam anchor."""
        if anchor_slot is None:
            return 0.0, np.zeros(3)

        anchor_dist = float(distances[anchor_slot])

        if anchor_dist < _COINCIDENT:
            # The vertex *is* the anchor: take its recorded displacement whole.
            return 1.0, direct_offset[anchor_slot]

        anchor_dist = min(anchor_dist, ANCHOR_RADIUS)
        offset = old_local[anchor_slot] - new_local[anchor_slot]
        influence = (ANCHOR_RADIUS - anchor_dist) ** 1.5 / ANCHOR_RADIUS
        return influence, offset

    @staticmethod
    def _neighbourhood_term(
        neighbours: Sequence[int],
        distances: np.ndarray,
        old_local: np.ndarray,
        new_local: np.ndarray,
        vertex_local: np.ndarray,
    ) -> np.ndarray:
        """Gaussian-weighted blend of the nearest control points' predictions."""
        if not neighbours:  # pragma: no cover - needs a single-point profile
            return np.zeros(3)

        idx = np.asarray(neighbours, dtype=int)

        # Each neighbour predicts "the vertex keeps its offset relative to me".
        predictions = old_local[idx] + (vertex_local - new_local[idx])

        # Scalar exp, deliberately: NumPy's vectorised exp can differ from the
        # scalar one in the last bit, and there are only four values here.
        weights = np.asarray(
            [np.exp(-0.5 * (float(distances[i]) / SIGMA) ** 2) for i in neighbours]
        )
        weight_sum = weights.sum()
        if weight_sum < _WEIGHT_EPSILON:
            weights = np.ones(len(idx)) / len(idx)
        else:
            weights = weights / weight_sum

        # Accumulated in a loop rather than as a matrix product: for four
        # terms the two differ in the last bit, and this is the arithmetic
        # the shipped assets were generated with.
        predicted_local = np.zeros(3)
        for weight, prediction in zip(weights, predictions):
            predicted_local += weight * prediction

        return predicted_local - vertex_local


def _smallest(values: np.ndarray, count: int) -> list[int]:
    """Indices of the ``count`` smallest entries of ``values``, unordered."""
    if values.size <= count:
        return list(range(values.size))
    return [int(i) for i in np.argpartition(values, count)[:count]]
