from dataclasses import dataclass
import json
from typing import List, Dict
import numpy as np
from pathlib import Path


@dataclass
class ControlPoint:
    local_pos: tuple[float, float, float]
    delta_local: tuple[float, float, float]
    weight: float
    is_anchor: bool


@dataclass
class BoneProfile:
    bone_name: str
    bone_pos: tuple[float, float, float]
    bone_rot: list[list[float]]
    control_points: List[ControlPoint]


@dataclass
class VertexBone:
    bone_name: str
    weight: float


class Reskin:

    def __init__(self, is_hand):
        self._profiles: Dict[str, BoneProfile]
        self._is_hand = is_hand

        profile_path = Path(__file__).resolve().parent / "bone_profiles.json"

        with profile_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        self._profiles = {
            bone_name: BoneProfile(
                bone_name=profile["bone_name"],
                bone_pos=tuple(profile["bone_pos"]),
                bone_rot=profile["bone_rot"],
                control_points=[
                    ControlPoint(
                        local_pos=tuple(cp["local_pos"]),
                        delta_local=tuple(cp["delta_local"]),
                        weight=cp["weight"],
                        is_anchor=cp["is_anchor"],
                    )
                    for cp in profile["control_points"]
                ],
            )
            for bone_name, profile in raw.items()
        }

    _bones_power = {
        "Bip01 L Forearm": 1.3,
        "Bip01 R Forearm": 1.3,
        # "Bip01 L UpperArm": 1.15,
        # "Bip01 R UpperArm": 1.15,
        # "L_ShCustom": 1.15,
        # "R_ShCustom": 1.15,
        # "Bip01 L Clavicle": 1.15,
        # "Bip01 R Clavicle": 1.15,
        # "Bip01 Spine": 1.15,
        # "Bip01 Spine1": 1.15,
        # "Bip01 Pelvis": 1.15,
        # "Bip01 L Thigh": 1.15,
        # "Bip01 R Thigh": 1.15,
        # "Bip01 L Calf": 1.15,
        # "Bip01 R Calf": 1.15,
        # "Bip01 Neck": 1.15,
        # "Bip01 R Foot": 1.15,
        # "Bip01 R Toe0": 1.15,
    }

    def transform_vertex(
        self,
        vertex_pos: list[float],
        bones: list[VertexBone],
    ) -> list[float]:

        vertex = np.asarray(vertex_pos, dtype=float)

        total_offset = np.zeros(3, dtype=float)
        total_weight = 0.0

        for bone in bones:

            profile = self._profiles.get(bone.bone_name)
            if profile is None:
                continue

            weight = bone.weight
            if weight <= 0.0:
                continue

            offset = self._calculate_bone_offset(vertex, profile)

            total_offset += offset * weight
            total_weight += weight

        if total_weight == 0:
            return vertex_pos.copy()

        # if total_weight > 0:
        #     total_offset /= total_weight

        return (vertex + total_offset).tolist()

    def _calculate_bone_offset(
        self,
        vertex_world: np.ndarray,
        profile: BoneProfile,
        nearest_count: int = 5,
        anchor_radius: float = 1.0,
    ) -> np.ndarray:

        rot = np.asarray(profile.bone_rot, dtype=float)
        bone_pos = np.asarray(profile.bone_pos, dtype=float)

        # vertex -> bone local
        vertex_local = rot.T @ (vertex_world - bone_pos)

        distances = []

        for cp in profile.control_points:

            cp_pos = np.asarray(cp.local_pos, dtype=float)

            dist = np.linalg.norm(vertex_local - cp_pos)

            distances.append((dist, cp))

        distances.sort(key=lambda x: x[0])

        if not distances:
            return np.zeros(3, dtype=float)

        # Anchor override
        nearest_dist, nearest_cp = distances[0]

        if nearest_cp.is_anchor and nearest_dist <= anchor_radius:
            delta_local = np.asarray(nearest_cp.delta_local, dtype=float)
            return rot @ delta_local

        # Interpolate nearest N
        neighbours = distances[:nearest_count]

        weights = []
        deltas = []

        eps = 1e-6

        for dist, cp in neighbours:

            # TODO: mb change later
            w = cp.weight / (dist * dist + eps)

            weights.append(w)
            deltas.append(np.asarray(cp.delta_local, dtype=float))

        weight_sum = sum(weights)

        if weight_sum == 0:
            return np.zeros(3, dtype=float)

        delta_local = np.zeros(3, dtype=float)

        for w, delta in zip(weights, deltas):
            delta_local += delta * (w / weight_sum)

        return (rot @ delta_local) * (
            self._bones_power[profile.bone_name]
            if profile.bone_name in self._bones_power and self._is_hand
            else 1
        )


__all__ = ["Reskin", "VertexBone"]
