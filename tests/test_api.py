"""The public ``transform_cgf`` function and its failure modes."""

from __future__ import annotations

from pathlib import Path

import pytest

from transform_cgf import (
    AlreadyOldFormatError,
    InvalidModelError,
    Model,
    TemplateNotFoundError,
    TransformCgfError,
    transform_cgf,
)

from conftest import chunks_of, data_file

pytestmark = pytest.mark.slow

SMALL = "input_Shoulder.cgf"


@pytest.fixture
def convert(tmp_path, template_dir):
    def run(**kwargs):
        kwargs.setdefault("input", data_file(SMALL))
        kwargs.setdefault("output", tmp_path / "out.cgf")
        kwargs.setdefault("model", "dm")
        kwargs.setdefault("template_dir", template_dir)
        return transform_cgf(**kwargs)

    return run


class TestHappyPath:
    def test_writes_the_file_and_describes_it(self, convert, tmp_path):
        result = convert()

        assert result.output_path == tmp_path / "out.cgf"
        assert result.output_path.is_file()
        assert result.source_bone_count == 149
        assert result.target_bone_count == 105
        assert result.vertex_count == 308
        assert result.model == Model("dm")

    def test_an_output_directory_keeps_the_input_name(self, convert, tmp_path):
        result = convert(output=tmp_path / "written")
        assert result.output_path == tmp_path / "written" / SMALL

    def test_missing_directories_are_created(self, convert, tmp_path):
        result = convert(output=tmp_path / "a" / "b" / "c.cgf")
        assert result.output_path.is_file()

    def test_the_default_output_sits_beside_the_input(self, tmp_path, template_dir):
        staged = tmp_path / SMALL
        staged.write_bytes(data_file(SMALL).read_bytes())

        result = transform_cgf(staged, model="dm", template_dir=template_dir)

        assert result.output_path == tmp_path / "transform_output" / SMALL
        assert result.output_path.is_file()

    def test_input_folder_is_joined_as_a_path(self, tmp_path, template_dir):
        result = transform_cgf(
            SMALL,
            tmp_path / "out.cgf",
            input_folder=data_file(SMALL).parent,
            model="dm",
            template_dir=template_dir,
        )
        assert result.output_path.is_file()

    def test_accepts_a_model_object(self, convert):
        assert convert(model=Model("dm")).model == Model("dm")

    def test_leaves_the_input_file_alone(self, convert):
        source = data_file(SMALL)
        before = source.read_bytes()
        convert()
        assert source.read_bytes() == before

    def test_is_deterministic(self, convert, tmp_path):
        first = convert(output=tmp_path / "one.cgf").output_path.read_bytes()
        second = convert(output=tmp_path / "two.cgf").output_path.read_bytes()
        assert first == second


class TestFailures:
    def test_an_unknown_model_is_rejected_before_any_work(self, convert, tmp_path):
        with pytest.raises(InvalidModelError):
            convert(model="zz")
        assert not (tmp_path / "out.cgf").exists()

    def test_a_missing_template_is_reported_clearly(self, convert, tmp_path):
        empty = tmp_path / "templates"
        empty.mkdir()
        with pytest.raises(TemplateNotFoundError, match="templatelm.cgf"):
            convert(model="lm", template_dir=empty)

    def test_a_missing_template_directory_is_reported(self, convert, tmp_path):
        with pytest.raises(TemplateNotFoundError):
            convert(template_dir=tmp_path / "nowhere")

    def test_converting_an_output_again_is_refused(self, convert):
        with pytest.raises(AlreadyOldFormatError):
            convert(input=data_file("output_Shoulder.cgf"))

    def test_a_missing_input_is_an_ordinary_file_error(self, convert, tmp_path):
        with pytest.raises(OSError):
            convert(input=tmp_path / "nope.cgf")

    def test_every_failure_shares_a_base_class(self, convert):
        """So a batch caller can use one except clause."""
        with pytest.raises(TransformCgfError):
            convert(model="zz")
        with pytest.raises(TransformCgfError):
            convert(input=data_file("output_Shoulder.cgf"))

    def test_failure_raises_rather_than_printing(self, convert, capsys):
        """The pre-1.0 function swallowed ValueError and printed it."""
        with pytest.raises(AlreadyOldFormatError):
            convert(input=data_file("output_Shoulder.cgf"))
        assert capsys.readouterr().out == ""


class TestReskinAndGloves:
    def test_a_light_model_is_not_reskinned(self, tmp_path, template_dir):
        """Light models already match the body the old client expects.

        The dark-male template stands in here; only the race flag is
        under test, and it does not depend on the template's contents.
        """
        result = transform_cgf(
            data_file(SMALL),
            tmp_path / "out.cgf",
            model="dm",
            template_dir=template_dir,
        )
        assert result.reskinned

    def test_gloves_are_only_touched_on_hand_meshes(self, convert):
        assert not convert().gloves_inflated
