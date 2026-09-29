"""Chunk discovery, the skeleton view, and input validation."""

from __future__ import annotations

import pytest
from pyffi.formats.cgf import CgfFormat

from transform_cgf.chunks import (
    MIN_PLAYER_BONES,
    SkeletonChunks,
    find_chunks,
    validate_convertible,
)
from transform_cgf.errors import (
    AlreadyOldFormatError,
    MalformedCgfError,
    NotAPlayerModelError,
    UnsupportedModelError,
)

from conftest import chunks_of, data_file, load


class TestFindChunks:
    def test_finds_everything_in_a_real_mesh(self, source_chunks):
        assert source_chunks.bone_names is not None
        assert source_chunks.bone_anim is not None
        assert source_chunks.bone_initial is not None
        assert source_chunks.mesh is not None
        assert source_chunks.source_info is not None

    def test_the_three_bone_chunks_agree_on_length(self, source_chunks):
        assert source_chunks.bone_count == 149
        assert len(source_chunks.names) == 149
        assert len(source_chunks.matrices) == 149
        assert source_chunks.bone_anim.num_bones == 149

    def test_a_template_may_have_no_skinned_mesh(self, template_dir):
        chunks = chunks_of(template_dir / "templatedm.cgf", require_mesh=False)
        assert chunks.bone_count == 105

    def test_a_missing_chunk_is_reported_by_name(self):
        data = CgfFormat.Data()
        with pytest.raises(MalformedCgfError) as caught:
            find_chunks(data)

        message = str(caught.value)
        assert "BoneNameList" in message
        assert "BoneAnim" in message
        assert "BoneInitialPos" in message

    def test_requiring_a_mesh_is_part_of_the_message(self):
        data = CgfFormat.Data()
        with pytest.raises(MalformedCgfError, match="Mesh"):
            find_chunks(data, require_mesh=True)


class TestSkeletonView:
    def test_looks_bones_up_by_name(self, source_chunks):
        index = source_chunks.index_of("Bip01 Head")
        assert source_chunks.name_of(index) == "Bip01 Head"

    def test_an_unknown_bone_is_a_file_error_not_a_value_error(self, source_chunks):
        with pytest.raises(MalformedCgfError, match="Bip01 Tail"):
            source_chunks.index_of("Bip01 Tail")

    def test_has_bone(self, source_chunks):
        assert source_chunks.has_bone("Bip01 Pelvis")
        assert not source_chunks.has_bone("Bip01 Tail")

    def test_vertices_and_weights_line_up(self, source_chunks):
        assert len(source_chunks.vertices) == len(source_chunks.vertex_weights)

    def test_iter_links_visits_every_link(self, source_chunks):
        counted = sum(
            len(weight.bone_links) for weight in source_chunks.vertex_weights
        )
        assert sum(1 for _ in source_chunks.iter_links()) == counted

    def test_requiring_an_absent_mesh_raises(self, template_dir):
        chunks = chunks_of(template_dir / "templatedm.cgf", require_mesh=False)
        chunks.mesh = None
        with pytest.raises(MalformedCgfError, match="no mesh chunk"):
            chunks.require_mesh()


class TestValidation:
    def test_a_patch_5x_mesh_is_convertible(self, source_chunks, template_chunks):
        validate_convertible(source_chunks, template_chunks, label="x.cgf")

    def test_an_already_converted_mesh_is_rejected(self, template_chunks):
        already = chunks_of(data_file("output_Body.cgf"))
        with pytest.raises(AlreadyOldFormatError, match="already in old format"):
            validate_convertible(already, template_chunks, label="output_Body.cgf")

    def test_a_prop_is_rejected(self, template_chunks, source_chunks):
        source_chunks.bone_names.num_names = MIN_PLAYER_BONES - 1
        with pytest.raises(NotAPlayerModelError, match="not a PC model"):
            validate_convertible(source_chunks, template_chunks, label="sword.cgf")

    def test_both_rejections_share_a_base_class(self, template_chunks):
        """So a batch run can skip unconvertible files with one except."""
        already = chunks_of(data_file("output_Body.cgf"))
        with pytest.raises(UnsupportedModelError):
            validate_convertible(already, template_chunks, label="x.cgf")

    def test_the_message_names_the_file(self, template_chunks):
        already = chunks_of(data_file("output_Body.cgf"))
        with pytest.raises(AlreadyOldFormatError, match="my_mesh.cgf"):
            validate_convertible(already, template_chunks, label="my_mesh.cgf")
