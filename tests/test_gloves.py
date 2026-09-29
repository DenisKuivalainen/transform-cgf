"""Glove inflation.

Built on stand-in chunks rather than a real mesh: the behaviour under test
is geometric and reads only vertices, normals and weights.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pyffi.formats.cgf import CgfFormat

from transform_cgf.chunks import SkeletonChunks
from transform_cgf.gloves import (
    ARM_BONES,
    EPSILON,
    MAX_INFLATION_DISTANCE,
    inflate_gloves,
)
from transform_cgf.reskin.deform import ReskinDeformer
from transform_cgf.reskin.profiles import BoneProfile, ControlPoint, ProfileLibrary

IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
ARM = "Bip01 L Forearm"


def vec(x, y, z) -> CgfFormat.Vector3:
    v = CgfFormat.Vector3()
    v.x, v.y, v.z = float(x), float(y), float(z)
    return v


def vertex(position, normal=(0.0, 0.0, 1.0)):
    return SimpleNamespace(p=vec(*position), n=vec(*normal))


def weight(bone_index, blending=1.0):
    link = CgfFormat.BoneLink()
    link.bone = bone_index
    link.blending = blending
    return SimpleNamespace(bone_links=[link], num_bone_links=1)


def make_chunks(positions, normals=None, names=(ARM,)):
    normals = normals or [(0.0, 0.0, 1.0)] * len(positions)
    mesh = SimpleNamespace(
        vertices=[vertex(p, n) for p, n in zip(positions, normals)],
        vertex_weights=[weight(0) for _ in positions],
        has_vertex_weights=True,
    )
    return SkeletonChunks(
        bone_names=SimpleNamespace(names=list(names), num_names=len(names)),
        bone_anim=SimpleNamespace(bones=[], num_bones=0),
        bone_initial=SimpleNamespace(initial_pos_matrices=[], num_bones=0),
        mesh=mesh,
    )


def make_deformer(control_points) -> ReskinDeformer:
    return ReskinDeformer(
        ProfileLibrary(
            {
                ARM: BoneProfile(
                    bone_name=ARM,
                    bone_pos=(0.0, 0.0, 0.0),
                    bone_rot=IDENTITY,
                    control_points=tuple(control_points),
                )
            }
        )
    )


def anchor(position):
    return ControlPoint(old_pos=tuple(position), new_pos=tuple(position), is_anchor=True)


def surface(position):
    return ControlPoint(
        old_pos=tuple(position), new_pos=tuple(position), is_anchor=False
    )


class TestSkinIsSkipped:
    """A mesh sharing geometry with the reference body is bare skin."""

    def test_a_mesh_sitting_on_an_anchor_is_left_alone(self):
        deformer = make_deformer([anchor((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0), (1.0, 0.0, 100.0)])
        before = [(v.p.x, v.p.y, v.p.z) for v in chunks.vertices]

        assert inflate_gloves(chunks, deformer, is_dark=True) is False
        assert [(v.p.x, v.p.y, v.p.z) for v in chunks.vertices] == before

    def test_the_match_is_within_epsilon(self):
        deformer = make_deformer([anchor((0.0, 0.0, 100.0))])
        chunks = make_chunks([(EPSILON / 2, 0.0, 100.0)])
        assert inflate_gloves(chunks, deformer, is_dark=True) is False

    def test_just_outside_epsilon_is_not_a_match(self):
        deformer = make_deformer([anchor((0.0, 0.0, 100.0))])
        chunks = make_chunks([(EPSILON * 10, 0.0, 100.0)])
        assert inflate_gloves(chunks, deformer, is_dark=True) is True

    def test_the_race_decides_which_body_the_anchors_describe(self):
        point = ControlPoint(
            old_pos=(0.0, 0.0, 100.0), new_pos=(50.0, 0.0, 100.0), is_anchor=True
        )
        deformer = make_deformer([point])

        on_old_body = make_chunks([(0.0, 0.0, 100.0)])
        assert inflate_gloves(on_old_body, deformer, is_dark=True) is False

        on_new_body = make_chunks([(0.0, 0.0, 100.0)])
        assert inflate_gloves(on_new_body, deformer, is_dark=False) is True


class TestInflation:
    def test_a_vertex_on_the_arm_surface_is_pushed_out_fully(self):
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0)])

        inflate_gloves(chunks, deformer, is_dark=True)

        # distance 0 -> full push of one unit along the normal
        assert chunks.vertices[0].p.z == pytest.approx(101.0)

    def test_the_push_tapers_with_distance(self):
        deformer = make_deformer([surface((0.0, 0.0, 0.0))])
        near = make_chunks([(0.0, 0.0, MAX_INFLATION_DISTANCE / 3)])
        far = make_chunks([(0.0, 0.0, MAX_INFLATION_DISTANCE * 2 / 3)])

        inflate_gloves(near, deformer, is_dark=True)
        inflate_gloves(far, deformer, is_dark=True)

        near_push = near.vertices[0].p.z - MAX_INFLATION_DISTANCE / 3
        far_push = far.vertices[0].p.z - MAX_INFLATION_DISTANCE * 2 / 3
        assert near_push > far_push > 0

    def test_nothing_happens_beyond_the_falloff_distance(self):
        deformer = make_deformer([surface((0.0, 0.0, 0.0))])
        chunks = make_chunks([(0.0, 0.0, MAX_INFLATION_DISTANCE * 2)])

        inflate_gloves(chunks, deformer, is_dark=True)

        assert chunks.vertices[0].p.z == pytest.approx(MAX_INFLATION_DISTANCE * 2)

    def test_vertices_above_the_height_limit_are_untouched(self):
        deformer = make_deformer([surface((0.0, 0.0, 200.0))])
        chunks = make_chunks([(0.0, 0.0, 200.0)])

        inflate_gloves(chunks, deformer, is_dark=True)

        assert chunks.vertices[0].p.z == pytest.approx(200.0)

    def test_a_vertex_not_weighted_to_the_arm_is_untouched(self):
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0)], names=("Bip01 Head",))

        assert inflate_gloves(chunks, deformer, is_dark=True) is False
        assert chunks.vertices[0].p.z == pytest.approx(100.0)

    def test_the_push_scales_with_the_arm_weight(self):
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0)])
        chunks.vertex_weights[0].bone_links[0].blending = 0.5

        inflate_gloves(chunks, deformer, is_dark=True)

        assert chunks.vertices[0].p.z == pytest.approx(100.5)

    def test_the_push_follows_the_normal(self):
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0)], normals=[(1.0, 0.0, 0.0)])

        inflate_gloves(chunks, deformer, is_dark=True)

        assert chunks.vertices[0].p.x == pytest.approx(1.0)
        assert chunks.vertices[0].p.z == pytest.approx(100.0)


class TestSeamWelding:
    def test_coincident_vertices_end_up_coincident(self):
        """Split vertices must not be torn apart by the inflation."""
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks(
            [(0.0, 0.0, 100.0), (0.0, 0.0, 100.0)],
            normals=[(0.0, 0.0, 1.0), (1.0, 0.0, 0.0)],
        )

        inflate_gloves(chunks, deformer, is_dark=True)

        first, second = chunks.vertices
        assert (first.p.x, first.p.y, first.p.z) == (second.p.x, second.p.y, second.p.z)

    def test_distinct_vertices_move_independently(self):
        deformer = make_deformer([surface((0.0, 0.0, 100.0))])
        chunks = make_chunks([(0.0, 0.0, 100.0), (0.0, 0.0, 110.0)])

        inflate_gloves(chunks, deformer, is_dark=True)

        assert chunks.vertices[0].p.z != chunks.vertices[1].p.z


class TestConstants:
    def test_the_arm_bone_list_covers_both_arms(self):
        assert len(ARM_BONES) == 4
        assert sum(1 for name in ARM_BONES if " L " in name) == 2
