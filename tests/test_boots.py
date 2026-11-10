"""Boot inflation, on stand-in chunks like the glove tests."""

from __future__ import annotations

import pytest

from transform_cgf.boots import LEG_BONES, MAX_INFLATION_DISTANCE, inflate_boots
from transform_cgf.reskin.deform import ReskinDeformer
from transform_cgf.reskin.profiles import BoneProfile, ProfileLibrary

from test_gloves import IDENTITY, make_chunks, surface

CALF = "Bip01 L Calf"


def make_deformer(control_points) -> ReskinDeformer:
    return ReskinDeformer(
        ProfileLibrary(
            {
                CALF: BoneProfile(
                    bone_name=CALF,
                    bone_pos=(0.0, 0.0, 0.0),
                    bone_rot=IDENTITY,
                    control_points=tuple(control_points),
                )
            }
        )
    )


def test_calf_is_a_leg_bone():
    assert CALF in LEG_BONES


def test_a_vertex_on_the_leg_surface_gets_the_full_push():
    deformer = make_deformer([surface((0.0, 0.0, 30.0))])
    chunks = make_chunks([(0.0, 0.0, 30.0)], names=(CALF,))
    assert inflate_boots(chunks, deformer, is_dark=True) is True
    assert chunks.vertices[0].p.z == pytest.approx(31.0)


def test_the_push_fades_out_with_distance():
    deformer = make_deformer([surface((0.0, 0.0, 30.0))])
    far = MAX_INFLATION_DISTANCE + 1.0
    chunks = make_chunks([(far, 0.0, 30.0)], names=(CALF,))
    inflate_boots(chunks, deformer, is_dark=True)
    assert chunks.vertices[0].p.z == pytest.approx(30.0)


def test_vertices_not_weighted_to_the_leg_are_left_alone():
    deformer = make_deformer([surface((0.0, 0.0, 30.0))])
    chunks = make_chunks([(0.0, 0.0, 30.0)], names=("Bip01 Spine",))
    assert inflate_boots(chunks, deformer, is_dark=True) is False
    assert chunks.vertices[0].p.z == pytest.approx(30.0)
