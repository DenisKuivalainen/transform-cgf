"""The offline tools under ``tools/``.

Both are data-generation steps whose output is checked in, so the useful
assertion for each is that re-running it reproduces what is committed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from conftest import data_file  # noqa: E402

pytestmark = pytest.mark.slow


def reference_assets() -> Path:
    directory = TOOLS / "reference"
    if not (directory / "old").is_dir():
        pytest.skip("reference meshes are not present in tools/reference/")
    return directory


class TestBuildBoneProfiles:
    @pytest.mark.parametrize("gender", ["m", "f"])
    def test_regenerating_reproduces_the_checked_in_data(self, gender, tmp_path):
        import build_bone_profiles as builder

        profiles = builder.build_profiles(
            gender, reference_assets(), TOOLS / "points"
        )
        destination = tmp_path / f"{gender}_bone_profiles.json"
        builder.write_profiles(profiles, destination)

        committed = (
            REPO_ROOT
            / "src"
            / "transform_cgf"
            / "reskin"
            / "data"
            / f"{gender}_bone_profiles.json"
        )
        assert destination.read_bytes() == committed.read_bytes()

    def test_every_sampled_bone_is_on_the_allow_list(self, tmp_path):
        import build_bone_profiles as builder

        profiles = builder.build_profiles("m", reference_assets(), TOOLS / "points")
        assert set(profiles) <= set(builder.ALLOWED_BONES)

    def test_mirrored_points_are_added(self, tmp_path):
        import build_bone_profiles as builder

        raw = json.loads((TOOLS / "points" / "m_points.json").read_text())
        expanded = builder.load_points("m", TOOLS / "points")
        assert len(expanded) > len(raw)

    def test_centre_line_points_are_not_mirrored(self):
        import build_bone_profiles as builder

        expanded = builder.load_points("m", TOOLS / "points")
        unmirrored = [p for p in expanded if p[4]]
        for point in unmirrored:
            twin = [p for p in expanded if p[1] == point[1] and p is not point]
            assert not twin, point


class TestRebuildTemplate:
    def test_it_is_deterministic(self, tmp_path):
        import rebuild_template

        first = tmp_path / "one.cgf"
        second = tmp_path / "two.cgf"
        for destination in (first, second):
            rebuild_template.main(
                [
                    str(data_file("input_Body.cgf")),
                    str(data_file("output_Body.cgf")),
                    str(destination),
                ]
            )

        assert first.read_bytes() == second.read_bytes()

    def test_any_body_part_gives_the_same_template(self, tmp_path, template_dir):
        """The skeleton is shared, so every mesh of a character agrees."""
        import rebuild_template

        from transform_cgf.chunks import find_chunks

        from_hand = find_chunks(
            rebuild_template.rebuild(
                data_file("input_Hand.cgf"), data_file("output_Hand.cgf")
            )
        )
        from_body = find_chunks(
            rebuild_template.rebuild(
                data_file("input_Body.cgf"), data_file("output_Body.cgf")
            )
        )

        for name in ("Bip01 L Finger0", "Bip01 R Finger0"):
            hand = from_hand.matrices[from_hand.index_of(name)]
            body = from_body.matrices[from_body.index_of(name)]
            assert hand.rot.m_11 == pytest.approx(body.rot.m_11, abs=1e-5)
            assert hand.pos.x == pytest.approx(body.pos.x, abs=1e-4)

    def test_the_recovered_template_converts_back_to_the_recorded_output(
        self, tmp_path, template_dir
    ):
        """The round trip that justifies shipping a reconstructed template."""
        import rebuild_template

        from transform_cgf import transform_cgf
        from transform_cgf.chunks import find_chunks
        from transform_cgf.cgf_io import read_cgf

        templates = tmp_path / "templates"
        rebuild_template.main(
            [
                str(data_file("input_Shoulder.cgf")),
                str(data_file("output_Shoulder.cgf")),
                str(templates / "templatedm.cgf"),
            ]
        )

        result = transform_cgf(
            data_file("input_Shoulder.cgf"),
            tmp_path / "out.cgf",
            model="dm",
            template_dir=templates,
        )

        produced = find_chunks(read_cgf(result.output_path))
        recorded = find_chunks(read_cgf(data_file("output_Shoulder.cgf")))

        for got, want in zip(produced.vertices, recorded.vertices):
            assert (got.p.x, got.p.y, got.p.z) == pytest.approx(
                (want.p.x, want.p.y, want.p.z), abs=1e-3
            )
