"""The reskin control-point data."""

from __future__ import annotations

import numpy as np
import pytest

from transform_cgf.model import Model
from transform_cgf.reskin.profiles import (
    BoneProfile,
    ControlPoint,
    ProfileLibrary,
    data_dir,
    load_profiles,
)

GENDERS = ["m_bone_profiles.json", "f_bone_profiles.json"]


@pytest.fixture(params=GENDERS, ids=["male", "female"])
def library(request) -> ProfileLibrary:
    return load_profiles(request.param)


class TestBundledData:
    @pytest.mark.parametrize("name", GENDERS)
    def test_both_genders_ship_with_the_package(self, name):
        assert (data_dir() / name).is_file()

    def test_the_model_picks_the_right_file(self):
        for code in ("lm", "dm"):
            assert load_profiles(Model(code).profile_name) is load_profiles(
                "m_bone_profiles.json"
            )

    def test_loading_is_cached(self):
        assert load_profiles("m_bone_profiles.json") is load_profiles(
            "m_bone_profiles.json"
        )


class TestLibrary:
    def test_covers_the_bones_the_reskin_needs(self, library):
        for bone in ("Bip01 L Forearm", "Bip01 R Forearm", "Bip01 Spine"):
            assert bone in library

    def test_has_a_substantial_number_of_control_points(self, library):
        assert library.control_point_count > 1000

    def test_behaves_as_a_mapping(self, library):
        assert len(library) == len(list(library))
        name = next(iter(library))
        assert library[name].bone_name == name

    def test_an_unknown_bone_is_absent_rather_than_guessed(self, library):
        assert "Bip01 Tail" not in library
        assert library.get("Bip01 Tail") is None

    def test_repr_says_how_big_it_is(self, library):
        assert str(len(library)) in repr(library)


class TestProfiles:
    def test_every_profile_has_a_rest_frame(self, library):
        for profile in library.values():
            assert len(profile.bone_pos) == 3
            assert np.asarray(profile.bone_rot).shape == (3, 3)

    def test_rotations_are_orthonormal(self, library):
        for profile in library.values():
            rot = profile.rotation
            assert np.allclose(rot @ rot.T, np.eye(3), atol=1e-4)
            assert np.linalg.det(rot) == pytest.approx(1.0, abs=1e-4)

    def test_every_profile_has_control_points(self, library):
        for profile in library.values():
            assert profile.control_points

    def test_forearms_carry_the_seam_anchors(self, library):
        for bone in ("Bip01 L Forearm", "Bip01 R Forearm"):
            assert library[bone].anchors

    def test_anchors_are_a_subset_of_the_control_points(self, library):
        for profile in library.values():
            assert set(profile.anchors) <= set(profile.control_points)


class TestControlPoint:
    @pytest.fixture
    def point(self) -> ControlPoint:
        return ControlPoint(old_pos=(1.0, 2.0, 3.0), new_pos=(4.0, 5.0, 6.0), is_anchor=True)

    def test_reference_follows_the_race(self, point):
        assert point.reference(is_dark=True) == (1.0, 2.0, 3.0)
        assert point.reference(is_dark=False) == (4.0, 5.0, 6.0)

    def test_numpy_views(self, point):
        assert np.array_equal(point.old, np.array([1.0, 2.0, 3.0]))
        assert np.array_equal(point.new, np.array([4.0, 5.0, 6.0]))

    def test_is_hashable_so_profiles_can_be_compared(self, point):
        assert len({point, point}) == 1

    def test_is_immutable(self, point):
        with pytest.raises(Exception):
            point.is_anchor = False
