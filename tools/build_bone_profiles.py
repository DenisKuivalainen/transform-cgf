#!/usr/bin/env python3
"""Regenerate the reskin bone profiles from the reference meshes.

This is an offline data-generation step, not part of the conversion.  It
reads the eight old-body and eight new-body reference meshes under
``tools/reference/``, matches them up through the hand-authored point lists
in ``tools/points/``, and writes the control points the reskin field is
built from.

    python tools/build_bone_profiles.py

The output goes to ``src/transform_cgf/reskin/data/`` by default and is
checked in, so this only needs running when the point lists or the reference
meshes change.

**Do not re-save the reference meshes.**  They are the ground truth the whole
reskin depends on; re-exporting one would shift its vertex positions and
silently change every profile derived from it.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from pyffi.formats.cgf import CgfFormat

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
POINTS_DIR = Path(__file__).resolve().parent / "points"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "src" / "transform_cgf" / "reskin" / "data"

#: Bones the reskin field is sampled at.  Everything else - head, fingers,
#: accessories - is either identical between the two bodies or too small to
#: be worth a profile.
ALLOWED_BONES = (
    "Bip01 L Forearm",
    "Bip01 R Forearm",
    "Bip01 L UpperArm",
    "Bip01 R UpperArm",
    "L_ShCustom",
    "R_ShCustom",
    "Bip01 L Clavicle",
    "Bip01 R Clavicle",
    "Bip01 Spine",
    "Bip01 Spine1",
    "Bip01 Pelvis",
    "Bip01 L Thigh",
    "Bip01 R Thigh",
    "Bip01 L Calf",
    "Bip01 R Calf",
    "Bip01 Neck",
    "Bip01 R Foot",
    "Bip01 R Toe0",
    "Bip01 L Foot",
    "Bip01 L Toe0",
)

BODY_PARTS = ("Hand", "Body", "Leg", "Foot")

GENDERS = ("m", "f")

#: Tolerance for matching an authored point to a mesh vertex.
#:
#: The original chained four progressively tighter tolerances with ``or``,
#: but the fallbacks were unreachable - ``find_vertex`` returns a 2-tuple,
#: which is always truthy - so only this first value was ever used.  Kept as
#: the single value it has always effectively been, so that the checked-in
#: profiles stay reproducible.
MATCH_EPSILON = 0.1


# -- reading --------------------------------------------------------------


@dataclass
class ReferenceMesh:
    """The three chunks a reference mesh is read for."""

    bone_names: object
    bone_initial: object
    mesh: object

    def bones_of_interest(self) -> dict[int, str]:
        return {
            index: name
            for index, name in enumerate(self.bone_names.names)
            if name in ALLOWED_BONES
        }


def read_reference(path: Path) -> ReferenceMesh:
    with path.open("rb") as stream:
        data = CgfFormat.Data()
        try:
            data.inspect_version_only(stream)
        except ValueError as exc:
            print(f"{path.name}: {exc}", file=sys.stderr)
        data.read(stream)

    bone_names = bone_initial = mesh = None
    for chunk in data.chunks:
        if isinstance(chunk, CgfFormat.BoneNameListChunk):
            bone_names = chunk
        elif isinstance(chunk, CgfFormat.BoneInitialPosChunk):
            bone_initial = chunk
        elif isinstance(chunk, CgfFormat.MeshChunk) and chunk.has_vertex_weights:
            mesh = chunk

    if bone_names is None or bone_initial is None or mesh is None:
        raise SystemExit(f"{path} is missing a chunk the profile builder needs")

    return ReferenceMesh(bone_names, bone_initial, mesh)


def matrix_to_rows(matrix) -> list[list[float]]:
    return [
        [matrix.m_11, matrix.m_12, matrix.m_13],
        [matrix.m_21, matrix.m_22, matrix.m_23],
        [matrix.m_31, matrix.m_32, matrix.m_33],
    ]


def vector_to_list(vector) -> list[float]:
    return [vector.x, vector.y, vector.z]


# -- point matching -------------------------------------------------------


def find_vertex(vertices, position, epsilon: float = MATCH_EPSILON):
    """Locate the vertex at ``position``.

    Returns ``(index, candidates)``.  ``index`` is ``None`` when the match is
    ambiguous, and ``candidates`` is what was in contention - the caller uses
    it to reconcile a point that matched on one body but not the other.

    Matching is done per axis and then intersected, because the authored
    positions are rounded and a straight distance test misses points that a
    per-axis test finds.
    """
    target = [round(value, 4) for value in position]

    near_x = [i for i, v in enumerate(vertices) if abs(v.p.x - target[0]) <= epsilon]
    near_y = [i for i, v in enumerate(vertices) if abs(v.p.y - target[1]) <= epsilon]
    near_z = [i for i, v in enumerate(vertices) if abs(v.p.z - target[2]) <= epsilon]

    matches = [i for i in near_x if i in near_y and i in near_z]

    if not matches:
        # Nothing matched on all three axes; fall back to any two.
        matches = [i for i in near_x if i in near_y or i in near_z]
        matches += [i for i in near_y if i in near_z and i not in matches]

    if len(matches) != 1:
        return None, matches

    return matches[0], matches


def load_points(gender: str, points_dir: Path) -> list:
    """Read the authored point list, adding the mirrored half.

    Each entry is ``[body part, old position, new position, is anchor]`` with
    an optional fifth flag meaning "do not mirror" - used for points on the
    body's centre line, which have no opposite number.
    """
    with (points_dir / f"{gender}_points.json").open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    points = []
    for entry in raw:
        if len(entry) != 5:
            entry.append(False)

        points.append(copy.deepcopy(entry))
        if entry[4]:
            continue

        mirrored = copy.deepcopy(entry)
        mirrored[1][0] *= -1
        mirrored[2][0] *= -1
        points.append(mirrored)

    return points


@dataclass
class Sample:
    """One control point, attached to one bone."""

    bone_name: str
    bone_pos: list[float]
    bone_rot: list[list[float]]
    vertex_old_pos: list[float]
    vertex_new_pos: list[float]
    is_anchor: bool


def collect_samples(gender: str, reference_dir: Path, points_dir: Path) -> list[Sample]:
    samples: list[Sample] = []
    points = load_points(gender, points_dir)

    for body_part in BODY_PARTS:
        old = read_reference(
            reference_dir / "old" / f"d{gender}df_c001_{body_part.lower()}.cgf"
        )
        new = read_reference(
            reference_dir / "new" / f"D{gender.upper()}DF_C001_{body_part}.cgf"
        )

        old_bones = old.bones_of_interest()
        new_bones = new.bones_of_interest()

        for part, old_pos, new_pos, is_anchor, _ in points:
            if part != body_part:
                continue

            old_index, old_candidates = find_vertex(old.mesh.vertices, old_pos)
            new_index, new_candidates = find_vertex(new.mesh.vertices, new_pos)

            old_index, new_index = _reconcile(
                gender,
                old_index,
                new_index,
                old_candidates,
                new_candidates,
                old_pos,
                new_pos,
            )
            if old_index is None:
                continue

            _append_vertex_samples(
                old,
                new,
                old_index,
                new_index,
                old_bones,
                new_bones,
                is_anchor,
                samples,
            )

    return samples


def _reconcile(
    gender, old_index, new_index, old_candidates, new_candidates, old_pos, new_pos
):
    """Resolve a point that matched cleanly on only one of the two bodies.

    The female meshes are close enough between old and new that an ambiguous
    match on one side can be settled by the other side's answer, if that
    answer was among the candidates.  For the male meshes the shapes differ
    too much for that to be safe, so an unresolved point is an error.
    """
    if old_index is None and new_index is None:
        return None, None

    if gender == "f" and old_index is None and new_index in old_candidates:
        return new_index, new_index

    if gender == "f" and new_index is None and old_index in new_candidates:
        return old_index, old_index

    if old_index is None:
        raise SystemExit(
            f"No matches for old point [{old_pos[0]}, {old_pos[1]}, {old_pos[2]}]"
        )

    if new_index is None:
        raise SystemExit(
            f"No matches for new point [{new_pos[0]}, {new_pos[1]}, {new_pos[2]}]"
        )

    return old_index, new_index


def _append_vertex_samples(
    old, new, old_index, new_index, old_bones, new_bones, is_anchor, samples
) -> None:
    """Add a sample per bone that influences the vertex on *both* bodies.

    A vertex can be reached through several body parts, so the same
    (position, bone) pair may come round more than once; only the first is
    kept.
    """
    old_position = old.mesh.vertices[old_index].p
    new_position = new.mesh.vertices[new_index].p

    new_weights = {
        new_bones[link.bone]: link.blending
        for link in new.mesh.vertex_weights[new_index].bone_links
        if link.bone in new_bones
    }

    for link in old.mesh.vertex_weights[old_index].bone_links:
        if link.bone not in old_bones:
            continue

        bone_name = old_bones[link.bone]
        if bone_name not in new_weights:
            continue

        matrix = new.bone_initial.initial_pos_matrices[link.bone]
        sample = Sample(
            bone_name=bone_name,
            bone_pos=vector_to_list(matrix.pos),
            bone_rot=matrix_to_rows(matrix.rot),
            vertex_old_pos=vector_to_list(old_position),
            vertex_new_pos=vector_to_list(new_position),
            is_anchor=is_anchor,
        )

        if any(
            other.vertex_old_pos == sample.vertex_old_pos
            and other.bone_name == sample.bone_name
            for other in samples
        ):
            continue

        samples.append(sample)


# -- output ---------------------------------------------------------------


@dataclass
class ControlPoint:
    old_pos: tuple
    new_pos: tuple
    is_anchor: bool


@dataclass
class BoneProfile:
    bone_name: str
    bone_pos: tuple
    bone_rot: list
    control_points: list


def build_profiles(gender: str, reference_dir: Path, points_dir: Path) -> dict:
    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in collect_samples(gender, reference_dir, points_dir):
        grouped[sample.bone_name].append(sample)

    profiles = {}
    for bone_name, samples in grouped.items():
        profiles[bone_name] = BoneProfile(
            bone_name=bone_name,
            bone_pos=tuple(samples[0].bone_pos),
            bone_rot=samples[0].bone_rot,
            control_points=[
                ControlPoint(
                    old_pos=s.vertex_old_pos,
                    new_pos=s.vertex_new_pos,
                    is_anchor=s.is_anchor,
                )
                for s in samples
            ],
        )

    return profiles


def write_profiles(profiles: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump({k: asdict(v) for k, v in profiles.items()}, handle, indent=4)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reference", type=Path, default=REFERENCE_DIR, help="reference mesh directory"
    )
    parser.add_argument(
        "--points", type=Path, default=POINTS_DIR, help="authored point lists"
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="where to write the JSON"
    )
    parser.add_argument("--gender", choices=GENDERS, action="append")
    args = parser.parse_args(argv)

    for gender in args.gender or list(GENDERS):
        profiles = build_profiles(gender, args.reference, args.points)
        destination = args.output / f"{gender}_bone_profiles.json"
        write_profiles(profiles, destination)
        points = sum(len(p.control_points) for p in profiles.values())
        print(f"{destination}: {len(profiles)} bones, {points} control points")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
