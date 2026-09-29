"""Finger repositioning, on a real rig."""

from __future__ import annotations

import math

import pytest

from transform_cgf.errors import MalformedCgfError
from transform_cgf.fingers import FINGER_MARKER, reposition_fingers

from conftest import chunks_of, data_file


def snapshot_bones(chunks):
    return {
        name: (
            (m.pos.x, m.pos.y, m.pos.z),
            tuple(getattr(m.rot, f"m_{r}{c}") for r in (1, 2, 3) for c in (1, 2, 3)),
        )
        for name, m in zip(chunks.names, chunks.matrices)
    }


def snapshot_vertices(chunks):
    return [(v.p.x, v.p.y, v.p.z) for v in chunks.vertices]


@pytest.fixture
def hand():
    """The hand mesh - the one where fingers actually carry weight."""
    return chunks_of(data_file("input_Hand.cgf"))


class TestBoneMovement:
    def test_finger_bones_move(self, hand, template_chunks):
        before = snapshot_bones(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        after = snapshot_bones(hand)

        moved = [n for n in before if FINGER_MARKER in n and before[n] != after[n]]
        assert len(moved) >= 20

    def test_nothing_else_moves(self, hand, template_chunks):
        before = snapshot_bones(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        after = snapshot_bones(hand)

        changed = [n for n in before if before[n] != after[n]]
        assert all(FINGER_MARKER in name for name in changed)

    def test_the_bone_count_is_unchanged(self, hand, template_chunks):
        before = hand.bone_count
        reposition_fingers(hand, template_chunks, is_male=True)
        assert hand.bone_count == before

    def test_rotations_stay_orthonormal(self, hand, template_chunks):
        reposition_fingers(hand, template_chunks, is_male=True)

        for name, matrix in zip(hand.names, hand.matrices):
            if FINGER_MARKER not in name:
                continue
            rows = [
                [getattr(matrix.rot, f"m_{r}{c}") for c in (1, 2, 3)] for r in (1, 2, 3)
            ]
            for row in rows:
                assert math.sqrt(sum(v * v for v in row)) == pytest.approx(1.0, abs=1e-5), name

    def test_finger_bones_stay_near_the_hand(self, hand, template_chunks):
        """A retarget nudges fingers; it does not fling them across the model."""
        before = snapshot_bones(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        after = snapshot_bones(hand)

        for name in before:
            if FINGER_MARKER not in name:
                continue
            assert math.dist(before[name][0], after[name][0]) < 10.0, name


class TestSkinFollows:
    def test_vertices_move(self, hand, template_chunks):
        before = snapshot_vertices(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        after = snapshot_vertices(hand)

        assert sum(1 for a, b in zip(before, after) if a != b) > 100

    def test_vertices_with_no_finger_weight_do_not_move(self, hand, template_chunks):
        names = hand.names
        untouched = [
            index
            for index, weight in enumerate(hand.vertex_weights)
            if not any(FINGER_MARKER in names[l.bone] for l in weight.bone_links)
        ]
        assert untouched, "the fixture has no finger-free vertices to check"

        before = snapshot_vertices(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        after = snapshot_vertices(hand)

        for index in untouched:
            assert before[index] == after[index]

    def test_the_vertex_count_is_unchanged(self, hand, template_chunks):
        before = len(hand.vertices)
        reposition_fingers(hand, template_chunks, is_male=True)
        assert len(hand.vertices) == before

    def test_weights_are_not_touched(self, hand, template_chunks):
        before = [
            [(l.bone, l.blending) for l in w.bone_links] for w in hand.vertex_weights
        ]
        reposition_fingers(hand, template_chunks, is_male=True)
        after = [
            [(l.bone, l.blending) for l in w.bone_links] for w in hand.vertex_weights
        ]
        assert before == after


class TestGenderPaths:
    def test_male_and_female_produce_different_poses(self, template_chunks):
        male = chunks_of(data_file("input_Hand.cgf"))
        female = chunks_of(data_file("input_Hand.cgf"))

        reposition_fingers(male, template_chunks, is_male=True)
        reposition_fingers(female, template_chunks, is_male=False)

        assert snapshot_bones(male) != snapshot_bones(female)

    def test_the_female_path_does_not_consult_the_template(self, template_chunks):
        """Only the male thumb reads a template orientation."""
        first = chunks_of(data_file("input_Hand.cgf"))
        second = chunks_of(data_file("input_Hand.cgf"))

        reposition_fingers(first, template_chunks, is_male=False)
        reposition_fingers(second, second, is_male=False)

        assert snapshot_bones(first) == snapshot_bones(second)


class TestFailures:
    def test_a_rig_with_no_fingers_is_a_no_op(self, hand, template_chunks):
        for index in range(hand.bone_count):
            if FINGER_MARKER in hand.bone_names.names[index]:
                hand.bone_names.names[index] = f"Bone{index}"

        before = snapshot_vertices(hand)
        reposition_fingers(hand, template_chunks, is_male=True)
        assert snapshot_vertices(hand) == before

    def test_a_half_present_finger_rig_is_reported(self, hand, template_chunks):
        index = hand.index_of("Bip01 R Finger41")
        hand.bone_names.names[index] = "Bip01 R FingerX"

        with pytest.raises(MalformedCgfError, match="Finger41"):
            reposition_fingers(hand, template_chunks, is_male=True)
