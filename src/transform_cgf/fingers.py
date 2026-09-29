"""Retargeting the five-finger patch-5.x hand onto the three-finger old hand.

This runs *before* the bone table is rebuilt, while all ten chains still
exist, and it does two things at once:

1. moves and re-orients every finger bone into a pose the old rig can hold;
2. drags the skin with it, so the hand does not tear where the ring and
   little fingers are about to be collapsed away.

The male and female rigs need different treatment - the male hand eases each
finger part-way towards a neighbour it will be merged with, the female hand
simply re-bases each chain on one - so the two share this module's plumbing
but keep their own pose functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from pyffi.formats.cgf import CgfFormat

from .chunks import SkeletonChunks
from .errors import MalformedCgfError
from .finger_chains import (
    FEMALE_TUNING,
    MALE_TUNING,
    FingerChain,
    female_chains,
    male_chains,
)
from .math3d import make_vector, partial_rotation, rotation_x, rotation_y

__all__ = ["FingerPose", "reposition_fingers"]

Matrix = CgfFormat.Matrix33
Vector = CgfFormat.Vector3

#: Every finger bone carries this in its name.
FINGER_MARKER = "Finger"

#: Constant swing applied to every female finger root.
_FEMALE_ROOT_SWING = 5.0

#: How far a female finger root is pulled back towards its own tip.
_FEMALE_ROOT_PULL = 0.75

#: Thumb-only corrections, in degrees about the local X axis.
_THUMB_MIDDLE_TWIST = 10.0
_THUMB_TIP_TWIST = -30.0
_THUMB_TIP_SWING = 20.0


@dataclass
class FingerPose:
    """New position and orientation for each finger bone, by bone index."""

    position: dict[int, Vector]
    rotation: dict[int, Matrix]

    def set(self, bone: int, position: Vector, rotation: Matrix) -> None:
        self.position[bone] = position
        self.rotation[bone] = rotation

    def fill_missing(
        self,
        old_position: Mapping[int, Vector],
        old_rotation: Mapping[int, Matrix],
    ) -> None:
        """Leave untouched bones where they are, so every finger has a pose."""
        for bone, position in old_position.items():
            if bone not in self.position:
                self.position[bone] = position.get_copy()
                self.rotation[bone] = old_rotation[bone].get_copy()


class _Rig:
    """Name/index bookkeeping for the finger bones of one model."""

    def __init__(self, chunks: SkeletonChunks) -> None:
        self.names: dict[int, str] = {}
        self.position: dict[int, Vector] = {}
        self.rotation: dict[int, Matrix] = {}

        for index, name in enumerate(chunks.bone_names.names):
            if FINGER_MARKER in name:
                self.names[index] = name
                self.position[index] = chunks.matrices[index].pos
                self.rotation[index] = chunks.matrices[index].rot

        self._by_name = {name: index for index, name in self.names.items()}

    def index(self, bone_name: str) -> int:
        try:
            return self._by_name[bone_name]
        except KeyError:
            raise MalformedCgfError(
                f"finger bone {bone_name!r} is missing from the bone table; "
                f"the input does not look like a patch-5.x character rig"
            ) from None

    def __contains__(self, bone: int) -> bool:
        return bone in self.names


def _swing(chain: FingerChain, degrees: float) -> Matrix:
    """A Y-axis swing, mirrored for the left hand."""
    return rotation_y(degrees, mirrored=not chain.is_right_hand)


def _pose_male(rig: _Rig, template: SkeletonChunks) -> FingerPose:
    """Male pose: ease each finger part-way towards the finger it merges with.

    ``factor`` is what makes this gentle - a little finger that snapped
    straight onto the middle finger's orientation would fold the knuckles
    inside out, so each chain only travels a fraction of the way.
    """
    pose = FingerPose({}, {})

    for chain in male_chains():
        root = rig.index(chain.root)
        middle = rig.index(chain.middle)
        tip = rig.index(chain.tip)
        tuning = MALE_TUNING[chain.finger_index]

        old_root_rot = rig.rotation[root]
        old_middle_rot = rig.rotation[middle]
        delta_root_middle = old_root_rot.get_transpose() * old_middle_rot
        delta_middle_tip = old_middle_rot.get_transpose() * rig.rotation[tip]

        # The thumb has no partner to merge with, so it aims at the template's
        # own thumb orientation instead of at another finger.
        aim = (
            template.matrices[template.index_of(chain.root)].rot
            if chain.is_thumb
            else rig.rotation[rig.index(chain.reference)]
        )

        root_pos = rig.position[root].get_copy()
        root_rot = old_root_rot * partial_rotation(
            old_root_rot.get_transpose() * aim * _swing(chain, tuning.root_angle),
            tuning.factor,
        )
        pose.set(root, root_pos, root_rot)

        middle_rot = (
            root_rot * delta_root_middle * rotation_x(_THUMB_MIDDLE_TWIST)
            if chain.is_thumb
            else root_rot * delta_root_middle * _swing(chain, tuning.middle_angle)
        )
        # The thumb root moved, so its bone length is measured in the new frame.
        middle_frame = root_rot if chain.is_thumb else old_root_rot
        middle_pos = (
            root_pos
            + (
                tuning.length_modifier
                * (rig.position[middle] - rig.position[root])
                * middle_frame.get_transpose()
            )
            * root_rot
        )
        pose.set(middle, middle_pos, middle_rot)

        tip_twist = (
            rotation_x(_THUMB_TIP_TWIST) * _swing(chain, _THUMB_TIP_SWING)
            if chain.is_thumb
            else _swing(chain, tuning.tip_angle)
        )
        tip_rot = middle_rot * delta_middle_tip * tip_twist
        tip_pos = (
            middle_pos
            + (
                tuning.length_modifier
                * (rig.position[tip] - rig.position[middle])
                * old_middle_rot.get_transpose()
            )
            * middle_rot
        )
        pose.set(tip, tip_pos, tip_rot)

    return pose


def _pose_female(rig: _Rig, template: SkeletonChunks) -> FingerPose:
    """Female pose: re-base each chain on its reference finger outright.

    The female old rig's fingers are close enough to the new ones that the
    root can simply take the reference orientation, with a fixed swing, and
    be pulled back towards its own tip to shorten the chain.
    """
    pose = FingerPose({}, {})

    for chain in female_chains():
        root = rig.index(chain.root)
        middle = rig.index(chain.middle)
        tip = rig.index(chain.tip)
        tuning = FEMALE_TUNING[chain.finger_index]

        old_root_rot = rig.rotation[root]
        old_middle_rot = rig.rotation[middle]
        delta_root_middle = old_root_rot.get_transpose() * old_middle_rot
        delta_middle_tip = old_middle_rot.get_transpose() * rig.rotation[tip]

        reference_rot = rig.rotation[rig.index(chain.reference)]
        tip_pos = rig.position[tip]

        root_pos = tip_pos + ((rig.position[root].get_copy() - tip_pos) * _FEMALE_ROOT_PULL)
        root_rot = reference_rot.get_copy() * _swing(chain, _FEMALE_ROOT_SWING)
        pose.set(root, root_pos, root_rot)

        swing = _swing(chain, tuning.angle)

        # A chain already aimed at the middle finger needs no per-joint delta:
        # it inherits the reference pose wholesale and only adds the swing.
        middle_rot = (
            root_rot * swing
            if chain.guided_by_middle_finger
            else root_rot * delta_root_middle * swing
        )
        middle_pos = (
            root_pos
            + (
                tuning.length_modifier
                * (rig.position[middle] - rig.position[root])
                * old_root_rot.get_transpose()
            )
            * root_rot
        )
        pose.set(middle, middle_pos, middle_rot)

        new_tip_rot = (
            middle_rot * swing
            if chain.guided_by_middle_finger
            else middle_rot * delta_middle_tip * swing
        )
        new_tip_pos = (
            middle_pos
            + (
                tuning.length_modifier
                * (rig.position[tip] - rig.position[middle])
                * old_middle_rot.get_transpose()
            )
            * middle_rot
        )
        pose.set(tip, new_tip_pos, new_tip_rot)

    return pose


def reposition_fingers(
    chunks: SkeletonChunks,
    template: SkeletonChunks,
    *,
    is_male: bool,
) -> None:
    """Re-pose the finger bones in place and carry the skin along with them.

    Vertex displacement is linear-blend skinning applied by hand: for each
    bone a vertex is weighted to, the vertex is taken into that bone's old
    frame and put back down in the new one, and the weighted sum of those
    moves is added to its position.  Bones the vertex is weighted to that
    are *not* fingers contribute nothing, which is what keeps the wrist
    still while the fingers move.
    """
    rig = _Rig(chunks)
    if not rig.names:
        return

    pose = (_pose_male if is_male else _pose_female)(rig, template)
    pose.fill_missing(rig.position, rig.rotation)

    displacements = _skin_displacements(chunks, rig, pose)

    for vertex_index, displacement in displacements.items():
        vertex = chunks.vertices[vertex_index]
        vertex.p = vertex.p + displacement

    for bone in rig.names:
        matrix = chunks.matrices[bone]
        matrix.pos = pose.position[bone]
        matrix.rot = pose.rotation[bone]


def _skin_displacements(
    chunks: SkeletonChunks, rig: _Rig, pose: FingerPose
) -> dict[int, Vector]:
    """How far each affected vertex must move, before anything is written."""
    displacements: dict[int, Vector] = {}

    for vertex_index, vertex_weight in enumerate(chunks.vertex_weights):
        if not any(link.bone in rig for link in vertex_weight.bone_links):
            continue

        position = chunks.vertices[vertex_index].p
        delta = make_vector(0, 0, 0)

        for link in vertex_weight.bone_links:
            bone = link.bone
            if bone not in rig:
                continue

            local = (position - rig.position[bone]) * rig.rotation[
                bone
            ].get_transpose()
            moved = local * pose.rotation[bone] + pose.position[bone]
            delta += (moved - position) * link.blending

        displacements[vertex_index] = delta

    return displacements
