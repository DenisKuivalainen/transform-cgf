"""Inflating male glove meshes so they sit outside the old body.

Patch 5.x slimmed the male arms down.  Gloves and sleeves authored against
that slimmer arm, worn on the beefier old body, clip straight through it -
skin pokes out through the leather.

The fix is to push each glove vertex out along its own normal, by an amount
that fades in as the vertex gets close to the arm.  Two details keep it from
doing damage:

* **Skin meshes are left alone.**  A mesh that shares vertices with the
  reference body's forearm anchors *is* skin, not a glove, so it is skipped.
* **Seams are welded.**  Vertices that coincide are moved identically, so
  splitting a vertex for UV or smoothing reasons cannot open a crack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pyffi.formats.cgf import CgfFormat

from .chunks import SkeletonChunks
from .reskin.deform import ReskinDeformer

__all__ = ["inflate_gloves", "ARM_BONES", "EPSILON", "MAX_INFLATION_DISTANCE"]

#: Two positions within this distance are treated as the same point.
EPSILON = 1e-2

#: Bones whose weight marks a vertex as part of the arm.
ARM_BONES = (
    "Bip01 L Forearm",
    "Bip01 R Forearm",
    "Bip01 L UpperArm",
    "Bip01 R UpperArm",
)

#: Bones whose anchors identify a mesh as bare skin rather than a glove.
_SKIN_MARKER_BONES = ("Bip01 L Forearm", "Bip01 R Forearm")

#: Beyond this distance from the arm surface, no inflation is applied.
MAX_INFLATION_DISTANCE = 15.0

#: Vertices at or above this height are head/torso and are left alone.
MAX_INFLATION_HEIGHT = 130.0

#: Reciprocal of the falloff distance, kept as its own factor so the
#: multiplication order matches the arithmetic the shipped assets were
#: generated with.
_INFLATION_SCALE = 1.0 / MAX_INFLATION_DISTANCE


@dataclass
class _Moved:
    """One vertex position before and after inflation."""

    before: CgfFormat.Vector3
    after: CgfFormat.Vector3


def _is_at(position: CgfFormat.Vector3, anchors: Iterable[tuple]) -> bool:
    return any(
        abs(position.x - x) <= EPSILON
        and abs(position.y - y) <= EPSILON
        and abs(position.z - z) <= EPSILON
        for x, y, z in anchors
    )


def _skin_anchor_positions(deformer: ReskinDeformer, is_dark: bool) -> list[tuple]:
    return [
        cp.reference(is_dark)
        for bone in _SKIN_MARKER_BONES
        for cp in deformer.anchors_for(bone)
    ]


def inflate_gloves(
    chunks: SkeletonChunks,
    deformer: ReskinDeformer,
    *,
    is_dark: bool,
) -> bool:
    """Push glove vertices outwards along their normals.

    Returns whether anything moved, so a caller (or a test) can tell an
    inflated glove from a skipped skin mesh.
    """
    anchors = _skin_anchor_positions(deformer, is_dark)

    # A single shared vertex is enough: reference-body geometry means skin.
    if any(_is_at(vertex.p, anchors) for vertex in chunks.vertices):
        return False

    names = chunks.names
    moved: list[_Moved] = []
    changed = False

    for index, vertex in enumerate(chunks.vertices):
        already = next(
            (m for m in moved if (vertex.p - m.before).norm() <= EPSILON),
            None,
        )
        if already is not None:
            vertex.p = already.after
            continue

        before = vertex.p

        if vertex.p.z < MAX_INFLATION_HEIGHT:
            arm_weight = sum(
                link.blending if names[link.bone] in ARM_BONES else 0
                for link in chunks.vertex_weights[index].bone_links
            )
            distance = deformer.distance_to_closest_control_point(
                (vertex.p.x, vertex.p.y, vertex.p.z), ARM_BONES, is_dark
            )
            # Full push at the surface, tapering linearly to nothing at
            # MAX_INFLATION_DISTANCE away from it.
            vertex.p += (
                vertex.n
                * arm_weight
                * (MAX_INFLATION_DISTANCE - min(distance, MAX_INFLATION_DISTANCE))
                * _INFLATION_SCALE
            )
            changed = changed or arm_weight != 0

        moved.append(_Moved(before=before, after=vertex.p))

    return changed
