from pyffi.formats.cgf import CgfFormat
import re
from pathlib import Path

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
    #
    # mb remove following
    # "Bip01 L Finger01": "Bip01 L Finger0",
    # "Bip01 L Finger11": "Bip01 L Finger1",
    # "Bip01 L Finger21": "Bip01 L Finger1",
    # "Bip01 L Finger31": "Bip01 L Finger2",
    # "Bip01 L Finger41": "Bip01 L Finger2",
    # "Bip01 R Finger01": "Bip01 R Finger0",
    # "Bip01 R Finger11": "Bip01 R Finger1",
    # "Bip01 R Finger21": "Bip01 R Finger1",
    # "Bip01 R Finger31": "Bip01 R Finger2",
    # "Bip01 R Finger41": "Bip01 R Finger2",
}


def _reposition_fingers(bone_name_chunk, bone_initial_chunk, vertex_chunk):
    names = {}
    old_pos = {}
    old_rot = {}
    new_pos = {}
    new_rot = {}

    for i, name in enumerate(bone_name_chunk.names):
        if "Finger" in name and "Finger0" not in name:
            names[i] = name
            old_pos[i] = bone_initial_chunk.initial_pos_matrices[i].pos
            old_rot[i] = bone_initial_chunk.initial_pos_matrices[i].rot

    for _f0, _f1, _f2, _d in [
        ["Bip01 R Finger1", "Bip01 R Finger11", "Bip01 R Finger12", "Bip01 R Finger2"],
        ["Bip01 R Finger3", "Bip01 R Finger31", "Bip01 R Finger32", "Bip01 R Finger2"],
        ["Bip01 R Finger4", "Bip01 R Finger41", "Bip01 R Finger42", "Bip01 R Finger2"],
        ["Bip01 L Finger1", "Bip01 L Finger11", "Bip01 L Finger12", "Bip01 L Finger2"],
        ["Bip01 L Finger3", "Bip01 L Finger31", "Bip01 L Finger32", "Bip01 L Finger2"],
        ["Bip01 L Finger4", "Bip01 L Finger41", "Bip01 L Finger42", "Bip01 L Finger2"],
    ]:
        f0 = next(k for k, v in names.items() if v == _f0)
        f1 = next(k for k, v in names.items() if v == _f1)
        f2 = next(k for k, v in names.items() if v == _f2)
        d = old_rot[next(k for k, v in names.items() if v == _d)]

        delta_rot_f0_f1 = old_rot[f0].get_transpose() * old_rot[f1]
        delta_rot_f1_f2 = old_rot[f1].get_transpose() * old_rot[f2]

        new_pos[f0] = old_pos[f0].get_copy()
        new_rot[f0] = d.get_copy()

        new_rot[f1] = new_rot[f0] * delta_rot_f0_f1
        new_pos[f1] = (
            new_pos[f0]
            + ((old_pos[f1] - old_pos[f0]) * old_rot[f0].get_transpose()) * new_rot[f0]
        )

        new_rot[f2] = new_rot[f1] * delta_rot_f1_f2
        new_pos[f2] = (
            new_pos[f1]
            + ((old_pos[f2] - old_pos[f1]) * old_rot[f1].get_transpose()) * new_rot[f1]
        )

    for key, value in old_pos.items():
        if key not in new_pos:
            new_pos[key] = value.get_copy()
            new_rot[key] = old_rot[key].get_copy()

    vertex_pos_delta = {}
    for i, vertex_weight in enumerate(vertex_chunk.vertex_weights):
        if any(link.bone in names for link in vertex_weight.bone_links):
            delta = CgfFormat.Vector3()
            delta.x = 0
            delta.y = 0
            delta.z = 0

            for link in vertex_weight.bone_links:
                if link.bone not in names:
                    continue
                bone = link.bone

                local = (vertex_chunk.vertices[i].p - old_pos[bone]) * old_rot[
                    bone
                ].get_transpose()
                transformed = local * new_rot[bone] + new_pos[bone]
                delta += (transformed - vertex_chunk.vertices[i].p) * link.blending

            local = (vertex_chunk.vertices[i].p - old_pos[bone]) * old_rot[
                bone
            ].get_transpose()
            vertex_pos_delta[i] = delta

    for key, value in vertex_pos_delta.items():
        vertex_chunk.vertices[key].p = vertex_chunk.vertices[key].p + value

    for key, value in names.items():
        bone_initial_chunk.initial_pos_matrices[key].pos = new_pos[key]
        bone_initial_chunk.initial_pos_matrices[key].rot = new_rot[key]


def _calculate_vertex_offset(
    cur_offset, curr_bone_pos, curr_bone_rot, new_bone_pos, new_bone_rot
):
    # Local (old bone) -> world
    wx = (
        curr_bone_rot.m_11 * cur_offset.x
        + curr_bone_rot.m_12 * cur_offset.y
        + curr_bone_rot.m_13 * cur_offset.z
        + curr_bone_pos.x
    )
    wy = (
        curr_bone_rot.m_21 * cur_offset.x
        + curr_bone_rot.m_22 * cur_offset.y
        + curr_bone_rot.m_23 * cur_offset.z
        + curr_bone_pos.y
    )
    wz = (
        curr_bone_rot.m_31 * cur_offset.x
        + curr_bone_rot.m_32 * cur_offset.y
        + curr_bone_rot.m_33 * cur_offset.z
        + curr_bone_pos.z
    )

    # Translate relative to new bone
    wx -= new_bone_pos.x
    wy -= new_bone_pos.y
    wz -= new_bone_pos.z

    # Apply transpose(new rotation) = inverse(new rotation)
    result = cur_offset.get_copy()

    result.x = new_bone_rot.m_11 * wx + new_bone_rot.m_21 * wy + new_bone_rot.m_31 * wz
    result.y = new_bone_rot.m_12 * wx + new_bone_rot.m_22 * wy + new_bone_rot.m_32 * wz
    result.z = new_bone_rot.m_13 * wx + new_bone_rot.m_23 * wy + new_bone_rot.m_33 * wz

    return result


def _read_data(file_name):
    with open(file_name, "rb") as caf:
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


def _write_data(file_name, data, output_folder=None):
    path = Path(file_name)

    if output_folder is not None:
        out_dir = Path(output_folder)
    else:
        out_dir = path.parent / "transform_output"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / path.name

    with open(out_file, "wb") as f:
        data.write(f)


def _find_chunks(data):
    bone_name_chunk = None
    bone_anim_chunk = None
    bone_initial_chunk = None
    vertex_chunk = None

    for chunk in data.chunks:
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


def transform_cgf(input_file: str, output_folder: str | None = None):
    """
    Transforms PC Aion models from patch 5.x and later to formats used by earlier patches.

    Args:
    * input_file:
    Path to the original .cgf file from patch 5.x or later that will be transformed.

    * output_folder:
        Path to the directory where the transformed file will be written.
        If not specified, a directory named `transform_output` will be created in the same directory as the original file.

    """
    template_data = _read_data(f"./template{input_file[:2].lower()}.cgf")
    (
        template_bone_name_chunk,
        template_bone_anim_chunk,
        template_bone_initial_chunk,
        template_vertex_chunk,
    ) = _find_chunks(template_data)

    data = _read_data(input_file)

    bone_name_chunk, bone_anim_chunk, bone_initial_chunk, vertex_chunk = _find_chunks(
        data
    )

    if bone_name_chunk.num_names == template_bone_name_chunk.num_names:
        raise RuntimeError(f"{input_file} is already in old format.")
    if bone_name_chunk.num_names != 151:
        raise RuntimeError(f"{input_file} is not a PC model.")

    _reposition_fingers(bone_name_chunk, bone_initial_chunk, vertex_chunk)

    index_mapping = {}
    new_names = [n for n in template_bone_name_chunk.names]
    new_bones = [None] * len(new_names)
    new_matrices = [None] * len(new_names)

    old_names = []
    old_pos = []
    old_rot = []

    for index, name in enumerate(bone_name_chunk.names):
        old_names.append(name)
        old_pos.append(bone_initial_chunk.initial_pos_matrices[index].pos.get_copy())
        old_rot.append(bone_initial_chunk.initial_pos_matrices[index].rot.get_copy())

        if name in _bone_name_map:
            curr_index = new_names.index(_bone_name_map[name])
            index_mapping[index] = curr_index

            bone = bone_anim_chunk.bones[index]
            bone.bone_id = curr_index
            bone.parent_id = template_bone_anim_chunk.bones[curr_index].parent_id
            bone.num_children = template_bone_anim_chunk.bones[curr_index].num_children
            bone.bone_name_crc_32 = template_bone_anim_chunk.bones[
                curr_index
            ].bone_name_crc_32
            new_bones[curr_index] = bone

            matrice = bone_initial_chunk.initial_pos_matrices[index]
            matrice.rot = template_bone_initial_chunk.initial_pos_matrices[
                curr_index
            ].rot
            matrice.pos = template_bone_initial_chunk.initial_pos_matrices[
                curr_index
            ].pos
            new_matrices[curr_index] = matrice

    # fix fingers rotation
    for _f0, _f1, _d in [
        ["Bip01 R Finger0", "Bip01 R Finger01", "Bip01 R Finger0"],
        ["Bip01 R Finger1", "Bip01 R Finger11", "Bip01 R Finger1"],
        ["Bip01 L Finger0", "Bip01 L Finger01", "Bip01 L Finger0"],
        ["Bip01 L Finger1", "Bip01 L Finger11", "Bip01 L Finger1"],
    ]:
        f0 = new_names.index(_f0)
        f1 = new_names.index(_f1)
        d = old_rot[old_names.index(_d)]

        delta_rot_f0_f1 = new_matrices[f0].rot.get_transpose() * new_matrices[f1].rot

        new_matrices[f0].pos = template_bone_initial_chunk.initial_pos_matrices[
            f0
        ].pos.get_copy()
        new_matrices[f0].rot = d.get_copy()

        new_matrices[f1].rot = new_matrices[f0].rot * delta_rot_f0_f1
        new_matrices[f1].pos = (
            new_matrices[f0].pos
            + (
                (
                    template_bone_initial_chunk.initial_pos_matrices[f1].pos
                    - template_bone_initial_chunk.initial_pos_matrices[f0].pos
                )
                * template_bone_initial_chunk.initial_pos_matrices[
                    f0
                ].rot.get_transpose()
            )
            * new_matrices[f0].rot
        )

    for vertex_weight in vertex_chunk.vertex_weights:
        while any(
            re.compile(r"Finger(\d)1").search(bone_name_chunk.names[link.bone])
            for link in vertex_weight.bone_links
        ):
            for i, link in enumerate(list(vertex_weight.bone_links)):
                bone_name = bone_name_chunk.names[link.bone]

                m = re.search(r"Finger(\d)1", bone_name)
                if not m:
                    continue

                finger = m.group(1)

                bone0 = old_names.index(
                    bone_name.replace(f"Finger{finger}1", f"Finger{finger}")
                )
                bone2 = old_names.index(
                    bone_name.replace(f"Finger{finger}1", f"Finger{finger}2")
                )

                while (
                    i < len(vertex_weight.bone_links)
                    and vertex_weight.bone_links[i].bone == link.bone
                ):
                    vertex_weight.bone_links.pop(i)

                for bone in (bone0, bone2):
                    new_link = CgfFormat.BoneLink()
                    new_link.bone = bone
                    new_link.blending = link.blending * 0.5

                    # not sure how it affects model
                    # new_link.offset = _calculate_vertex_offset(
                    #     link.offset,
                    #     old_pos[link.bone],
                    #     old_rot[link.bone],
                    #     old_pos[bone],
                    #     old_rot[bone],
                    # )

                    vertex_weight.bone_links.append(new_link)

        for link in vertex_weight.bone_links:
            new_bone = 0
            if link.bone in index_mapping:
                new_bone = index_mapping[link.bone]
            elif bone_name_chunk.names[link.bone] in _bone_vertex_map:
                new_bone = new_names.index(
                    _bone_vertex_map[bone_name_chunk.names[link.bone]]
                )
            else:
                raise RuntimeError(
                    f"Vertex references removed bone index {link.bone} - {old_names[link.bone]}"
                )

            # if offset above does affect model, why this does not :/
            link.offset = _calculate_vertex_offset(
                link.offset,
                old_pos[link.bone],
                old_rot[link.bone],
                new_matrices[new_bone].pos,
                new_matrices[new_bone].rot,
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
        bone_name_chunk.names[index] = name
    while len(new_names) != len(bone_name_chunk.names):
        bone_name_chunk.names.pop(len(new_names))
    bone_name_chunk.num_names = len(bone_name_chunk.names)

    bone_anim_chunk.bones.clear()
    for bone in new_bones:
        bone_anim_chunk.bones.append(bone)
    bone_anim_chunk.num_bones = len(bone_anim_chunk.bones)

    bone_initial_chunk.initial_pos_matrices.clear()
    for matrice in new_matrices:
        bone_initial_chunk.initial_pos_matrices.append(matrice)
    bone_initial_chunk.num_bones = len(bone_initial_chunk.initial_pos_matrices)

    _write_data(input_file, data, output_folder)


__all__ = ["transform_cgf"]
