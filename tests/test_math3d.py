"""Rotation and vector helpers."""

from __future__ import annotations

import math

import pytest

from transform_cgf.math3d import (
    identity,
    make_vector,
    mean,
    partial_rotation,
    rotation_x,
    rotation_y,
    to_local,
    to_world,
)


def as_rows(matrix) -> list[list[float]]:
    return [
        [matrix.m_11, matrix.m_12, matrix.m_13],
        [matrix.m_21, matrix.m_22, matrix.m_23],
        [matrix.m_31, matrix.m_32, matrix.m_33],
    ]


def determinant(matrix) -> float:
    (a, b, c), (d, e, f), (g, h, i) = as_rows(matrix)
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def assert_close(matrix, other, tol=1e-12) -> None:
    for row_a, row_b in zip(as_rows(matrix), as_rows(other)):
        for a, b in zip(row_a, row_b):
            assert a == pytest.approx(b, abs=tol)


class TestIdentity:
    def test_is_the_identity(self):
        assert as_rows(identity()) == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    def test_returns_a_fresh_matrix_each_call(self):
        first = identity()
        first.m_11 = 99.0
        assert identity().m_11 == 1.0


class TestRotations:
    @pytest.mark.parametrize("degrees", [0, 1, 17, 90, 180, -45])
    def test_x_rotation_is_orthonormal(self, degrees):
        assert determinant(rotation_x(degrees)) == pytest.approx(1.0)

    @pytest.mark.parametrize("degrees", [0, 1, 17, 90, 180, -45])
    def test_y_rotation_is_orthonormal(self, degrees):
        assert determinant(rotation_y(degrees)) == pytest.approx(1.0)

    def test_zero_angle_is_the_identity(self):
        assert_close(rotation_x(0), identity())
        assert_close(rotation_y(0), identity())

    def test_x_rotation_leaves_the_x_axis_alone(self):
        rotated = make_vector(1, 0, 0) * rotation_x(40)
        assert (rotated.x, rotated.y, rotated.z) == pytest.approx((1, 0, 0), abs=1e-12)

    def test_y_rotation_leaves_the_y_axis_alone(self):
        rotated = make_vector(0, 1, 0) * rotation_y(40)
        assert (rotated.x, rotated.y, rotated.z) == pytest.approx((0, 1, 0), abs=1e-12)

    def test_mirroring_negates_the_angle(self):
        assert_close(rotation_y(25, mirrored=True), rotation_y(-25))

    def test_x_rotation_swings_y_towards_z(self):
        """Fixes the sign convention: rotation_x(90) takes +Y to +Z."""
        swung = make_vector(0, 1, 0) * rotation_x(90)
        assert (swung.x, swung.y, swung.z) == pytest.approx((0, 0, 1), abs=1e-12)

    def test_y_rotation_swings_x_towards_z(self):
        """Fixes the sign convention: rotation_y(90) takes +X to +Z."""
        swung = make_vector(1, 0, 0) * rotation_y(90)
        assert (swung.x, swung.y, swung.z) == pytest.approx((0, 0, 1), abs=1e-12)

    def test_opposite_angles_are_inverses(self):
        assert_close(rotation_x(37) * rotation_x(-37), identity(), tol=1e-12)
        assert_close(rotation_y(37) * rotation_y(-37), identity(), tol=1e-12)


class TestPartialRotation:
    @pytest.fixture
    def rotation(self):
        return rotation_y(60)

    def test_factor_zero_is_the_identity(self, rotation):
        assert_close(partial_rotation(rotation, 0.0), identity())

    def test_factor_one_reproduces_the_input(self, rotation):
        assert_close(partial_rotation(rotation, 1.0), rotation)

    def test_half_applied_twice_is_the_whole(self, rotation):
        half = partial_rotation(rotation, 0.5)
        assert_close(half * half, rotation, tol=1e-10)

    def test_stays_orthonormal(self, rotation):
        for factor in (0.25, 0.5, 1.5, 2.0):
            assert determinant(partial_rotation(rotation, factor)) == pytest.approx(1.0)

    def test_extrapolates_past_one(self):
        """Used by tools/rebuild_template.py to invert the male thumb ease."""
        assert_close(partial_rotation(rotation_y(20), 1.5), rotation_y(30), tol=1e-10)

    def test_identity_input_short_circuits(self):
        assert_close(partial_rotation(identity(), 0.37), identity())


class TestVectors:
    def test_mean_averages_componentwise(self):
        averaged = mean([make_vector(0, 0, 0), make_vector(2, 4, 6)])
        assert (averaged.x, averaged.y, averaged.z) == pytest.approx((1, 2, 3))

    def test_mean_of_one_is_itself(self):
        averaged = mean([make_vector(-1.5, 2.5, 0)])
        assert (averaged.x, averaged.y, averaged.z) == pytest.approx((-1.5, 2.5, 0))

    def test_mean_of_nothing_is_an_error_not_the_origin(self):
        with pytest.raises(ZeroDivisionError):
            mean([])

    def test_local_and_world_round_trip(self):
        bone_pos = make_vector(3, -4, 10)
        bone_rot = rotation_y(35)
        point = make_vector(1, 2, 3)

        local = to_local(point, bone_pos, bone_rot)
        back = to_world(local, bone_pos, bone_rot)

        assert (back.x, back.y, back.z) == pytest.approx((1, 2, 3), abs=1e-12)
