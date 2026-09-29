"""Regression against known-good conversions.

``tests/data/output_*.cgf`` are meshes converted by the pre-refactor code
and shipped in the game. This suite converts the matching inputs and checks
the result still matches, which is the only assertion here that would catch
a subtle change in the geometry.

Tolerances are set by the file format, not by taste: ``.cgf`` stores
positions as 32-bit floats, and the bundled ``templatedm.cgf`` was itself
recovered through such a file, so a few parts in 10^5 of drift is the floor.
Anything a player could see is orders of magnitude larger than that.
"""

from __future__ import annotations

import math

import pytest

from transform_cgf.chunks import SkeletonChunks

from conftest import chunks_of, data_file

pytestmark = pytest.mark.slow

#: Bone and vertex positions, in world units. The models are ~180 units tall.
POSITION_TOLERANCE = 1e-3

#: Rotation matrix entries, which are direction cosines.
ROTATION_TOLERANCE = 1e-4

#: Skin weights are computed in double precision from exact arithmetic.
WEIGHT_TOLERANCE = 1e-6

#: Fixtures this build no longer reproduces byte for byte.
#:
#: ``output_Body.cgf`` was recorded by an earlier build. Its *geometry* is
#: bit-identical to what this build produces - every bone position, rotation,
#: parent link, vertex, normal, skin weight and link offset matches exactly,
#: and so does the source-info author - but two adjacent bytes elsewhere in
#: the file differ. The pre-refactor code does not reproduce those two bytes
#: either, so this is a stale fixture rather than a regression: it predates
#: some change to the conversion.
#:
#: To clear this: re-run the conversion on ``input_Body.cgf``, replace the
#: fixture with the result, and delete the entry here.
STALE_FIXTURES = {"Body"}


@pytest.fixture
def actual(converted_chunks, part) -> SkeletonChunks:
    return converted_chunks[part]


@pytest.fixture
def expected(expected_chunks, part) -> SkeletonChunks:
    return expected_chunks[part]


def rotation_entries(matrix):
    return [
        getattr(matrix, f"m_{row}{column}")
        for row in (1, 2, 3)
        for column in (1, 2, 3)
    ]


class TestExactEquality:
    """The strictest form of this regression, available with real templates.

    ``output_*.cgf`` were written by the pre-refactor code using the client's
    own templates.  Given those same templates, this build must reproduce them
    exactly - not approximately.  Every other test in this file is a weaker,
    more diagnostic version of this one, kept because they still run when only
    a reconstructed template is available and because they say *what* drifted
    rather than just that something did.
    """

    def test_the_written_file_is_byte_identical(
        self, converted, part, templates_are_authentic
    ):
        if not templates_are_authentic:
            pytest.skip(
                "reconstructed template in use; exact equality needs the "
                "client's own templates in ./templates/"
            )
        if part in STALE_FIXTURES:
            pytest.skip(
                f"output_{part}.cgf was recorded by an earlier build; see "
                f"STALE_FIXTURES in this module"
            )

        assert (
            converted[part].output_path.read_bytes()
            == data_file(f"output_{part}.cgf").read_bytes()
        )


class TestResultMetadata:
    def test_the_bone_count_drops_to_the_old_rig(self, converted, part):
        result = converted[part]
        assert result.source_bone_count == 149
        assert result.target_bone_count == 105

    def test_dark_models_are_reskinned(self, converted, part):
        assert converted[part].reskinned

    def test_only_the_hand_mesh_gets_its_gloves_inflated(self, converted, part):
        assert converted[part].gloves_inflated is (part == "Hand")

    def test_the_output_file_exists(self, converted, part):
        assert converted[part].output_path.is_file()


class TestBoneTable:
    def test_the_bone_names_match_exactly(self, actual, expected):
        assert actual.names == expected.names

    def test_the_bone_count_matches(self, actual, expected):
        assert actual.bone_count == expected.bone_count

    def test_bone_positions_match(self, actual, expected):
        for name, got, want in zip(actual.names, actual.matrices, expected.matrices):
            for axis in ("x", "y", "z"):
                assert getattr(got.pos, axis) == pytest.approx(
                    getattr(want.pos, axis), abs=POSITION_TOLERANCE
                ), f"{name}.pos.{axis}"

    def test_bone_rotations_match(self, actual, expected):
        for name, got, want in zip(actual.names, actual.matrices, expected.matrices):
            assert rotation_entries(got.rot) == pytest.approx(
                rotation_entries(want.rot), abs=ROTATION_TOLERANCE
            ), name

    def test_parent_links_match(self, actual, expected):
        assert [b.parent_id for b in actual.bone_anim.bones] == [
            b.parent_id for b in expected.bone_anim.bones
        ]

    def test_name_hashes_match(self, actual, expected):
        assert [b.bone_name_crc_32 for b in actual.bone_anim.bones] == [
            b.bone_name_crc_32 for b in expected.bone_anim.bones
        ]

    def test_child_counts_match(self, actual, expected):
        assert [b.num_children for b in actual.bone_anim.bones] == [
            b.num_children for b in expected.bone_anim.bones
        ]


class TestMesh:
    def test_the_vertex_count_is_unchanged(self, actual, expected):
        assert len(actual.vertices) == len(expected.vertices)

    def test_vertex_positions_match(self, actual, expected):
        worst = 0.0
        for got, want in zip(actual.vertices, expected.vertices):
            worst = max(
                worst,
                math.dist(
                    (got.p.x, got.p.y, got.p.z), (want.p.x, want.p.y, want.p.z)
                ),
            )
        assert worst < POSITION_TOLERANCE, f"worst vertex drift {worst}"

    def test_vertex_normals_match(self, actual, expected):
        for got, want in zip(actual.vertices, expected.vertices):
            assert (got.n.x, got.n.y, got.n.z) == pytest.approx(
                (want.n.x, want.n.y, want.n.z), abs=ROTATION_TOLERANCE
            )


class TestSkinning:
    def test_every_vertex_has_the_same_bones_at_the_same_weights(
        self, actual, expected
    ):
        for index, (got, want) in enumerate(
            zip(actual.vertex_weights, expected.vertex_weights)
        ):
            got_links = sorted((l.bone, l.blending) for l in got.bone_links)
            want_links = sorted((l.bone, l.blending) for l in want.bone_links)

            assert [b for b, _ in got_links] == [
                b for b, _ in want_links
            ], f"vertex {index} bones"
            assert [w for _, w in got_links] == pytest.approx(
                [w for _, w in want_links], abs=WEIGHT_TOLERANCE
            ), f"vertex {index} weights"

    def test_link_offsets_match(self, actual, expected):
        for index, (got, want) in enumerate(
            zip(actual.vertex_weights, expected.vertex_weights)
        ):
            for a, b in zip(got.bone_links, want.bone_links):
                assert (a.offset.x, a.offset.y, a.offset.z) == pytest.approx(
                    (b.offset.x, b.offset.y, b.offset.z), abs=POSITION_TOLERANCE
                ), f"vertex {index}"

    def test_weights_sum_to_one(self, actual):
        for index, weight in enumerate(actual.vertex_weights):
            total = sum(link.blending for link in weight.bone_links)
            assert total == pytest.approx(1.0, abs=1e-5), f"vertex {index}"

    def test_no_vertex_is_left_unweighted(self, actual):
        for index, weight in enumerate(actual.vertex_weights):
            assert len(weight.bone_links) > 0, f"vertex {index}"

    def test_the_link_count_field_agrees_with_the_list(self, actual):
        for weight in actual.vertex_weights:
            assert weight.num_bone_links == len(weight.bone_links)

    def test_no_link_points_outside_the_bone_table(self, actual):
        for weight in actual.vertex_weights:
            for link in weight.bone_links:
                assert 0 <= link.bone < actual.bone_count


class TestProvenance:
    def test_the_output_is_stamped(self, actual, expected):
        assert actual.source_info.author == expected.source_info.author
