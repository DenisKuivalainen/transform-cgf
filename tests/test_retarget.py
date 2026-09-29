"""Rebuilding the bone table on the old rig."""

from __future__ import annotations

import pytest

from transform_cgf.bone_maps import BONE_NAME_MAP
from transform_cgf.errors import MalformedCgfError
from transform_cgf.finger_chains import OLD_RIG_REBASED_CHAINS
from transform_cgf.retarget import (
    build_bone_table,
    commit,
    rebase_old_rig_fingers,
)

from conftest import chunks_of, data_file


@pytest.fixture
def source():
    return chunks_of(data_file("input_Hand.cgf"))


@pytest.fixture
def rebuild(source, template_chunks):
    return build_bone_table(source, template_chunks)


class TestBuildBoneTable:
    def test_the_table_is_the_templates_shape(self, rebuild, template_chunks):
        assert rebuild.names == template_chunks.names
        assert len(rebuild.bones) == template_chunks.bone_count
        assert len(rebuild.matrices) == template_chunks.bone_count

    def test_every_slot_is_filled(self, rebuild):
        assert rebuild.missing_slots() == []

    def test_the_source_table_is_captured_before_anything_changes(
        self, rebuild, source
    ):
        assert rebuild.source_names == source.names
        assert len(rebuild.source_rotations) == len(rebuild.source_names)
        assert len(rebuild.source_positions) == len(rebuild.source_names)

    def test_the_index_mapping_only_covers_mapped_bones(self, rebuild):
        for source_index, slot in rebuild.index_mapping.items():
            name = rebuild.source_names[source_index]
            assert BONE_NAME_MAP[name] == rebuild.names[slot]

    def test_bone_ids_and_parents_come_from_the_template(
        self, rebuild, template_chunks
    ):
        for slot, bone in enumerate(rebuild.bones):
            template_bone = template_chunks.bone_anim.bones[slot]
            assert bone.bone_id == slot
            assert bone.parent_id == template_bone.parent_id
            assert bone.num_children == template_bone.num_children
            assert bone.bone_name_crc_32 == template_bone.bone_name_crc_32

    def test_finger_bones_take_the_templates_rest_pose(
        self, rebuild, template_chunks
    ):
        slot = rebuild.index_of("Bip01 L Finger2")
        assert rebuild.matrices[slot].pos.x == pytest.approx(
            template_chunks.matrices[slot].pos.x
        )

    def test_non_finger_bones_keep_the_inputs_rest_pose(
        self, rebuild, source, template_chunks
    ):
        slot = rebuild.index_of("Bip01 L Forearm")
        source_index = source.index_of("Bip01 L Forearm")
        assert rebuild.matrices[slot].pos.x == pytest.approx(
            rebuild.source_positions[source_index].x
        )


class TestRebaseFingers:
    def test_the_thumb_and_index_take_the_inputs_orientation(
        self, rebuild, template_chunks
    ):
        rebase_old_rig_fingers(rebuild, template_chunks)

        for root_name, _ in OLD_RIG_REBASED_CHAINS:
            slot = rebuild.index_of(root_name)
            source_rot = rebuild.source_rotations[
                rebuild.source_names.index(root_name)
            ]
            assert rebuild.matrices[slot].rot.m_11 == pytest.approx(source_rot.m_11)

    def test_the_thumb_keeps_the_templates_position(self, rebuild, template_chunks):
        rebase_old_rig_fingers(rebuild, template_chunks)

        slot = rebuild.index_of("Bip01 R Finger0")
        assert rebuild.matrices[slot].pos.x == pytest.approx(
            template_chunks.matrices[slot].pos.x
        )

    def test_the_middle_finger_is_not_rebased(self, rebuild, template_chunks):
        slot = rebuild.index_of("Bip01 R Finger2")
        before = rebuild.matrices[slot].pos.x

        rebase_old_rig_fingers(rebuild, template_chunks)

        assert rebuild.matrices[slot].pos.x == pytest.approx(before)

    def test_a_missing_source_bone_is_reported(self, rebuild, template_chunks):
        index = rebuild.source_names.index("Bip01 R Finger0")
        rebuild.source_names[index] = "Something Else"

        with pytest.raises(MalformedCgfError, match="Bip01 R Finger0"):
            rebase_old_rig_fingers(rebuild, template_chunks)


class TestCommit:
    def test_the_chunks_shrink_to_the_old_rig(self, source, rebuild):
        commit(source, rebuild)

        assert source.bone_count == 105
        assert source.names == rebuild.names
        assert source.bone_anim.num_bones == 105
        assert source.bone_initial.num_bones == 105

    def test_the_three_chunks_stay_in_step(self, source, rebuild):
        commit(source, rebuild)

        assert (
            len(source.bone_names.names)
            == len(source.bone_anim.bones)
            == len(source.bone_initial.initial_pos_matrices)
        )

    def test_an_unfilled_slot_is_refused(self, source, rebuild):
        rebuild.bones[7] = None

        with pytest.raises(MalformedCgfError, match=rebuild.names[7]):
            commit(source, rebuild)

    def test_the_error_names_every_unfilled_slot(self, source, rebuild):
        rebuild.matrices[3] = None
        rebuild.matrices[9] = None

        with pytest.raises(MalformedCgfError) as caught:
            commit(source, rebuild)

        assert rebuild.names[3] in str(caught.value)
        assert rebuild.names[9] in str(caught.value)
