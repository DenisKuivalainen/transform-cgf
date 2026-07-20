from dataclasses import dataclass
import json
from typing import List, Dict
import numpy as np
from pathlib import Path


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
                        old_pos=tuple(cp["old_pos"]),
                        new_pos=tuple(cp["new_pos"]),
                        is_anchor=cp["is_anchor"],
                    )
                    for cp in profile["control_points"]
                ],
            )
            for bone_name, profile in raw.items()
        }

    def get_distance_to_closest_control_point(self, vertex_pos, bone_names, is_dark):
        min_dist = float("inf")

        vertex = np.array([vertex_pos.x, vertex_pos.y, vertex_pos.z], dtype=float)

        for bone_name in bone_names:
            profile = self._profiles.get(bone_name)
            if profile is None:
                continue

            for cp in profile.control_points:
                control_pos = np.array(
                    cp.old_pos if is_dark else cp.new_pos,
                    dtype=float,
                )

                dist = np.linalg.norm(vertex - control_pos)

                if dist < min_dist:
                    min_dist = dist

        return min_dist

    def get_anchors(self, bone_name) -> list[ControlPoint]:
        profile = self._profiles.get(bone_name)

        if profile is None:
            return []

        return [cp for cp in profile.control_points if cp.is_anchor]

    def transform_vertex(
        self,
        vertex_pos: list[float],
        bones: list[VertexBone],
    ) -> list[float]:

        vertex = np.asarray(vertex_pos, dtype=float)

        total_offset = np.zeros(3, dtype=float)

        all_points = []
        bones_to_use = []

        for bone in bones:
            profile = self._profiles.get(bone.bone_name)
            if profile is None or bone.weight <= 0.0:
                continue

            bones_to_use.append(bone)
            all_points.extend(profile.control_points)

        if not bones_to_use or not all_points:
            return vertex_pos.copy()

        for bone in bones_to_use:

            profile = self._profiles[bone.bone_name]

            offset = self._calculate_bone_offset(
                vertex,
                profile,
                all_points,
            )

            total_offset += offset * bone.weight

        return (vertex + total_offset).tolist()

    def _calculate_bone_offset(
        self,
        vertex_world: np.ndarray,
        profile: BoneProfile,
        all_points: list[ControlPoint],
        nearest_count: int = 4,
    ) -> np.ndarray:

        rot = np.asarray(profile.bone_rot, dtype=float)
        bone_pos = np.asarray(profile.bone_pos, dtype=float)

        # vertex in bone-local space
        vertex_local = rot.T @ (vertex_world - bone_pos)

        candidates = []

        for cp in all_points:

            new_local = rot.T @ (np.asarray(cp.new_pos) - bone_pos)

            dist = np.linalg.norm(vertex_local - new_local)

            candidates.append((dist, cp, new_local))

        if not candidates:
            return np.zeros(3)

        candidates.sort(key=lambda x: x[0])

        anchor = None
        for i, (_, cp, _) in enumerate(candidates):
            if cp.is_anchor:
                anchor = candidates.pop(i)
                break

        # ---------------- Anchor ----------------
        anchor_radius = 2

        if anchor is None:
            anchor_k = 0.0
            anchor_local_offset = np.zeros(3)
        else:
            anchor_dist, anchor_cp, anchor_new_local = anchor
            if anchor_dist < 1e-4:
                anchor_local_offset = rot.T @ (
                    np.asarray(anchor_cp.old_pos) - np.asarray(anchor_cp.new_pos)
                )
                anchor_k = 1
            else:
                anchor_dist = min(anchor_dist, anchor_radius)
                anchor_old_local = rot.T @ (np.asarray(anchor_cp.old_pos) - bone_pos)

                anchor_local_offset = anchor_old_local - anchor_new_local
                anchor_k = (anchor_radius - anchor_dist) ** 1.5 / anchor_radius

        # ---------------- Neighbours ----------------

        neighbours = candidates[:nearest_count]

        sigma = 2.0
        eps = 1e-6

        predictions = []
        weights = []

        for dist, cp, new_local in neighbours:

            old_local = rot.T @ (np.asarray(cp.old_pos) - bone_pos)

            # Vertex keeps the same offset relative to this control point.
            prediction = old_local + (vertex_local - new_local)

            predictions.append(prediction)

            w = np.exp(-0.5 * (dist / sigma) ** 2)
            weights.append(w)

        weights = np.asarray(weights)

        weight_sum = weights.sum()

        if weight_sum < eps:
            weights = np.ones(len(weights)) / len(weights)
        else:
            weights /= weight_sum

        predicted_local = np.zeros(3)

        for w, p in zip(weights, predictions):
            predicted_local += w * p

        offset_local = predicted_local - vertex_local
        offset_k = 1 - anchor_k

        return rot @ (anchor_local_offset * anchor_k + offset_local * offset_k)


__all__ = ["Reskin", "VertexBone"]
