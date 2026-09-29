"""The ``lf`` / ``df`` / ``lm`` / ``dm`` model code as a value object.

The original code passed the two-character string around and re-derived
``model[0] == "d"`` / ``model[1] == "m"`` at each use site.  Parsing it once
into a :class:`Model` puts the meaning of those characters in exactly one
place and makes an invalid code fail immediately instead of halfway through
a transform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

from .errors import InvalidModelError

__all__ = ["Model", "ModelCode", "MODEL_CODES"]

#: The four playable combinations of race and gender in Aion's asset naming.
ModelCode = Literal["lf", "df", "lm", "dm"]

MODEL_CODES: tuple[str, ...] = ("lf", "df", "lm", "dm")

_RACES = {"l": "light", "d": "dark"}
_GENDERS = {"f": "female", "m": "male"}


@dataclass(frozen=True)
class Model:
    """A parsed two-character model code: race letter then gender letter.

    ``l``/``d`` select the Elyos ("light") or Asmodian ("dark") race and
    ``f``/``m`` the gender, matching Aion's ``LF``/``DF``/``LM``/``DM``
    asset prefixes.
    """

    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise InvalidModelError(
                f"model must be a string, got {type(self.code).__name__}"
            )
        normalised = self.code.lower()
        if normalised not in MODEL_CODES:
            raise InvalidModelError(
                f"unknown model {self.code!r}; expected one of "
                + ", ".join(MODEL_CODES)
            )
        # frozen dataclass: bypass the setattr guard to normalise the case
        object.__setattr__(self, "code", normalised)

    @classmethod
    def parse(cls, model: Union["Model", str, None]) -> "Model":
        """Coerce ``model`` to a :class:`Model`, accepting an existing one."""
        if isinstance(model, Model):
            return model
        if model is None:
            raise InvalidModelError("model is required")
        return cls(model)

    @property
    def is_dark(self) -> bool:
        """True for Asmodian models, which need the body reskin."""
        return self.code[0] == "d"

    @property
    def is_male(self) -> bool:
        """True for male models, which use the 105-bone old rig."""
        return self.code[1] == "m"

    @property
    def race(self) -> str:
        return _RACES[self.code[0]]

    @property
    def gender(self) -> str:
        return _GENDERS[self.code[1]]

    @property
    def template_name(self) -> str:
        """File name of the old-rig template this model is retargeted onto."""
        return f"template{self.code}.cgf"

    @property
    def profile_name(self) -> str:
        """File name of the reskin bone-profile data for this model's gender."""
        return f"{'m' if self.is_male else 'f'}_bone_profiles.json"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.code
