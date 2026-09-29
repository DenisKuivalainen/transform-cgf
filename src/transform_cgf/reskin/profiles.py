"""The reskin control-point data and how it is loaded.

A *bone profile* is a sample of how one bone's surrounding skin differs
between the shared patch-5.x body and the old race-specific body: a list of
control points, each pairing a vertex position on the new body (``new_pos``)
with the same vertex on the old one (``old_pos``).

The profiles are generated offline by ``tools/build_bone_profiles.py`` from
the reference meshes and checked in as JSON, because deriving them needs
game assets that cannot be redistributed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Mapping

import numpy as np

__all__ = [
    "ControlPoint",
    "BoneProfile",
    "ProfileLibrary",
    "load_profiles",
    "data_dir",
]

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class ControlPoint:
    """One vertex sampled on both bodies.

    ``is_anchor`` marks a point that must land exactly where ``old_pos``
    says - typically a seam between body parts, where a millimetre of drift
    shows up as a visible crack in game.
    """

    old_pos: Vec3
    new_pos: Vec3
    is_anchor: bool

    @property
    def old(self) -> np.ndarray:
        return np.asarray(self.old_pos, dtype=float)

    @property
    def new(self) -> np.ndarray:
        return np.asarray(self.new_pos, dtype=float)

    def reference(self, is_dark: bool) -> Vec3:
        """The position this point occupies on the body being targeted."""
        return self.old_pos if is_dark else self.new_pos


@dataclass(frozen=True)
class BoneProfile:
    """Control points attached to one bone, plus that bone's rest frame."""

    bone_name: str
    bone_pos: Vec3
    bone_rot: list[list[float]]
    control_points: tuple[ControlPoint, ...]

    @property
    def position(self) -> np.ndarray:
        return np.asarray(self.bone_pos, dtype=float)

    @property
    def rotation(self) -> np.ndarray:
        return np.asarray(self.bone_rot, dtype=float)

    @property
    def anchors(self) -> tuple[ControlPoint, ...]:
        return tuple(cp for cp in self.control_points if cp.is_anchor)


class ProfileLibrary(Mapping[str, BoneProfile]):
    """Read-only mapping of bone name -> :class:`BoneProfile`."""

    def __init__(self, profiles: Mapping[str, BoneProfile]) -> None:
        self._profiles = dict(profiles)

    def __getitem__(self, bone_name: str) -> BoneProfile:
        return self._profiles[bone_name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._profiles)

    def __len__(self) -> int:
        return len(self._profiles)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ProfileLibrary({len(self._profiles)} bones)"

    @property
    def control_point_count(self) -> int:
        return sum(len(p.control_points) for p in self._profiles.values())

    @classmethod
    def from_json(cls, raw: Mapping[str, dict]) -> "ProfileLibrary":
        return cls(
            {
                bone_name: BoneProfile(
                    bone_name=profile["bone_name"],
                    bone_pos=tuple(profile["bone_pos"]),
                    bone_rot=profile["bone_rot"],
                    control_points=tuple(
                        ControlPoint(
                            old_pos=tuple(cp["old_pos"]),
                            new_pos=tuple(cp["new_pos"]),
                            is_anchor=cp["is_anchor"],
                        )
                        for cp in profile["control_points"]
                    ),
                )
                for bone_name, profile in raw.items()
            }
        )

    @classmethod
    def from_file(cls, path: Path) -> "ProfileLibrary":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_json(json.load(handle))


def data_dir() -> Path:
    """Directory holding the bundled profile JSON."""
    return Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def load_profiles(profile_name: str) -> ProfileLibrary:
    """Load a bundled profile file by name, caching the parsed result.

    Parsing ~2k control points is cheap but not free, and a batch conversion
    reloads the same two files for every mesh, so the cache matters.  The
    library is immutable, which is what makes sharing it safe.
    """
    return ProfileLibrary.from_file(data_dir() / profile_name)
