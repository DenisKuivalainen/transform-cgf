"""Pushing clothing vertices out along their normals, near a set of bones.

Shared by the glove and boot inflation: both fix clothing authored against a
slimmer patch-5.x limb that clips through the beefier old body.  Each vertex
is pushed along its own normal by an amount that is full at the limb surface
and fades to nothing ``max_distance`` away from it, scaled by how much of the
vertex is weighted to the limb's bones.

Coinciding vertices are moved identically, so splitting a vertex for UV or
smoothing reasons cannot open a crack in the seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from pyffi.formats.cgf import CgfFormat

from .chunks import SkeletonChunks
from .reskin.deform import ReskinDeformer

__all__ = ["inflate_near_bones", "EPSILON"]

#: Two positions within this distance are treated as the same point.
EPSILON = 1e-2


@dataclass
class _Moved:
    """One vertex position before and after inflation."""

    before: CgfFormat.Vector3
    after: CgfFormat.Vector3


def inflate_near_bones(
    chunks: SkeletonChunks,
    deformer: ReskinDeformer,
    bones: Sequence[str],
    *,
    is_dark: bool,
    max_distance: float,
    max_height: Optional[float] = None,
) -> bool:
    """Push vertices weighted to ``bones`` outwards along their normals.

    Vertices at or above ``max_height`` (when given) are left alone.
    Returns whether anything moved.
    """
    # Reciprocal kept as its own factor so the multiplication order matches
    # the arithmetic the shipped assets were generated with.
    scale = 1.0 / max_distance

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

        if max_height is None or vertex.p.z < max_height:
            weight = sum(
                link.blending if names[link.bone] in bones else 0
                for link in chunks.vertex_weights[index].bone_links
            )
            distance = deformer.distance_to_closest_control_point(
                (vertex.p.x, vertex.p.y, vertex.p.z),
                bones,
                is_dark,
            )
            # Full push at the surface, tapering linearly to nothing at
            # max_distance away from it.
            vertex.p += (
                vertex.n
                * weight
                * (max_distance - min(distance, max_distance))
                * scale
            )
            changed = changed or weight != 0

        moved.append(_Moved(before=before, after=vertex.p))

    return changed
