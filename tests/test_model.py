"""The model code value object."""

from __future__ import annotations

import pytest

from transform_cgf import InvalidModelError, Model
from transform_cgf.model import MODEL_CODES


class TestParsing:
    @pytest.mark.parametrize("code", MODEL_CODES)
    def test_accepts_every_valid_code(self, code):
        assert Model(code).code == code

    @pytest.mark.parametrize("code", ["DM", "Lf", "LM"])
    def test_normalises_case(self, code):
        assert Model(code).code == code.lower()

    @pytest.mark.parametrize("code", ["", "x", "ml", "dmm", "d_m", "fd"])
    def test_rejects_anything_else(self, code):
        with pytest.raises(InvalidModelError):
            Model(code)

    def test_rejects_non_strings(self):
        with pytest.raises(InvalidModelError):
            Model(42)

    def test_error_lists_the_valid_codes(self):
        with pytest.raises(InvalidModelError, match="lf, df, lm, dm"):
            Model("zz")

    def test_parse_passes_a_model_through(self):
        existing = Model("dm")
        assert Model.parse(existing) is existing

    def test_parse_accepts_a_string(self):
        assert Model.parse("lf") == Model("lf")

    def test_parse_rejects_none(self):
        with pytest.raises(InvalidModelError):
            Model.parse(None)

    def test_is_hashable_and_comparable(self):
        assert Model("dm") == Model("DM")
        assert len({Model("dm"), Model("DM"), Model("lf")}) == 2


class TestProperties:
    @pytest.mark.parametrize(
        "code,dark,male",
        [("lf", False, False), ("df", True, False), ("lm", False, True), ("dm", True, True)],
    )
    def test_race_and_gender_flags(self, code, dark, male):
        model = Model(code)
        assert model.is_dark is dark
        assert model.is_male is male

    @pytest.mark.parametrize("code", MODEL_CODES)
    def test_template_name_matches_the_code(self, code):
        assert Model(code).template_name == f"template{code}.cgf"

    def test_profile_is_chosen_by_gender_only(self):
        assert Model("lm").profile_name == Model("dm").profile_name == "m_bone_profiles.json"
        assert Model("lf").profile_name == Model("df").profile_name == "f_bone_profiles.json"

    def test_readable_names(self):
        assert (Model("df").race, Model("df").gender) == ("dark", "female")
        assert str(Model("lm")) == "lm"
