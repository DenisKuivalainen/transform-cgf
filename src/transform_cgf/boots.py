"""Inflating male boot meshes so they sit outside the old body.

The leg counterpart of :mod:`transform_cgf.gloves`: boots authored against
the slimmer patch-5.x legs clip through the old body's calves and feet, so
each boot vertex is pushed out along its normal, fading in as the vertex
gets close to the leg.  The shared arithmetic lives in
:mod:`transform_cgf.inflation`.
"""

from __future__ import annotations

from .chunks import SkeletonChunks
from .inflation import inflate_near_bones
from .reskin.deform import ReskinDeformer

__all__ = ["inflate_boots", "LEG_BONES", "MAX_INFLATION_DISTANCE"]

#: Bones whose weight marks a vertex as part of the lower leg and foot.
LEG_BONES = (
    "Bip01 L Calf",
    "Bip01 R Calf",
    "Bip01 L Foot",
    "Bip01 R Foot",
    "Bip01 L Toe0",
    "Bip01 R Toe0",
)

#: Beyond this distance from the leg surface, no inflation is applied.
MAX_INFLATION_DISTANCE = 10.0


def inflate_boots(
    chunks: SkeletonChunks,
    deformer: ReskinDeformer,
    *,
    is_dark: bool,
) -> bool:
    """Push boot vertices outwards along their normals.

    Returns whether anything moved.
    """
    return inflate_near_bones(
        chunks,
        deformer,
        LEG_BONES,
        is_dark=True,
        max_distance=MAX_INFLATION_DISTANCE,
    )
