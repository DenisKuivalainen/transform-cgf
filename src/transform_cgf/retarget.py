"""Rebuilding the bone table on the old rig's layout.

The old skeleton is not a subset of the new one - the bones are in a
different order, carry different parent links and different name hashes.
So rather than deleting bones from the input, the template's table is taken
as the shape of the answer and each old-rig slot is filled from whichever
input bone maps onto it.

This module owns only the *bone table*.  The vertex weights that reference
it are rewritten by :mod:`.skinning`, driven by the index mapping returned
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pyffi.formats.cgf import CgfFormat

from .bone_maps import BONE_NAME_MAP
from .chunks import SkeletonChunks
from .errors import MalformedCgfError
from .finger_chains import OLD_RIG_REBASED_CHAINS

__all__ = ["BoneTableRebuild", "build_bone_table", "rebase_old_rig_fingers", "commit"]


@dataclass
class BoneTableRebuild:
    """The old-rig bone table, assembled but not yet written back."""

    names: list[str]
    bones: list[Optional[CgfFormat.BoneAnimChunk]]
    matrices: list[Optional[object]]

    #: source bone index -> old-rig bone index
    index_mapping: dict[int, int] = field(default_factory=dict)

    #: The source bone table as it stood before any of this, which the
    #: weight passes need to resolve names to their original indices.
    source_names: list[str] = field(default_factory=list)
    source_rotations: list[object] = field(default_factory=list)
    source_positions: list[object] = field(default_factory=list)

    def index_of(self, name: str) -> int:
        return self.names.index(name)

    def missing_slots(self) -> list[str]:
        return [
            name
            for name, bone, matrix in zip(self.names, self.bones, self.matrices)
            if bone is None or matrix is None
        ]


def build_bone_table(
    chunks: SkeletonChunks, template: SkeletonChunks
) -> BoneTableRebuild:
    """Map every input bone onto its old-rig slot.

    Finger bones take the template's rest pose outright: the old hand's
    proportions are what the old animations were authored against, so
    keeping the input's finger rest pose would make every hand animation
    land in the wrong place.  Non-finger bones keep the input's pose, which
    is what carries the character's build across.
    """
    rebuild = BoneTableRebuild(
        names=template.names,
        bones=[None] * template.bone_count,
        matrices=[None] * template.bone_count,
    )

    for index, name in enumerate(chunks.bone_names.names):
        rebuild.source_names.append(name)
        rebuild.source_positions.append(chunks.matrices[index].pos.get_copy())
        rebuild.source_rotations.append(chunks.matrices[index].rot.get_copy())

        target_name = BONE_NAME_MAP.get(name)
        if target_name is None or target_name not in rebuild.names:
            continue

        slot = rebuild.names.index(target_name)
        rebuild.index_mapping[index] = slot

        bone = chunks.bone_anim.bones[index]
        template_bone = template.bone_anim.bones[slot]
        bone.bone_id = slot
        bone.parent_id = template_bone.parent_id
        bone.num_children = template_bone.num_children
        bone.bone_name_crc_32 = template_bone.bone_name_crc_32
        rebuild.bones[slot] = bone

        matrix = chunks.matrices[index]
        if "Finger" in name:
            matrix.rot = template.matrices[slot].rot
            matrix.pos = template.matrices[slot].pos
        rebuild.matrices[slot] = matrix

    return rebuild


def rebase_old_rig_fingers(
    rebuild: BoneTableRebuild, template: SkeletonChunks
) -> None:
    """Give the thumb and index their input orientation at template length.

    These two chains are what rings, gauntlets and weapon grips are fitted
    to, so they keep the *input* model's orientation.  Their bone lengths
    still come from the template, because the old animations expect those.
    """
    for root_name, middle_name in OLD_RIG_REBASED_CHAINS:
        root = rebuild.index_of(root_name)
        middle = rebuild.index_of(middle_name)

        try:
            aim = rebuild.source_rotations[rebuild.source_names.index(root_name)]
        except ValueError:
            raise MalformedCgfError(
                f"bone {root_name!r} is missing from the input bone table"
            ) from None

        root_matrix = rebuild.matrices[root]
        middle_matrix = rebuild.matrices[middle]
        if root_matrix is None or middle_matrix is None:
            raise MalformedCgfError(
                f"finger chain {root_name!r} was not mapped onto the old rig"
            )

        # Captured before the root is re-oriented: this is the template's own
        # knuckle bend, which survives the re-aim unchanged.
        knuckle_bend = root_matrix.rot.get_transpose() * middle_matrix.rot

        template_root = template.matrices[root]
        template_middle = template.matrices[middle]

        root_matrix.pos = template_root.pos.get_copy()
        root_matrix.rot = aim.get_copy()

        middle_matrix.rot = root_matrix.rot * knuckle_bend
        middle_matrix.pos = (
            root_matrix.pos
            + (
                (template_middle.pos - template_root.pos)
                * template_root.rot.get_transpose()
            )
            * root_matrix.rot
        )


def commit(chunks: SkeletonChunks, rebuild: BoneTableRebuild) -> None:
    """Write the rebuilt table back into the chunks.

    The name list is overwritten entry by entry and then truncated rather
    than cleared and refilled: PyFFI's string array reuses its element
    objects, and replacing them wholesale loses the per-element sizing the
    writer needs.
    """
    missing = rebuild.missing_slots()
    if missing:
        raise MalformedCgfError(
            "no input bone maps onto old-rig bone(s): " + ", ".join(missing)
        )

    for index, name in enumerate(rebuild.names):
        chunks.bone_names.names[index] = name
    while len(rebuild.names) != len(chunks.bone_names.names):
        chunks.bone_names.names.pop(len(rebuild.names))
    chunks.bone_names.num_names = len(chunks.bone_names.names)

    chunks.bone_anim.bones.clear()
    for bone in rebuild.bones:
        chunks.bone_anim.bones.append(bone)
    chunks.bone_anim.num_bones = len(chunks.bone_anim.bones)

    chunks.bone_initial.initial_pos_matrices.clear()
    for matrix in rebuild.matrices:
        chunks.bone_initial.initial_pos_matrices.append(matrix)
    chunks.bone_initial.num_bones = len(chunks.bone_initial.initial_pos_matrices)
