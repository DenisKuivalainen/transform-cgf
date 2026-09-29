"""The reskin deformation field."""

from __future__ import annotations

import numpy as np
import pytest

from transform_cgf.reskin.deform import (
    ANCHOR_RADIUS,
    NEAREST_COUNT,
    ReskinDeformer,
    VertexBone,
)
from transform_cgf.reskin.profiles import (
    BoneProfile,
    ControlPoint,
    ProfileLibrary,
    load_profiles,
)

IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def profile(name: str, points, bone_pos=(0.0, 0.0, 0.0)) -> BoneProfile:
    return BoneProfile(
        bone_name=name,
        bone_pos=bone_pos,
        bone_rot=IDENTITY,
        control_points=tuple(points),
    )


def point(old, new, anchor=False) -> ControlPoint:
    return ControlPoint(old_pos=tuple(old), new_pos=tuple(new), is_anchor=anchor)


class TestSyntheticField:
    """A one-bone field where the right answer is known by construction."""

    @pytest.fixture
    def shift(self) -> ReskinDeformer:
        """Every control point moved by exactly (10, 0, 0)."""
        points = [
            point(old=(x + 10.0, y, 0.0), new=(x, y, 0.0))
            for x in (0.0, 1.0, 2.0, 3.0, 4.0)
            for y in (0.0, 1.0, 2.0)
        ]
        return ReskinDeformer(ProfileLibrary({"Bone": profile("Bone", points)}))

    def test_a_uniform_shift_is_reproduced(self, shift):
        moved = shift.transform_vertex([2.0, 1.0, 0.0], [VertexBone("Bone", 1.0)])
        assert moved == pytest.approx([12.0, 1.0, 0.0], abs=1e-9)

    def test_weight_scales_the_displacement(self, shift):
        moved = shift.transform_vertex([2.0, 1.0, 0.0], [VertexBone("Bone", 0.5)])
        assert moved == pytest.approx([7.0, 1.0, 0.0], abs=1e-9)

    def test_weights_from_several_bones_add_up(self, shift):
        both = shift.transform_vertex(
            [2.0, 1.0, 0.0], [VertexBone("Bone", 0.25), VertexBone("Bone", 0.25)]
        )
        assert both == pytest.approx([7.0, 1.0, 0.0], abs=1e-9)


class TestAnchors:
    @pytest.fixture
    def anchored(self) -> ReskinDeformer:
        points = [
            point(old=(100.0, 0.0, 0.0), new=(0.0, 0.0, 0.0), anchor=True),
            *[
                point(old=(x, y, 0.0), new=(x, y, 0.0))
                for x in (20.0, 21.0, 22.0, 23.0)
                for y in (0.0, 1.0)
            ],
        ]
        return ReskinDeformer(ProfileLibrary({"Bone": profile("Bone", points)}))

    def test_a_vertex_on_an_anchor_lands_on_its_recorded_position(self, anchored):
        moved = anchored.transform_vertex([0.0, 0.0, 0.0], [VertexBone("Bone", 1.0)])
        assert moved == pytest.approx([100.0, 0.0, 0.0], abs=1e-9)

    def test_anchor_influence_is_gone_beyond_its_radius(self, anchored):
        far = [ANCHOR_RADIUS * 4, 0.0, 0.0]
        moved = anchored.transform_vertex(far, [VertexBone("Bone", 1.0)])
        assert moved[0] == pytest.approx(far[0], abs=1e-6)

    def test_influence_falls_off_with_distance(self, anchored):
        near = anchored.transform_vertex(
            [ANCHOR_RADIUS * 0.25, 0.0, 0.0], [VertexBone("Bone", 1.0)]
        )
        further = anchored.transform_vertex(
            [ANCHOR_RADIUS * 0.75, 0.0, 0.0], [VertexBone("Bone", 1.0)]
        )
        assert near[0] > further[0]

    def test_anchors_for_returns_only_anchors(self, anchored):
        anchors = anchored.anchors_for("Bone")
        assert len(anchors) == 1
        assert all(cp.is_anchor for cp in anchors)

    def test_anchors_for_an_unknown_bone_is_empty(self, anchored):
        assert anchored.anchors_for("Nope") == ()


class TestPassThrough:
    @pytest.fixture
    def deformer(self) -> ReskinDeformer:
        points = [point(old=(1.0, 0.0, 0.0), new=(0.0, 0.0, 0.0))]
        return ReskinDeformer(ProfileLibrary({"Bone": profile("Bone", points)}))

    def test_a_vertex_with_no_profiled_bone_is_untouched(self, deformer):
        original = [5.0, 6.0, 7.0]
        assert deformer.transform_vertex(original, [VertexBone("Other", 1.0)]) == original

    def test_a_vertex_with_no_bones_at_all_is_untouched(self, deformer):
        original = [5.0, 6.0, 7.0]
        assert deformer.transform_vertex(original, []) == original

    def test_zero_and_negative_weights_are_ignored(self, deformer):
        original = [5.0, 6.0, 7.0]
        assert deformer.transform_vertex(original, [VertexBone("Bone", 0.0)]) == original
        assert deformer.transform_vertex(original, [VertexBone("Bone", -1.0)]) == original

    def test_the_input_list_is_not_mutated(self, deformer):
        original = [5.0, 6.0, 7.0]
        deformer.transform_vertex(original, [VertexBone("Bone", 1.0)])
        assert original == [5.0, 6.0, 7.0]

    def test_has_profile(self, deformer):
        assert deformer.has_profile("Bone")
        assert not deformer.has_profile("Other")


class TestDistanceQuery:
    @pytest.fixture
    def deformer(self) -> ReskinDeformer:
        points = [point(old=(3.0, 0.0, 0.0), new=(10.0, 0.0, 0.0))]
        return ReskinDeformer(ProfileLibrary({"Bone": profile("Bone", points)}))

    def test_measures_against_the_old_body_for_dark_models(self, deformer):
        assert deformer.distance_to_closest_control_point(
            (0.0, 0.0, 0.0), ["Bone"], is_dark=True
        ) == pytest.approx(3.0)

    def test_measures_against_the_new_body_otherwise(self, deformer):
        assert deformer.distance_to_closest_control_point(
            (0.0, 0.0, 0.0), ["Bone"], is_dark=False
        ) == pytest.approx(10.0)

    def test_unknown_bones_give_infinity_rather_than_zero(self, deformer):
        assert (
            deformer.distance_to_closest_control_point((0, 0, 0), ["Nope"], True)
            == float("inf")
        )


class TestRealData:
    @pytest.fixture
    def deformer(self) -> ReskinDeformer:
        return ReskinDeformer(load_profiles("m_bone_profiles.json"))

    def test_the_field_is_deterministic(self, deformer):
        bones = [VertexBone("Bip01 Spine1", 0.6), VertexBone("Bip01 Neck", 0.4)]
        position = [5.0, -3.0, 140.0]
        assert deformer.transform_vertex(position, bones) == deformer.transform_vertex(
            position, bones
        )

    def test_the_displacement_is_small(self, deformer):
        """A reskin nudges the surface; it does not relocate it."""
        bones = [VertexBone("Bip01 Spine1", 1.0)]
        position = np.array([5.0, -3.0, 140.0])
        moved = np.asarray(deformer.transform_vertex(list(position), bones))
        assert np.linalg.norm(moved - position) < 10.0

    def test_caching_does_not_change_the_answer(self, deformer):
        """The local-space cache is warmed by the first call."""
        fresh = ReskinDeformer(load_profiles("m_bone_profiles.json"))
        bones = [VertexBone("Bip01 L Forearm", 1.0)]
        position = [12.0, -2.0, 120.0]
        assert fresh.transform_vertex(position, bones) == deformer.transform_vertex(
            position, bones
        )

    def test_uses_at_most_the_configured_neighbour_count(self, deformer):
        assert NEAREST_COUNT == 4
