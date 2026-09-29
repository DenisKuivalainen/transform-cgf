"""The command-line interface."""

from __future__ import annotations

import pytest

from transform_cgf.cli import build_parser, main

from conftest import data_file

SMALL = "input_Shoulder.cgf"


@pytest.fixture
def workspace(tmp_path, template_dir):
    """A directory holding one convertible mesh."""
    source = tmp_path / "in"
    source.mkdir()
    (source / SMALL).write_bytes(data_file(SMALL).read_bytes())
    return source


def run(argv, template_dir, **extra):
    return main([*argv, "--templates", str(template_dir)])


class TestArgumentParsing:
    def test_model_is_required(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["a.cgf"])

    def test_an_unknown_model_is_rejected_by_argparse(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["a.cgf", "-m", "zz"])

    def test_several_inputs_are_accepted(self):
        args = build_parser().parse_args(["a.cgf", "b.cgf", "-m", "dm"])
        assert len(args.inputs) == 2

    def test_defaults(self):
        args = build_parser().parse_args(["a.cgf", "-m", "lf"])
        assert args.output is None
        assert args.templates is None
        assert args.keep_going is False
        assert args.verbose is False

    def test_short_options(self):
        args = build_parser().parse_args(
            ["a.cgf", "-m", "dm", "-o", "out", "-t", "tpl", "-k", "-v"]
        )
        assert (str(args.output), str(args.templates)) == ("out", "tpl")
        assert args.keep_going and args.verbose


@pytest.mark.slow
class TestConversion:
    def test_converts_a_single_file(self, workspace, tmp_path, template_dir):
        out = tmp_path / "out.cgf"
        assert run([str(workspace / SMALL), "-m", "dm", "-o", str(out)], template_dir) == 0
        assert out.is_file()

    def test_a_directory_is_searched_for_cgf_files(
        self, workspace, tmp_path, template_dir
    ):
        out = tmp_path / "out"
        assert run([str(workspace), "-m", "dm", "-o", str(out)], template_dir) == 0
        assert (out / SMALL).is_file()

    def test_the_default_output_is_beside_the_input(self, workspace, template_dir):
        assert run([str(workspace / SMALL), "-m", "dm"], template_dir) == 0
        assert (workspace / "transform_output" / SMALL).is_file()

    def test_reports_what_it_did(self, workspace, tmp_path, template_dir, caplog):
        with caplog.at_level("INFO"):
            run([str(workspace / SMALL), "-m", "dm", "-o", str(tmp_path)], template_dir)
        assert "149" in caplog.text and "105" in caplog.text


class TestErrorHandling:
    def test_no_matching_files_is_a_usage_error(self, tmp_path, template_dir):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert run([str(empty), "-m", "dm"], template_dir) == 2

    def test_a_single_output_file_with_many_inputs_is_refused(
        self, tmp_path, template_dir
    ):
        code = run(
            ["a.cgf", "b.cgf", "-m", "dm", "-o", str(tmp_path / "one.cgf")],
            template_dir,
        )
        assert code == 2

    @pytest.mark.slow
    def test_an_already_converted_file_is_skipped_not_failed(
        self, tmp_path, template_dir, caplog
    ):
        staged = tmp_path / "output_Shoulder.cgf"
        staged.write_bytes(data_file("output_Shoulder.cgf").read_bytes())

        with caplog.at_level("INFO"):
            code = run([str(staged), "-m", "dm", "-o", str(tmp_path)], template_dir)

        assert code == 0
        assert "skipped" in caplog.text

    def test_a_missing_template_fails_with_one(self, tmp_path):
        missing = tmp_path / "no-templates"
        missing.mkdir()
        staged = tmp_path / "x.cgf"
        staged.write_bytes(data_file("input_Shoulder.cgf").read_bytes())

        assert main([str(staged), "-m", "dm", "--templates", str(missing)]) == 1

    @pytest.mark.slow
    def test_keep_going_carries_on_past_a_failure(
        self, workspace, tmp_path, template_dir, caplog
    ):
        broken = workspace / "broken.cgf"
        broken.write_bytes(b"not a cgf")

        with caplog.at_level("INFO"):
            code = run(
                [str(workspace), "-m", "dm", "-o", str(tmp_path / "out"), "-k"],
                template_dir,
            )

        assert code == 1
        assert (tmp_path / "out" / SMALL).is_file()
        assert "broken.cgf" in caplog.text

    @pytest.mark.slow
    def test_without_keep_going_it_stops(self, workspace, tmp_path, template_dir):
        (workspace / "aaa_broken.cgf").write_bytes(b"not a cgf")

        code = run(
            [str(workspace), "-m", "dm", "-o", str(tmp_path / "out")], template_dir
        )

        assert code == 1
        assert not (tmp_path / "out" / SMALL).exists()
