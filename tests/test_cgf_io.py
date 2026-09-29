"""Path resolution, reading, writing and the author stamp."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from transform_cgf import Model, TemplateNotFoundError
from transform_cgf.cgf_io import (
    SIGN_SUFFIX,
    TEMPLATE_DIR_ENV,
    default_template_dir,
    read_cgf,
    resolve_input_path,
    resolve_output_path,
    stamp_sign,
    template_path,
    write_cgf,
)
from transform_cgf.chunks import find_chunks
from transform_cgf.errors import MalformedCgfError

from conftest import data_file


class TestResolveInputPath:
    def test_a_bare_name_is_left_alone(self):
        assert resolve_input_path("mesh.cgf") == Path("mesh.cgf")

    @pytest.mark.parametrize("folder", ["assets", "assets/", "assets//"])
    def test_trailing_separators_do_not_matter(self, folder):
        """The old API concatenated strings and needed exactly one."""
        assert resolve_input_path("mesh.cgf", folder) == Path("assets/mesh.cgf")

    def test_an_empty_folder_is_ignored(self):
        assert resolve_input_path("mesh.cgf", "") == Path("mesh.cgf")
        assert resolve_input_path("mesh.cgf", None) == Path("mesh.cgf")

    def test_an_absolute_input_wins(self):
        assert resolve_input_path("/abs/mesh.cgf", "assets") == Path("/abs/mesh.cgf")


class TestResolveOutputPath:
    def test_default_is_a_sibling_directory(self):
        assert resolve_output_path("a/b/mesh.cgf") == Path(
            "a/b/transform_output/mesh.cgf"
        )

    def test_default_for_a_bare_name(self):
        assert resolve_output_path("mesh.cgf") == Path("transform_output/mesh.cgf")

    def test_a_directory_keeps_the_input_name(self):
        assert resolve_output_path("a/mesh.cgf", "out") == Path("out/mesh.cgf")

    def test_a_cgf_path_is_used_verbatim(self):
        assert resolve_output_path("a/mesh.cgf", "out/other.cgf") == Path(
            "out/other.cgf"
        )

    def test_the_suffix_check_ignores_case(self):
        assert resolve_output_path("a/mesh.cgf", "out/OTHER.CGF") == Path(
            "out/OTHER.CGF"
        )

    def test_a_directory_named_like_a_file_is_still_a_directory(self):
        assert resolve_output_path("a/mesh.cgf", "out.d") == Path("out.d/mesh.cgf")


class TestTemplateLookup:
    def test_default_is_a_templates_directory(self, monkeypatch):
        monkeypatch.delenv(TEMPLATE_DIR_ENV, raising=False)
        assert default_template_dir() == Path("templates")

    def test_the_environment_variable_overrides_it(self, monkeypatch):
        monkeypatch.setenv(TEMPLATE_DIR_ENV, "/srv/aion/templates")
        assert default_template_dir() == Path("/srv/aion/templates")

    def test_an_explicit_directory_beats_the_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv(TEMPLATE_DIR_ENV, "/nowhere")
        (tmp_path / "templatedm.cgf").write_bytes(b"")
        assert template_path(Model("dm"), tmp_path) == tmp_path / "templatedm.cgf"

    def test_a_missing_template_says_what_to_do_about_it(self, tmp_path):
        with pytest.raises(TemplateNotFoundError) as caught:
            template_path(Model("lf"), tmp_path)

        message = str(caught.value)
        assert "templatelf.cgf" in message
        assert "game assets" in message
        assert TEMPLATE_DIR_ENV in message

    def test_finds_the_real_template(self, template_dir):
        assert template_path(Model("dm"), template_dir).is_file()


class TestReadWrite:
    def test_reads_a_real_mesh(self):
        data = read_cgf(data_file("input_Body.cgf"))
        assert find_chunks(data).bone_count == 149

    def test_a_non_cgf_file_raises_a_typed_error(self, tmp_path):
        broken = tmp_path / "broken.cgf"
        broken.write_bytes(b"not a cgf file at all")
        with pytest.raises(MalformedCgfError, match="could not read"):
            read_cgf(broken)

    def test_round_trips_through_a_write(self, tmp_path):
        data = read_cgf(data_file("input_Shoulder.cgf"))
        destination = tmp_path / "nested" / "deeper" / "out.cgf"

        write_cgf(data, destination)

        assert destination.is_file()
        assert find_chunks(read_cgf(destination)).bone_count == 149

    def test_creates_missing_parent_directories(self, tmp_path):
        data = read_cgf(data_file("input_Shoulder.cgf"))
        written = write_cgf(data, tmp_path / "a" / "b" / "c.cgf")
        assert written.parent.is_dir()


class TestAuthorStamp:
    def test_appends_the_suffix_once(self):
        chunks = find_chunks(read_cgf(data_file("input_Shoulder.cgf")))
        before = chunks.source_info.author

        stamp_sign(chunks.source_info)

        assert chunks.source_info.author == before + SIGN_SUFFIX

    def test_tolerates_a_file_with_no_source_info(self):
        stamp_sign(None)  # must not raise

    def test_the_fixtures_carry_the_stamp(self):
        chunks = find_chunks(read_cgf(data_file("output_Body.cgf")))
        assert chunks.source_info.author.endswith(SIGN_SUFFIX)
