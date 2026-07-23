from pyffi.formats.cgf import CgfFormat
import re
from pathlib import Path
from math import acos, cos, sin, radians
from reskin.reskin_vertex import Reskin, VertexBone
from typing import Literal


class _TransformCgf:
    _bone_name_map = {
        "Sub_R_bone_skin03": "R_Sup",
        "R_eye_upper_skin": "R_eye_upper",
        "R_eye_under_skin": "R_eye_under",
        "Sub_L_bone_skin03": "L_Sup",
        "L_eye_upper_skin": "L_eye_upper",
        "L_eye_under_skin": "L_eye_under",
        "mouth_R_side_skin": "R_Mouth_side",
        "mouth_L_side_skin": "L_Mouth_side",
        "Bip01": "Bip01",
        "Bip01 Pelvis": "Bip01 Pelvis",
        "Bip01 Spine": "Bip01 Spine",
        "Bip01 Spine1": "Bip01 Spine1",
        "Bip01 Neck": "Bip01 Neck",
        "Bip01 Head": "Bip01 Head",
        "Rear_bone": "Rear_bone",
        "Lear_bone": "Lear_bone",
        "Mouth_bone": "Mouth_bone",
        "mouth_down_skin": "Mouth",
        "FX_H01": "FX_H01",
        "Bip01 L Clavicle": "Bip01 L Clavicle",
        "Bip01 L UpperArm": "Bip01 L UpperArm",
        "Bip01 L Forearm": "Bip01 L Forearm",
        "Bip01 L Hand": "Bip01 L Hand",
        "Bip01 L Finger0": "Bip01 L Finger0",
        "Bip01 L Finger01": "Bip01 L Finger01",
        "Bip01 L Finger1": "Bip01 L Finger1",
        "Bip01 L Finger11": "Bip01 L Finger11",
        "Bip01 L Finger3": "Bip01 L Finger2",
        "Bip01 L Finger31": "Bip01 L Finger21",
        "Lhand_bone": "Lhand_bone",
        "Shield_bone": "Shield_bone",
        "L_Sbone": "L_Sbone",
        "L_ShCustom": "L_ShCustom",
        "Bip01 R Clavicle": "Bip01 R Clavicle",
        "Bip01 R UpperArm": "Bip01 R UpperArm",
        "Bip01 R Forearm": "Bip01 R Forearm",
        "Bip01 R Hand": "Bip01 R Hand",
        "Bip01 R Finger01": "Bip01 R Finger0",
        "Bip01 R Finger02": "Bip01 R Finger01",
        "Bip01 R Finger11": "Bip01 R Finger1",
        "Bip01 R Finger12": "Bip01 R Finger11",
        "Bip01 R Finger31": "Bip01 R Finger2",
        "Bip01 R Finger32": "Bip01 R Finger21",
        "Rhand_bone": "Rhand_bone",
        "R_Sbone": "R_Sbone",
        "R_ShCustom": "R_ShCustom",
        "L_Bust": "L_Bust",
        "R_Bust": "R_Bust",
        "Rback_bone": "Rback_bone",
        "FX_Hit": "FX_Hit",
        "Lback_bone": "Lback_bone",
        "Neck_bone": "Neck_bone",
        "Wing_bone": "Wing_bone",
        "Rhip_bone": "Rhip_bone",
        "Lhip_bone": "Lhip_bone",
        "Back_bone": "Back_bone",
        "Bip01 L Thigh": "Bip01 L Thigh",
        "Bip01 L Calf": "Bip01 L Calf",
        "Bip01 L Foot": "Bip01 L Foot",
        "Bip01 L Toe0": "Bip01 L Toe0",
        "FX_LF01": "FX_LF01",
        "Bip01 R Thigh": "Bip01 R Thigh",
        "Bip01 R Calf": "Bip01 R Calf",
        "Bip01 R Foot": "Bip01 R Foot",
        "Bip01 R Toe0": "Bip01 R Toe0",
        "FX_RF01": "FX_RF01",
        "CL_Bone": "CL_Bone",
        "bone_L3_00": "bone_L3_00",
        "bone_L3_01": "bone_L3_01",
        "bone_L3_02": "bone_L3_02",
        "bone_L3_03": "bone_L3_03",
        "bone_L3_04": "bone_L3_04",
        "bone_L3_05": "bone_L3_05",
        "bone_L1_00": "bone_L1_00",
        "bone_L1_01": "bone_L1_01",
        "bone_L1_02": "bone_L1_02",
        "bone_L1_03": "bone_L1_03",
        "bone_L1_04": "bone_L1_04",
        "bone_L1_05": "bone_L1_05",
        "bone_L2_00": "bone_L2_00",
        "bone_L2_01": "bone_L2_01",
        "bone_L2_02": "bone_L2_02",
        "bone_L2_03": "bone_L2_03",
        "bone_L2_04": "bone_L2_04",
        "bone_L2_05": "bone_L2_05",
        "bone_R2_00": "bone_R2_00",
        "bone_R2_01": "bone_R2_01",
        "bone_R2_02": "bone_R2_02",
        "bone_R2_03": "bone_R2_03",
        "bone_R2_04": "bone_R2_04",
        "bone_R2_05": "bone_R2_05",
        "bone_R3_00": "bone_R3_00",
        "bone_R3_01": "bone_R3_01",
        "bone_R3_02": "bone_R3_02",
        "bone_R3_03": "bone_R3_03",
        "bone_R3_04": "bone_R3_04",
        "bone_R3_05": "bone_R3_05",
        "bone_R1_00": "bone_R1_00",
        "bone_R1_01": "bone_R1_01",
        "bone_R1_02": "bone_R1_02",
        "bone_R1_03": "bone_R1_03",
        "bone_R1_04": "bone_R1_04",
        "bone_R1_05": "bone_R1_05",
        "Rwaist_bone": "Rwaist_bone",
        "Lwaist_bone": "Lwaist_bone",
        "Reye_bone": "Reye_bone",
        "Leye_bone": "Leye_bone",
    }

    _bone_vertex_map = {
        "mouth_down_skin": "Mouth",
        "tongue_skin01": "Bip01 Head",
        "tongue_skin02": "Bip01 Head",
        "tongue_skin03": "Bip01 Head",
        "mouth_up_skin": "Bip01 Head",
        "R_eye_skin": "Bip01 Head",
        "L_eye_skin": "Bip01 Head",
        "mouth_up_skin01": "Bip01 Head",
        "mouth_down_skin01": "Mouth",
        "mouth_down_skin02": "Mouth",
        "mouth_up_skin02": "Bip01 Head",
        "mouth_up_skin03": "Bip01 Head",
        "mouth_down_skin03": "Mouth",
        "Sub_R_bone_skin01": "Bip01 Head",
        "Sub_R_bone_skin02": "R_Sup",
        "Sub_R_bone_skin03": "R_Sup",
        "Sub_R_bone_skin04": "R_Sup",
        "Sub_R_bone_skin05": "R_Sup",
        "Sub_L_bone_skin01": "Bip01 Head",
        "Sub_L_bone_skin02": "R_Sup",
        "Sub_L_bone_skin03": "R_Sup",
        "Sub_L_bone_skin04": "R_Sup",
        "Sub_L_bone_skin05": "R_Sup",
        "L_ball_skin_attch_box": "Bip01 Head",  # not sure
        "R_ball_skin_attch_box": "Bip01 Head",  # not sure
        "Reye_bone": "Bip01 Head",
        "Leye_bone": "Bip01 Head",
        "Bip01 L Finger0": "Bip01 L Finger0",
        "Bip01 L Finger02": "Bip01 L Finger01",
        "Bip01 L Finger1": "Bip01 L Finger1",
        "Bip01 L Finger12": "Bip01 L Finger11",
        "Bip01 L Finger2": "Bip01 L Finger2",
        "Bip01 L Finger22": "Bip01 L Finger21",
        "Bip01 L Finger3": "Bip01 L Finger2",
        "Bip01 L Finger32": "Bip01 L Finger21",
        "Bip01 L Finger4": "Bip01 L Finger2",
        "Bip01 L Finger42": "Bip01 L Finger21",
        "Bip01 R Finger0": "Bip01 R Finger0",
        "Bip01 R Finger02": "Bip01 R Finger01",
        "Bip01 R Finger1": "Bip01 R Finger1",
        "Bip01 R Finger12": "Bip01 R Finger11",
        "Bip01 R Finger2": "Bip01 R Finger2",
        "Bip01 R Finger22": "Bip01 R Finger21",
        "Bip01 R Finger3": "Bip01 R Finger2",
        "Bip01 R Finger32": "Bip01 R Finger21",
        "Bip01 R Finger4": "Bip01 R Finger2",
        "Bip01 R Finger42": "Bip01 R Finger21",
        #
        # not sure about ones below, lets wait for an error
        # "FX_D": "Lwaist_bone",
        # "FX_C": "Lwaist_bone",
        # "FX_A": "Rwaist_bone",
        # "FX_B": "Rwaist_bone",
    }

    def _get_finger0_rotation(self, direction_right: bool, angle: float):
        angle = radians(-angle)

        c = cos(angle)
        s = sin(angle)

        r = CgfFormat.Matrix33()

        r.m_11 = 1.0
        r.m_12 = 0.0
        r.m_13 = 0.0
        r.m_21 = 0.0
        r.m_22 = c
        r.m_23 = -s
        r.m_31 = 0.0
        r.m_32 = s
        r.m_33 = c

        return r

    def _get_finger_rotation(self, direction_right: bool, angle: float):
        angle = radians(angle if direction_right else -angle)

        c = cos(angle)
        s = sin(angle)

        r = CgfFormat.Matrix33()

        r.m_11 = c
        r.m_12 = 0.0
        r.m_13 = s
        r.m_21 = 0.0
        r.m_22 = 1.0
        r.m_23 = 0.0
        r.m_31 = -s
        r.m_32 = 0.0
        r.m_33 = c

        return r

    def _partial_rotation(self, R, factor):
        trace = R.m_11 + R.m_22 + R.m_33
        c = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
        angle = acos(c)

        # Identity
        if abs(angle) < 1e-8:
            M = CgfFormat.Matrix33()
            M.set_identity()
            return M

        s = 2.0 * sin(angle)

        x = (R.m_32 - R.m_23) / s
        y = (R.m_13 - R.m_31) / s
        z = (R.m_21 - R.m_12) / s

        angle *= factor

        c = cos(angle)
        s = sin(angle)
        t = 1.0 - c

        M = CgfFormat.Matrix33()

        M.m_11 = t * x * x + c
        M.m_12 = t * x * y - s * z
        M.m_13 = t * x * z + s * y

        M.m_21 = t * x * y + s * z
        M.m_22 = t * y * y + c
        M.m_23 = t * y * z - s * x

        M.m_31 = t * x * z - s * y
        M.m_32 = t * y * z + s * x
        M.m_33 = t * z * z + c

        return M

    def _move_finder_bones_female(self, names, old_pos, old_rot):
        new_pos = {}
        new_rot = {}

        for _f0, _f1, _f2, _d in [
            [
                "Bip01 R Finger0",
                "Bip01 R Finger01",
                "Bip01 R Finger02",
                "Bip01 R Finger0",
            ],
            [
                "Bip01 R Finger1",
                "Bip01 R Finger11",
                "Bip01 R Finger12",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 R Finger2",
                "Bip01 R Finger21",
                "Bip01 R Finger22",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 R Finger3",
                "Bip01 R Finger31",
                "Bip01 R Finger32",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 R Finger4",
                "Bip01 R Finger41",
                "Bip01 R Finger42",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 L Finger0",
                "Bip01 L Finger01",
                "Bip01 L Finger02",
                "Bip01 L Finger0",
            ],
            [
                "Bip01 L Finger1",
                "Bip01 L Finger11",
                "Bip01 L Finger12",
                "Bip01 L Finger2",
            ],
            [
                "Bip01 L Finger2",
                "Bip01 L Finger21",
                "Bip01 L Finger22",
                "Bip01 L Finger2",
            ],
            [
                "Bip01 L Finger3",
                "Bip01 L Finger31",
                "Bip01 L Finger32",
                "Bip01 L Finger2",
            ],
            [
                "Bip01 L Finger4",
                "Bip01 L Finger41",
                "Bip01 L Finger42",
                "Bip01 L Finger2",
            ],
        ]:
            f0 = next(k for k, v in names.items() if v == _f0)
            f1 = next(k for k, v in names.items() if v == _f1)
            f2 = next(k for k, v in names.items() if v == _f2)
            d = old_rot[next(k for k, v in names.items() if v == _d)]

            delta_rot_f0_f1 = old_rot[f0].get_transpose() * old_rot[f1]
            delta_rot_f1_f2 = old_rot[f1].get_transpose() * old_rot[f2]

            new_pos[f0] = old_pos[f0].get_copy()
            new_rot[f0] = d.get_copy()

            angle = 20
            length_modifier = 1.25
            if "Finger0" in _f0:
                angle = 0
                length_modifier = 1.15
            elif "Finger4" in _f0:
                length_modifier = 1.15
            elif "Finger1" in _f0:
                length_modifier = 1.35
                angle = 15

            additional_rot = self._get_finger_rotation(" R " in _d, angle)

            new_rot[f1] = new_rot[f0] * delta_rot_f0_f1 * additional_rot
            new_pos[f1] = (
                new_pos[f0]
                + (
                    length_modifier
                    * (old_pos[f1] - old_pos[f0])
                    * old_rot[f0].get_transpose()
                )
                * new_rot[f0]
            )

            new_rot[f2] = new_rot[f1] * delta_rot_f1_f2 * additional_rot
            new_pos[f2] = (
                new_pos[f1]
                + (
                    length_modifier
                    * (old_pos[f2] - old_pos[f1])
                    * old_rot[f1].get_transpose()
                )
                * new_rot[f1]
            )

        return new_pos, new_rot

    def _move_finder_bones_male(self, names, old_pos, old_rot):
        new_pos = {}
        new_rot = {}

        for _f0, _f1, _f2, _d in [
            [
                "Bip01 R Finger0",
                "Bip01 R Finger01",
                "Bip01 R Finger02",
                "Bip01 R Finger0",
            ],
            [
                "Bip01 R Finger1",
                "Bip01 R Finger11",
                "Bip01 R Finger12",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 R Finger2",
                "Bip01 R Finger21",
                "Bip01 R Finger22",
                "Bip01 R Finger3",
            ],
            [
                "Bip01 R Finger3",
                "Bip01 R Finger31",
                "Bip01 R Finger32",
                "Bip01 R Finger2",
            ],
            [
                "Bip01 R Finger4",
                "Bip01 R Finger41",
                "Bip01 R Finger42",
                "Bip01 R Finger3",
            ],
            [
                "Bip01 L Finger0",
                "Bip01 L Finger01",
                "Bip01 L Finger02",
                "Bip01 L Finger0",
            ],
            [
                "Bip01 L Finger1",
                "Bip01 L Finger11",
                "Bip01 L Finger12",
                "Bip01 L Finger2",
            ],
            [
                "Bip01 L Finger2",
                "Bip01 L Finger21",
                "Bip01 L Finger22",
                "Bip01 L Finger3",
            ],
            [
                "Bip01 L Finger3",
                "Bip01 L Finger31",
                "Bip01 L Finger32",
                "Bip01 L Finger2",
            ],
            [
                "Bip01 L Finger4",
                "Bip01 L Finger41",
                "Bip01 L Finger42",
                "Bip01 L Finger3",
            ],
        ]:
            f0 = next(k for k, v in names.items() if v == _f0)
            f1 = next(k for k, v in names.items() if v == _f1)
            f2 = next(k for k, v in names.items() if v == _f2)
            d = old_rot[next(k for k, v in names.items() if v == _d)]

            angle0 = 5
            angle1 = 10
            angle2 = 30
            length_modifier = 1.05
            factor = 1
            if "Finger1" in _f0:
                angle0 = 0
                angle1 = 5
                angle2 = 5
                factor = 5.0 / 9.0
            elif "Finger2" in _f0:
                angle0 = 25
                angle1 = 10
                angle2 = 25
                factor = 2.0 / 9.0
            elif "Finger3" in _f0:
                length_modifier = 0.95
                angle0 = 10
                angle1 = 5
                angle2 = 5
                factor = 4.0 / 9.0
            elif "Finger4" in _f0:
                length_modifier = 1
                angle0 = 5
                angle1 = 10
                angle2 = 10
                factor = 1
            elif "Finger0" in _f0:
                angle0 = 0
                length_modifier = 1.15
                factor = 2.0 / 3.0

            is_right_hand = " R " in _d

            delta_rot_f0_f1 = old_rot[f0].get_transpose() * old_rot[f1]
            delta_rot_f1_f2 = old_rot[f1].get_transpose() * old_rot[f2]

            new_pos[f0] = old_pos[f0].get_copy()
            new_rot[f0] = old_rot[f0] * self._partial_rotation(
                old_rot[f0].get_transpose()
                * (
                    d
                    if "Finger0" not in _f0
                    else self._template_bone_initial_chunk.initial_pos_matrices[
                        [n for n in self._template_bone_name_chunk.names].index(_f0)
                    ].rot
                )
                * self._get_finger_rotation(is_right_hand, angle0),
                factor,
            )

            new_rot[f1] = (
                new_rot[f0]
                * delta_rot_f0_f1
                * (
                    self._get_finger_rotation(is_right_hand, angle1)
                    if "Finger0" not in _f0
                    else self._get_finger0_rotation(True, 10)
                )
            )
            new_pos[f1] = (
                new_pos[f0]
                + (
                    length_modifier
                    * (old_pos[f1] - old_pos[f0])
                    * (
                        old_rot[f0] if "Finger0" not in _f0 else new_rot[f0]
                    ).get_transpose()
                )
                * new_rot[f0]
            )

            new_rot[f2] = (
                new_rot[f1]
                * delta_rot_f1_f2
                * (
                    self._get_finger_rotation(is_right_hand, angle2)
                    if "Finger0" not in _f0
                    else self._get_finger0_rotation(is_right_hand, -30)
                    * self._get_finger_rotation(is_right_hand, 20)
                )
            )
            new_pos[f2] = (
                new_pos[f1]
                + (
                    length_modifier
                    * (old_pos[f2] - old_pos[f1])
                    * old_rot[f1].get_transpose()
                )
                * new_rot[f1]
            )

        return new_pos, new_rot

    def _reposition_fingers(self):
        names = {}
        old_pos = {}
        old_rot = {}

        for i, name in enumerate(self._bone_name_chunk.names):
            if "Finger" in name:
                names[i] = name
                old_pos[i] = self._bone_initial_chunk.initial_pos_matrices[i].pos
                old_rot[i] = self._bone_initial_chunk.initial_pos_matrices[i].rot

        new_pos, new_rot = (
            self._move_finder_bones_male
            if self._is_male
            else self._move_finder_bones_female
        )(names, old_pos, old_rot)

        for key, value in old_pos.items():
            if key not in new_pos:
                new_pos[key] = value.get_copy()
                new_rot[key] = old_rot[key].get_copy()

        vertex_pos_delta = {}
        for i, vertex_weight in enumerate(self._vertex_chunk.vertex_weights):
            if any(link.bone in names for link in vertex_weight.bone_links):
                delta = CgfFormat.Vector3()
                delta.x = 0
                delta.y = 0
                delta.z = 0

                for link in vertex_weight.bone_links:
                    if link.bone not in names:
                        continue
                    bone = link.bone

                    local = (
                        self._vertex_chunk.vertices[i].p - old_pos[bone]
                    ) * old_rot[bone].get_transpose()
                    transformed = local * new_rot[bone] + new_pos[bone]
                    delta += (
                        transformed - self._vertex_chunk.vertices[i].p
                    ) * link.blending

                local = (self._vertex_chunk.vertices[i].p - old_pos[bone]) * old_rot[
                    bone
                ].get_transpose()
                vertex_pos_delta[i] = delta

        for key, value in vertex_pos_delta.items():
            self._vertex_chunk.vertices[key].p = (
                self._vertex_chunk.vertices[key].p + value
            )

        for key, value in names.items():
            self._bone_initial_chunk.initial_pos_matrices[key].pos = new_pos[key]
            self._bone_initial_chunk.initial_pos_matrices[key].rot = new_rot[key]

    def _read_data(self, file_name, input_folder):
        with open(input_folder + file_name, "rb") as caf:
            data = CgfFormat.Data()
            try:
                data.inspect_version_only(caf)
            except ValueError as e:
                print(e)

            try:
                data.read(caf)
            except:
                raise

        return data

    def _write_data(self):
        input_path = Path(self._input)

        if self._output is None:
            out_dir = input_path.parent / "transform_output"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / input_path.name
        else:
            output_path = Path(self._output)

            if output_path.suffix.lower() == ".cgf":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                out_file = output_path
            else:
                output_path.mkdir(parents=True, exist_ok=True)
                out_file = output_path / input_path.name

        with open(out_file, "wb") as f:
            self._data.write(f)

    def _find_chunks(self, data):
        bone_name_chunk = None
        bone_anim_chunk = None
        bone_initial_chunk = None
        vertex_chunk = None

        for i, chunk in enumerate(data.chunks):
            if isinstance(chunk, CgfFormat.SourceInfoChunk):
                chunk.author += bytes.fromhex(
                    "207C205472616E73666F726D65642062792044656E6973204B756976616C61696E656E"
                ).decode("ascii")
            elif isinstance(chunk, CgfFormat.BoneNameListChunk):
                bone_name_chunk = chunk
            elif isinstance(chunk, CgfFormat.BoneAnimChunk):
                bone_anim_chunk = chunk
            elif isinstance(chunk, CgfFormat.BoneInitialPosChunk):
                bone_initial_chunk = chunk
            elif isinstance(chunk, CgfFormat.MeshChunk) and chunk.has_vertex_weights:
                vertex_chunk = chunk

        return (
            bone_name_chunk,
            bone_anim_chunk,
            bone_initial_chunk,
            vertex_chunk,
        )

    def _calculate_bone_offset(self):
        offsets = []

        for n, _v in enumerate(self._vertex_chunk.vertices):
            for m, _bl in enumerate(self._vertex_chunk.vertex_weights[n].bone_links):
                bone_rot = self._bone_initial_chunk.initial_pos_matrices[
                    self._vertex_chunk.vertex_weights[n].bone_links[m].bone
                ].rot
            bone_pos = self._bone_initial_chunk.initial_pos_matrices[
                self._vertex_chunk.vertex_weights[n].bone_links[m].bone
            ].pos
            offset = self._vertex_chunk.vertex_weights[n].bone_links[m].offset
            vertex_pos = self._vertex_chunk.vertices[n].p

            if self._vertex_chunk.vertex_weights[n].bone_links[m].blending == 0:
                continue

            offsets.append(vertex_pos - (bone_pos + offset * bone_rot))

        avg = CgfFormat.Vector3()
        for v in offsets:
            avg += v

        avg.x = avg.x / len(offsets)
        avg.y = avg.y / len(offsets)
        avg.z = avg.z / len(offsets)

        self._bone_offset = avg

    def _transform_cgf(self):
        index_mapping = {}
        new_names = [n for n in self._template_bone_name_chunk.names]
        new_bones = [None] * len(new_names)
        new_matrices = [None] * len(new_names)

        old_names = []
        old_pos = []
        old_rot = []

        for index, name in enumerate(self._bone_name_chunk.names):
            old_names.append(name)
            old_pos.append(
                self._bone_initial_chunk.initial_pos_matrices[index].pos.get_copy()
            )
            old_rot.append(
                self._bone_initial_chunk.initial_pos_matrices[index].rot.get_copy()
            )

            if (
                name in self._bone_name_map
                and self._bone_name_map[name] in self._template_bone_name_chunk.names
            ):
                curr_index = new_names.index(self._bone_name_map[name])
                index_mapping[index] = curr_index

                bone = self._bone_anim_chunk.bones[index]
                bone.bone_id = curr_index
                bone.parent_id = self._template_bone_anim_chunk.bones[
                    curr_index
                ].parent_id
                bone.num_children = self._template_bone_anim_chunk.bones[
                    curr_index
                ].num_children
                bone.bone_name_crc_32 = self._template_bone_anim_chunk.bones[
                    curr_index
                ].bone_name_crc_32
                new_bones[curr_index] = bone

                matrice = self._bone_initial_chunk.initial_pos_matrices[index]
                if "Finger" in name:
                    matrice.rot = (
                        self._template_bone_initial_chunk.initial_pos_matrices[
                            curr_index
                        ].rot
                    )
                    matrice.pos = (
                        self._template_bone_initial_chunk.initial_pos_matrices[
                            curr_index
                        ].pos
                    )
                new_matrices[curr_index] = matrice

        for _f0, _f1, _d in [
            ["Bip01 R Finger0", "Bip01 R Finger01", "Bip01 R Finger0"],
            ["Bip01 R Finger1", "Bip01 R Finger11", "Bip01 R Finger1"],
            ["Bip01 L Finger0", "Bip01 L Finger01", "Bip01 L Finger0"],
            ["Bip01 L Finger1", "Bip01 L Finger11", "Bip01 L Finger1"],
        ]:
            f0 = new_names.index(_f0)
            f1 = new_names.index(_f1)
            d = old_rot[old_names.index(_d)]

            delta_rot_f0_f1 = (
                new_matrices[f0].rot.get_transpose() * new_matrices[f1].rot
            )

            new_matrices[f0].pos = (
                self._template_bone_initial_chunk.initial_pos_matrices[
                    f0
                ].pos.get_copy()
            )
            new_matrices[f0].rot = d.get_copy()

            new_matrices[f1].rot = new_matrices[f0].rot * delta_rot_f0_f1
            new_matrices[f1].pos = (
                new_matrices[f0].pos
                + (
                    (
                        self._template_bone_initial_chunk.initial_pos_matrices[f1].pos
                        - self._template_bone_initial_chunk.initial_pos_matrices[f0].pos
                    )
                    * self._template_bone_initial_chunk.initial_pos_matrices[
                        f0
                    ].rot.get_transpose()
                )
                * new_matrices[f0].rot
            )

        for vertex_index, vertex_weight in enumerate(self._vertex_chunk.vertex_weights):
            # change finger3 and finger4 to finger2
            for link in vertex_weight.bone_links:
                bone_name = self._bone_name_chunk.names[link.bone]

                m = re.search(r"Finger([34])$", bone_name)
                if not m:
                    continue

                new_bone_name = bone_name.replace(f"Finger{m.group(1)}", "Finger2")
                link.bone = old_names.index(new_bone_name)

            # merge repeated links
            merged = {}
            for link in vertex_weight.bone_links:
                if link.bone in merged:
                    merged[link.bone].blending += link.blending
                else:
                    new_link = CgfFormat.BoneLink()
                    new_link.bone = link.bone
                    new_link.blending = link.blending
                    merged[link.bone] = new_link

            while vertex_weight.bone_links:
                vertex_weight.bone_links.pop()

            for link in merged.values():
                vertex_weight.bone_links.append(link)

            # Normalize dominant hand/finger weights
            handled = False
            for finger in range(5):
                hand_idx = next(
                    (
                        i
                        for i, l in enumerate(vertex_weight.bone_links)
                        if self._bone_name_chunk.names[l.bone].endswith("Hand")
                    ),
                    None,
                )

                idx0 = next(
                    (
                        i
                        for i, l in enumerate(vertex_weight.bone_links)
                        if self._bone_name_chunk.names[l.bone].endswith(
                            f"Finger{finger}"
                        )
                    ),
                    None,
                )

                idx1 = next(
                    (
                        i
                        for i, l in enumerate(vertex_weight.bone_links)
                        if self._bone_name_chunk.names[l.bone].endswith(
                            f"Finger{finger}1"
                        )
                    ),
                    None,
                )

                idx2 = next(
                    (
                        i
                        for i, l in enumerate(vertex_weight.bone_links)
                        if self._bone_name_chunk.names[l.bone].endswith(
                            f"Finger{finger}2"
                        )
                    ),
                    None,
                )

                # Hand + FingerN
                if hand_idx is not None and idx0 is not None:
                    hand = vertex_weight.bone_links[hand_idx]
                    finger0 = vertex_weight.bone_links[idx0]

                    total = hand.blending + finger0.blending

                    if total > 0.75:
                        finger_total = sum(
                            l.blending
                            for l in vertex_weight.bone_links
                            if re.search(
                                r"Finger\d$",
                                self._bone_name_chunk.names[l.bone],
                            )
                        )

                        new_links = []

                        new_hand = CgfFormat.BoneLink()
                        new_hand.bone = hand.bone
                        new_hand.blending = 0.5
                        new_links.append(new_hand)

                        for l in vertex_weight.bone_links:
                            if not re.search(
                                r"Finger\d$",
                                self._bone_name_chunk.names[l.bone],
                            ):
                                continue

                            new_link = CgfFormat.BoneLink()
                            new_link.bone = l.bone
                            new_link.blending = (
                                l.blending / finger_total * 0.5
                                if finger_total > 0
                                else 0
                            )
                            new_links.append(new_link)

                        while vertex_weight.bone_links:
                            vertex_weight.bone_links.pop()

                        for link in new_links:
                            vertex_weight.bone_links.append(link)
                        handled = True
                        break

                # FingerN + FingerN1
                if idx0 is not None and idx1 is not None:
                    blend = (
                        vertex_weight.bone_links[idx0].blending
                        + vertex_weight.bone_links[idx1].blending
                    )

                    if blend > 0.75:
                        bone2 = old_names.index(
                            self._bone_name_chunk.names[
                                vertex_weight.bone_links[idx1].bone
                            ].replace(f"Finger{finger}1", f"Finger{finger}2")
                        )

                        link0 = CgfFormat.BoneLink()
                        link0.bone = vertex_weight.bone_links[idx0].bone
                        link0.blending = 0.5

                        link2 = CgfFormat.BoneLink()
                        link2.bone = bone2
                        link2.blending = 0.5

                        while vertex_weight.bone_links:
                            vertex_weight.bone_links.pop()

                        vertex_weight.bone_links.append(link0)
                        vertex_weight.bone_links.append(link2)
                        handled = True
                        break

                # FingerN1 + FingerN2
                if idx1 is not None and idx2 is not None:
                    blend = (
                        vertex_weight.bone_links[idx1].blending
                        + vertex_weight.bone_links[idx2].blending
                    )

                    if blend > 0.75:
                        link2 = CgfFormat.BoneLink()
                        link2.bone = vertex_weight.bone_links[idx2].bone
                        link2.blending = 1.0

                        while vertex_weight.bone_links:
                            vertex_weight.bone_links.pop()

                        vertex_weight.bone_links.append(link2)
                        handled = True
                        break

                if handled:
                    continue

            # remove all left Finger1 links
            while any(
                re.compile(r"Finger(\d)1").search(
                    self._bone_name_chunk.names[link.bone]
                )
                for link in vertex_weight.bone_links
            ):
                for i, link in enumerate(list(vertex_weight.bone_links)):
                    bone_name = self._bone_name_chunk.names[link.bone]

                    m = re.search(r"Finger(\d)1", bone_name)
                    if not m:
                        continue

                    finger = m.group(1)

                    while (
                        i < len(vertex_weight.bone_links)
                        and vertex_weight.bone_links[i].bone == link.bone
                    ):
                        vertex_weight.bone_links.pop(i)

                    # cuz splitting into n and n2 looks like shit
                    bone0 = old_names.index(
                        bone_name.replace(f"Finger{finger}1", f"Finger{finger}")
                    )
                    bone2 = old_names.index(
                        bone_name.replace(f"Finger{finger}1", f"Finger{finger}2")
                    )

                    for bone in (bone0, bone2):
                        new_link = CgfFormat.BoneLink()
                        new_link.bone = bone
                        new_link.blending = link.blending * 0.5

                        vertex_weight.bone_links.append(new_link)

            while any(link.blending == 0 for link in vertex_weight.bone_links):
                for i, link in enumerate(vertex_weight.bone_links):
                    if link.blending == 0:
                        vertex_weight.bone_links.pop(i)

            for link in vertex_weight.bone_links:
                new_bone = 0
                if link.bone in index_mapping:
                    new_bone = index_mapping[link.bone]
                elif self._bone_name_chunk.names[link.bone] in self._bone_vertex_map:
                    new_bone = new_names.index(
                        self._bone_vertex_map[self._bone_name_chunk.names[link.bone]]
                    )
                else:
                    raise RuntimeError(
                        f"Vertex references removed bone index {link.bone} - {old_names[link.bone]}"
                    )
                link.bone = new_bone

            new_links = {}
            for link in vertex_weight.bone_links:
                if link.bone in new_links:
                    new_links[link.bone].blending += link.blending
                else:
                    new_links[link.bone] = link

            vertex_weight.bone_links.clear()
            for link in new_links.values():
                vertex_weight.bone_links.append(link)
            vertex_weight.num_bone_links = len(vertex_weight.bone_links)

            if len(vertex_weight.bone_links) > 0:
                other_sum = sum(link.blending for link in vertex_weight.bone_links[1:])
                vertex_weight.bone_links[0].blending = 1.0 - other_sum

        # following might be updated cuz bones and matrices are links, but since it works I will not refactor that
        for index, name in enumerate(new_names):
            self._bone_name_chunk.names[index] = name
        while len(new_names) != len(self._bone_name_chunk.names):
            self._bone_name_chunk.names.pop(len(new_names))
        self._bone_name_chunk.num_names = len(self._bone_name_chunk.names)

        self._bone_anim_chunk.bones.clear()
        for bone in new_bones:
            self._bone_anim_chunk.bones.append(bone)
        self._bone_anim_chunk.num_bones = len(self._bone_anim_chunk.bones)

        self._bone_initial_chunk.initial_pos_matrices.clear()
        for matrice in new_matrices:
            self._bone_initial_chunk.initial_pos_matrices.append(matrice)
        self._bone_initial_chunk.num_bones = len(
            self._bone_initial_chunk.initial_pos_matrices
        )

    def _validate_data(self):
        if self._bone_name_chunk.num_names == self._template_bone_name_chunk.num_names:
            raise ValueError(f"{self._input} is already in old format.")
        if self._bone_name_chunk.num_names < 100:
            raise ValueError(f"{self._input} is not a PC model.")

    def _reskin_mesh(self):
        file_name = Path(self._input).name.lower()
        self._reskin = Reskin("hand" in file_name, self._is_male)

        if not self._is_dark:
            return

        for i, vertex in enumerate(self._vertex_chunk.vertices):

            [x, y, z] = self._reskin.transform_vertex(
                [vertex.p.x, vertex.p.y, vertex.p.z],
                [
                    VertexBone(self._bone_name_chunk.names[link.bone], link.blending)
                    for link in self._vertex_chunk.vertex_weights[i].bone_links
                ],
            )

            vertex.p.x = x
            vertex.p.y = y
            vertex.p.z = z

    def _calculate_vertex_link_offset(self):
        for i, vertex in enumerate(self._vertex_chunk.vertices):
            for link in self._vertex_chunk.vertex_weights[i].bone_links:
                link.offset = (
                    vertex.p
                    - self._bone_initial_chunk.initial_pos_matrices[link.bone].pos
                    - self._bone_offset
                ) * self._bone_initial_chunk.initial_pos_matrices[
                    link.bone
                ].rot.get_transpose()

    _EPSILON = 1e-2

    def _is_hand_anchor(self, vertex, hand_anchors) -> bool:

        return any(
            abs(vertex.p.x - x) <= self._EPSILON
            and abs(vertex.p.y - y) <= self._EPSILON
            and abs(vertex.p.z - z) <= self._EPSILON
            for x, y, z in hand_anchors
        )

    def _transform_gloves(self):
        if not self._is_male:
            return

        file_name = Path(self._input).name.lower()
        if "hand" not in file_name:
            return

        hand_anchors = [
            cp.old_pos if self._is_dark else cp.new_pos
            for cp in [
                *self._reskin.get_anchors("Bip01 L Forearm"),
                *self._reskin.get_anchors("Bip01 R Forearm"),
            ]
        ]
        processed_vertices = []
        close_to_anchors = any(
            self._is_hand_anchor(v, hand_anchors) for v in self._vertex_chunk.vertices
        )

        hand_bones_names = [
            "Bip01 L Forearm",
            "Bip01 R Forearm",
            "Bip01 L UpperArm",
            "Bip01 R UpperArm",
        ]

        for i, vertex in enumerate(self._vertex_chunk.vertices):
            v = {}

            if close_to_anchors:
                v["old"] = vertex.p
                v["new"] = vertex.p
                processed_vertices.append(v)
                continue

            _v = next(
                (
                    p
                    for p in processed_vertices
                    if (vertex.p - p["old"]).norm() <= self._EPSILON
                ),
                None,
            )

            if _v is not None:
                vertex.p = _v["new"]
            else:
                v["old"] = vertex.p

                weight = sum(
                    (
                        link.blending
                        if self._bone_name_chunk.names[link.bone] in hand_bones_names
                        else 0
                    )
                    for link in self._vertex_chunk.vertex_weights[i].bone_links
                )
                if vertex.p.z < 130:
                    if not close_to_anchors:
                        m = 15
                        k = 1 / m
                        vertex.p += (
                            vertex.n
                            * weight
                            * (
                                m
                                - min(
                                    self._reskin.get_distance_to_closest_control_point(
                                        vertex.p, hand_bones_names, self._is_dark
                                    ),
                                    m,
                                )
                            )
                            * k
                        )
                    else:
                        vertex.p += (
                            vertex.n
                            * weight
                            * max(0.0, min(1.0, (vertex.p.z - 110.0) / (120.0 - 110.0)))
                        )

                v["new"] = vertex.p
                processed_vertices.append(v)

    def __init__(
        self,
        input: str,
        output: str | None = None,
        input_folder: str | None = "",
        model: str | None = "lm",
    ):
        self._input = input
        self._output = output
        self._input_folder = input_folder
        self._model = model

        self._is_male = model[1] == "m"
        self._is_dark = model[0] == "d"

        # read template data for old sceleton
        template_data = self._read_data(f"templates/template{model}.cgf", "./")
        (
            self._template_bone_name_chunk,
            self._template_bone_anim_chunk,
            self._template_bone_initial_chunk,
            self._template_vertex_chunk,
        ) = self._find_chunks(template_data)

        self._data = self._read_data(input, input_folder)

        (
            self._bone_name_chunk,
            self._bone_anim_chunk,
            self._bone_initial_chunk,
            self._vertex_chunk,
        ) = self._find_chunks(self._data)

        self._validate_data()

        # Each bone has an offset.
        # It is almost same, but I cannot find how it is calculated.
        # So the best solution I came to was find avg of all offsets.
        # Since it does not affect texture due - it is ok.
        self._calculate_bone_offset()

        # In 5.x+ there are 5 fingers, not 3 as before.
        # Since we downgrade model, we need to reposition fingers to look properly with animations.
        self._reposition_fingers()

        # Basic sceleton transformation from new model to old one.
        self._transform_cgf()

        # In 5.x+ asmo end elyos have same model, but on older versions not.
        # The idea is to sransform skin to fit old asmo model
        self._reskin_mesh()

        # In 5.x+ characters have less buffed hands than on older versions.
        # The idea is to scale gloves to fit old model (skin and gloves surfaces should not overlap).
        self._transform_gloves()

        self._calculate_vertex_link_offset()

        self._write_data()


def transform_cgf(
    input: str,
    output: str | None = None,
    input_folder: str | None = "",
    model: Literal["lf", "df", "lm", "dm"] | None = "lm",
):
    """
    Transforms PC Aion models from patch 5.x and later to a format used by earlier patches.

    Args:
    * input:
        Original .cgf file name from patch 5.x or later that will be transformed.

    * output:
        Path to either the output directory or the output `.cgf` file.
        If a directory is specified, the transformed file will be written there
        using the original filename. If a `.cgf` file is specified, it will be
        used as the exact output path.
        If not specified, a directory named `transform_output` will be created
        in the same directory as the original file.

    * input_folder:
        Path to directory with original file

    * model:
        lm, dm, lf, df
    """

    try:
        _TransformCgf(input, output, input_folder, model)
    except ValueError as e:
        print(f"{e}")


__all__ = ["transform_cgf"]
