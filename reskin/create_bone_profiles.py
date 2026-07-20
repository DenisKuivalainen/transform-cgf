from pyffi.formats.cgf import CgfFormat
from dataclasses import dataclass, asdict
import json
from typing import List
import numpy as np
from collections import defaultdict
import copy

allowed_bones = [
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
]


def find_vertices(vertices, pos, epsilon=1e-2, retry=True):
    position = [round(v, 4) for v in pos]
    matches_x = []
    matches_y = []
    matches_z = []

    for i, v in enumerate(vertices):
        if abs(v.p.x - position[0]) <= epsilon:
            matches_x.append(i)

        if abs(v.p.y - position[1]) <= epsilon:
            matches_y.append(i)

        if abs(v.p.z - position[2]) <= epsilon:
            matches_z.append(i)

    matches = []
    for mx in matches_x:
        if mx in matches_y and mx in matches_z:
            matches.append(mx)

    if len(matches) == 0:
        for mx in matches_x:
            if mx in matches_y or mx in matches_z:
                matches.append(mx)

    if len(matches) != 1:
        if retry:
            return find_vertices(vertices, pos, 1e-4, False)

        raise Exception(
            f"{len(matches)} for point [{position[0]}, {position[1]}, {position[2]}]"
        )

    return matches[0]


def getChunks(file):
    with open(file, "rb") as caf:
        data = CgfFormat.Data()
        try:
            data.inspect_version_only(caf)
        except ValueError as e:
            print(e)

        try:
            data.read(caf)
        except:
            raise

    bone_name_chunk: CgfFormat.BoneNameListChunk = None
    bone_initial_chunk: CgfFormat.BoneInitialPosChunk = None
    vertex_chunk: CgfFormat.MeshChunk = None

    for i, chunk in enumerate(data.chunks):
        if isinstance(chunk, CgfFormat.BoneNameListChunk):
            bone_name_chunk = chunk
        elif isinstance(chunk, CgfFormat.BoneInitialPosChunk):
            bone_initial_chunk = chunk
        elif isinstance(chunk, CgfFormat.MeshChunk) and chunk.has_vertex_weights:
            vertex_chunk = chunk

    return bone_name_chunk, bone_initial_chunk, vertex_chunk


def matrix_to_array(m):
    return [
        [m.m_11, m.m_12, m.m_13],
        [m.m_21, m.m_22, m.m_23],
        [m.m_31, m.m_32, m.m_33],
    ]


def vector_to_array(v):
    return [v.x, v.y, v.z]


def read_points_json(gender):
    with open(f"./points/{gender}_points.json", "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class VertexesTransformation:
    bone_name: str
    bone_pos: list[float]
    bone_rot: list[list[float]]

    vertex_old_pos: list[float]
    vertex_new_pos: list[float]
    is_anchor: bool

    def __init__(
        self,
        bone_name,
        bone_pos,
        bone_rot,
        vertex_old_pos,
        vertex_new_pos,
        is_anchor,
    ):
        self.bone_name = bone_name
        self.bone_pos = vector_to_array(bone_pos)
        self.bone_rot = matrix_to_array(bone_rot)
        self.vertex_old_pos = vector_to_array(vertex_old_pos)
        self.vertex_new_pos = vector_to_array(vertex_new_pos)
        self.is_anchor = is_anchor


def get_matched_vertices(gender):
    matched_vertices: list[VertexesTransformation] = []

    points = []
    for p in read_points_json(gender):
        if len(p) != 5:
            p.append(False)

        points.append(copy.deepcopy(p))
        if p[4]:
            continue

        mirrored = copy.deepcopy(p)
        mirrored[1][0] *= -1
        mirrored[2][0] *= -1

        points.append(mirrored)

    for body_part in ["Hand", "Body", "Leg", "Foot"]:
        old_bone_name_chunk, old_bone_initial_chunk, old_vertex_chunk = getChunks(
            f"./old/d{gender}df_c001_{body_part.lower()}.cgf"
        )

        new_bone_name_chunk, new_bone_initial_chunk, new_vertex_chunk = getChunks(
            f"./new/D{gender.upper()}DF_C001_{body_part}.cgf"
        )

        old_bone_names = {}
        new_bone_names = {}

        for name_index, name in enumerate(old_bone_name_chunk.names):
            if name in allowed_bones:
                old_bone_names[name_index] = name

        for name_index, name in enumerate(new_bone_name_chunk.names):
            if name in allowed_bones:
                new_bone_names[name_index] = name

        for b_p, old_pos, new_pos, is_anchor, _ in points:
            if b_p != body_part:
                continue
            old_vertex_index = find_vertices(old_vertex_chunk.vertices, old_pos)
            new_vertex_index = find_vertices(new_vertex_chunk.vertices, new_pos)

            if old_vertex_index is None or new_vertex_index is None:
                continue

            old_vertex_p = old_vertex_chunk.vertices[old_vertex_index].p
            new_vertex_p = new_vertex_chunk.vertices[new_vertex_index].p

            new_bones_weights = {}

            for link in new_vertex_chunk.vertex_weights[new_vertex_index].bone_links:
                if link.bone not in new_bone_names:
                    continue

                new_bones_weights[new_bone_names[link.bone]] = link.blending

            for link in old_vertex_chunk.vertex_weights[old_vertex_index].bone_links:
                if link.bone not in old_bone_names:
                    continue

                bone_name = old_bone_names[link.bone]

                if bone_name not in new_bones_weights:
                    continue

                t = VertexesTransformation(
                    bone_name,
                    new_bone_initial_chunk.initial_pos_matrices[link.bone].pos,
                    new_bone_initial_chunk.initial_pos_matrices[link.bone].rot,
                    old_vertex_p,
                    new_vertex_p,
                    is_anchor,
                )

                if not any(
                    m.vertex_old_pos == t.vertex_old_pos and m.bone_name == t.bone_name
                    for m in matched_vertices
                ):
                    matched_vertices.append(t)

    return matched_vertices


@dataclass
class ControlPoint:
    old_pos: tuple[float, float, float]
    new_pos: tuple[float, float, float]
    is_anchor: bool


@dataclass
class BoneProfile:
    bone_name: str
    bone_pos: tuple[float, float, float]
    bone_rot: list[list[float]]
    control_points: List[ControlPoint]


def world_to_local(point, bone_pos, bone_rot):
    point = np.asarray(point, dtype=float)
    bone_pos = np.asarray(bone_pos, dtype=float)
    rot = np.asarray(bone_rot, dtype=float)

    return rot.T @ (point - bone_pos)


def local_to_world(vec, bone_rot):
    rot = np.asarray(bone_rot, dtype=float)
    return rot @ vec


def build_profiles(gender):
    matched = get_matched_vertices(gender)

    grouped = defaultdict(list)

    for sample in matched:
        grouped[sample.bone_name].append(sample)

    profiles = {}

    for bone_name, samples in grouped.items():

        bone_pos = samples[0].bone_pos
        bone_rot = samples[0].bone_rot

        control_points = []

        for s in samples:
            cp = ControlPoint(
                old_pos=s.vertex_old_pos,
                new_pos=s.vertex_new_pos,
                is_anchor=s.is_anchor,
            )

            control_points.append(cp)

        profiles[bone_name] = BoneProfile(
            bone_name=bone_name,
            bone_pos=tuple(bone_pos),
            bone_rot=bone_rot,
            control_points=control_points,
        )

    with open("bone_profiles.json", "w") as f:
        json.dump({k: asdict(v) for k, v in profiles.items()}, f, indent=4)


if __name__ == "__main__":
    for gender in ["m"]:  # TODO: add "f"
        build_profiles(gender)
