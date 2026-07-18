from pyffi.formats.cgf import CgfFormat
from dataclasses import dataclass, asdict
import json
from typing import List
import numpy as np
from collections import defaultdict

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
]

male_points = [
    ["Hand", 44.3183, None, 43.5119, None, True],
    ["Hand", 46.3076, None, 45.0931, None, True],
    ["Hand", 48.6815, None, 46.9516, None, True],
    ["Hand", 50.7641, None, 48.3314, None, True],
    ["Hand", 49.4227, None, 47.7138, None, True],
    ["Hand", 46.1688, None, 45.8837, None, True],
    ["Hand", 43.9022, None, 44.0372, None, True],
    ["Hand", 43.1779, None, 43.2542, None, True],
    ["Hand", 44.3183, None, 43.5119, None, True],
    ["Hand", 46.1864, None, 45.6078, None, False],
    ["Hand", 47.9422, None, 46.4906, None, False],
    ["Hand", 50.4567, None, 48.456, None, False],
    ["Hand", 52.3381, None, 50.037, None, False],
    ["Hand", 50.8636, None, 49.7092, None, False],
    ["Hand", 48.3078, None, 47.4417, None, False],
    ["Hand", 46.4764, None, 46.1304, None, False],
    ["Hand", 45.5934, None, 45.3092, None, False],
    ["Hand", 46.1864, None, 45.6078, None, False],
    ["Foot", 8.368, None, 8.8334, None, True],
    ["Foot", 10.9957, None, 10.9576, None, True],
    ["Foot", 15.5077, None, 15.0604, None, True],
    ["Foot", 20.6435, None, 18.6471, None, True],
    ["Foot", 23.2286, None, 20.6541, None, True],
    ["Foot", 20.9304, None, 18.8168, None, True],
    ["Foot", 15.0146, None, 14.539, None, True],
    ["Foot", 9.8837, None, 10.3417, None, True],
    ["Foot", 8.368, None, 8.8334, None, True],
    ["Foot", 10.7059, None, 10.9898, None, False],
    ["Foot", 12.7068, None, 12.4927, None, False],
    ["Foot", 16.1713, None, 15.704, None, False],
    ["Foot", 20.5961, None, 18.7928, None, False],
    ["Foot", 22.4392, None, 20.4322, None, False],
    ["Foot", 20.5437, None, 18.6698, None, False],
    ["Foot", 15.6849, None, 15.1702, None, False],
    ["Foot", 11.9042, None, 12.0142, None, False],
    ["Foot", 10.7059, None, 10.9898, None, False],
    ["Foot", 12.0381, None, 12.3484, None, False],
    ["Foot", 13.8149, None, 13.7116, None, False],
    ["Foot", 16.6447, None, 16.084, None, False],
    ["Foot", 20.5391, None, 18.8408, None, False],
    ["Foot", 21.98, None, 19.882, None, False],
    ["Foot", 19.9683, None, 18.5488, None, False],
    ["Foot", 16.2601, None, 15.8191, None, False],
    ["Foot", 13.4209, None, 13.4082, None, False],
    ["Foot", 12.0381, None, 12.3484, None, False],
    ["Foot", 12.5298, None, 13.068, None, False],
    ["Foot", 13.9938, None, 14.2567, None, False],
    ["Foot", 16.9962, None, 16.6265, None, False],
    ["Foot", 20.3897, None, 18.6681, None, False],
    ["Foot", 22.1384, None, 19.5875, None, False],
    ["Foot", 20.1892, None, 18.4479, None, False],
    ["Foot", 16.4512, None, 16.1619, None, False],
    ["Foot", 13.982, None, 14.2594, None, False],
    ["Foot", 12.5298, None, 13.068, None, False],
    ["Leg", 0, -11.288, 0, -11.1166, True],
    ["Leg", 5.52067, None, 5.35723, None, True],
    ["Leg", 10.7403, None, 9.54487, None, True],
    ["Leg", 13.8598, None, 12.894, None, True],
    ["Leg", 15.3719, None, 13.8625, None, True],
    ["Leg", 11.3599, None, 10.9618, None, True],
    ["Leg", 5.52116, None, 5.48746, None, True],
    ["Leg", 0, 10.2746, 0, 10.2746, True],
    ["Leg", 0, -10.8943, 0, -10.8757, False],
    ["Leg", 5.51964, None, 5.51964, None, False],
    ["Leg", 10.0225, None, 10.0225, None, False],
    ["Leg", 14.4018, None, 13.4244, None, False],
    ["Leg", 15.5994, None, 14.1866, None, False],
    ["Leg", 12.9066, None, 11.8472, None, False],
    ["Leg", 6.80693, None, 6.57484, None, False],
    ["Leg", 0, 10.8423, 0, 10.4856, False],
    ["Leg", 8.36804, None, 8.83344, None, True],
    ["Leg", 10.9957, None, 10.9576, None, True],
    ["Leg", 15.5077, None, 15.0604, None, True],
    ["Leg", 20.6435, None, 18.6471, None, True],
    ["Leg", 23.2286, None, 20.6541, None, True],
    ["Leg", 20.9304, None, 18.8168, None, True],
    ["Leg", 15.0146, None, 14.539, None, True],
    ["Leg", 9.88375, None, 10.3417, None, True],
    ["Leg", 8.36804, None, 8.83344, None, True],
    ["Leg", 7.73554, None, 8.13839, None, False],
    ["Leg", 8.92156, None, 8.84269, None, False],
    ["Leg", 11.2156, None, 10.5356, None, False],
    ["Leg", 15.6163, None, 14.4455, None, False],
    ["Leg", 19.6965, None, 18.3186, None, False],
    ["Leg", 22.5843, None, 20.4141, None, False],
    ["Leg", 22.9612, None, 19.957, None, False],
    ["Leg", 20.7927, None, 18.4172, None, False],
    ["Leg", 14.0026, None, 14.0027, None, False],
    ["Leg", 9.13122, None, 9.43969, None, False],
    ["Leg", 7.73554, None, 8.13839, None, False],
    ["Leg", 7.84199, None, 8.04861, None, False],
    ["Leg", 9.4344, None, 9.11874, None, False],
    ["Leg", 11.5301, None, 10.5831, None, False],
    ["Leg", 14.9829, None, 14.1409, None, False],
    ["Leg", 18.5978, None, 17.7611, None, False],
    ["Leg", 21.6268, None, 19.6354, None, False],
    ["Leg", 22.121, None, 19.3335, None, False],
    ["Leg", 19.8908, None, 17.5867, None, False],
    ["Leg", 13.5173, None, 13.2793, None, False],
    ["Leg", 9.12182, None, 9.15654, None, False],
    ["Leg", 7.84203, None, 8.04861, None, False],
    ["Leg", 6.57632, None, 6.52139, None, False],
    ["Leg", 7.59557, None, 7.00212, None, False],
    ["Leg", 9.83318, None, 9.59208, None, False],
    ["Leg", 11.9823, None, 11.8776, None, False],
    ["Leg", 14.3438, None, 14.0015, None, False],
    ["Leg", 16.7211, None, 15.4738, None, False],
    ["Leg", 18.3708, None, 16.9444, None, False],
    ["Leg", 19.894, None, 17.5971, None, False],
    ["Leg", 19.5709, None, 16.7939, None, False],
    ["Leg", 17.3538, None, 15.2844, None, False],
    ["Leg", 13.0398, None, 11.8774, None, False],
    ["Leg", 9.13183, None, 8.85358, None, False],
    ["Leg", 6.57635, None, 6.52139, None, False],
    ["Leg", 4.54897, None, 4.96727, None, False],
    ["Leg", 4.82226, None, 4.85382, None, False],
    ["Leg", 7.35867, None, 7.5743, None, False],
    ["Leg", 10.6037, None, 11.0773, None, False],
    ["Leg", 13.2654, None, 13.8174, None, False],
    ["Leg", 18.8292, None, 17.4764, None, False],
    ["Leg", 21.0443, None, 18.0991, None, False],
    ["Leg", 18.9074, None, 16.6288, None, False],
    ["Leg", 16.3569, None, 14.2511, None, False],
    ["Leg", 11.7419, None, 10.6007, None, False],
    ["Leg", 6.65711, None, 6.92259, None, False],
    ["Leg", 4.54897, None, 4.96727, None, False],
    ["Leg", 2.48037, None, 3.28852, None, False],
    ["Leg", 4.6715, None, 4.1679, None, False],
    ["Leg", 7.21554, None, 7.63717, None, False],
    ["Leg", 12.3862, None, 13.2772, None, False],
    ["Leg", 21.3284, None, 18.1104, None, False],
    ["Leg", 19.4034, None, 16.5494, None, False],
    ["Leg", 15.2248, None, 13.7995, None, False],
    ["Leg", 10.1383, None, 9.7054, None, False],
    ["Leg", 5.04693, None, 5.52334, None, False],
    ["Leg", 2.48037, None, 3.28852, None, False],
    ["Leg", 1.28935, None, 1.66955, None, False],
    ["Leg", 3.14625, None, 2.63284, None, False],
    ["Leg", 6.96153, None, 6.93971, None, False],
    ["Leg", 11.7145, None, 12.4252, None, False],
    ["Leg", 20.9273, None, 17.829, None, False],
    ["Leg", 18.7306, None, 15.8153, None, False],
    ["Leg", 14.314, None, 12.9087, None, False],
    ["Leg", 8.97812, None, 8.85223, None, False],
    ["Leg", 4.31421, None, 5.0277, None, False],
    ["Leg", 2.76389, None, 3.17409, None, False],
    ["Leg", 1.28938, None, 1.66955, None, False],
    ["Body", 0, 10.2746, 0, 10.2746, True],
    ["Body", 5.52116, None, 5.48745, None, True],
    ["Body", 11.3599, None, 10.9618, None, True],
    ["Body", 15.3719, None, 13.8625, None, True],
    ["Body", 13.8598, None, 12.894, None, True],
    ["Body", 10.7403, None, 9.54487, None, True],
    ["Body", 5.52067, None, 5.35723, None, True],
    ["Body", 0, -11.288, 0, -11.1166, True],
    ["Body", 0, 10.2014, 0, 9.69447, False],
    ["Body", 4.18622, None, 4.18622, None, False],
    ["Body", 7.30091, None, 7.20958, None, False],
    ["Body", 11.8624, None, 10.9421, None, False],
    ["Body", 14.8665, None, 13.541, None, False],
    ["Body", 14.8444, None, 13.9691, None, False],
    ["Body", 13.3544, None, 12.5761, None, False],
    ["Body", 9.27197, None, 9.27197, None, False],
    ["Body", 0, 10.6853, 0, 10.0435, False],
    ["Body", 4.0105, None, 4.0105, None, False],
    ["Body", 7.62172, None, 7.5304, None, False],
    ["Body", 12.4123, None, 11.4391, None, False],
    ["Body", 15.6928, None, 14.0153, None, False],
    ["Body", 15.3195, None, 14.5532, None, False],
    ["Body", 13.9282, None, 13.0889, None, False],
    ["Body", 10.1432, None, 9.89987, None, False],
    ["Body", 7.25459, None, 7.25459, None, False],
    ["Body", 4.03957, None, 4.03957, None, False],
    ["Body", 0, -10.1664, 0, -10.6939, False],
    ["Body", 0, 11.427, 0, 10.1895, False],
    ["Body", 0, 12.4604, 0, 11.259, False],
    ["Body", 0, 13.959, 0, 13.0973, False],
    ["Body", 0, 15.5422, 0, 13.914, False],
    ["Body", 0, 15.2528, 0, 13.1446, False],
    ["Body", 0, 12.9944, 0, 11.4183, False],
    ["Body", 0, 10.5228, 0, 9.05862, False],
    ["Body", 0, 9.03142, 0, 7.99728, False],
    ["Body", 0, 7.7923, 0, 7.31291, False],
    ["Body", 0, 7.20262, 0, 7.20249, False],
    ["Body", 0, -10.575, 0, -10.4484, False],
    ["Body", 0, -10.1, 0, -9.8767, False],
    ["Body", 0, -10.7988, 0, -10.9393, False],
    ["Body", 0, -10.5621, 0, -10.8982, False],
    ["Body", 0, -11.4801, 0, -11.1093, False],
    ["Body", 0, -10.3663, 0, -9.70259, False],
    ["Body", 0, -10.792, 0, -9.95659, False],
    ["Body", 0, -10.2396, 0, -9.24279, False],
    ["Body", 0, -8.6845, 0, -7.72492, False],
    ["Body", 0, -6.77298, 0, -6.41122, False],
    ["Body", 0, -5.90232, 0, -6.00299, False],
    ["Body", 0, -3.59121, 0, -3.59121, False],
    ["Body", 0, -3.22732, 0, -3.22732, False],
    ["Body", 0, -3.33267, 0, -3.54007, False],
    ["Body", 0, -3.96558, 0, -3.88202, False],
    ["Body", 0, -3.8788, 0, -3.87879, False],
    ["Body", 11.3893, None, 10.5891, None, False],
    ["Body", 11.8874, None, 11.3334, None, False],
    ["Body", 12.9862, None, 12.2914, None, False],
    ["Body", 13.8194, None, 13.1556, None, False],
    ["Body", 14.4243, None, 13.7173, None, False],
    ["Body", 6.33862, None, 6.26883, None, False],
    ["Body", 6.99085, None, 6.6833, None, False],
    ["Body", 7.60421, None, 7.60421, None, False],
    ["Body", 8.21748, None, 7.9785, None, False],
    ["Body", 8.91305, None, 8.32727, None, False],
    ["Body", 2.09227, None, 2.09227, None, False],
    ["Body", 2.44976, None, 2.44976, None, False],
    ["Body", 2.06889, None, 2.06889, None, False],
    ["Body", 2.47031, None, 2.47031, None, False],
    ["Body", 3.19142, None, 3.19142, None, False],
    ["Body", 4.90121, None, 4.90121, None, False],
    ["Body", 10.3841, None, 9.12468, None, False],
    ["Body", 14.6035, None, 12.9921, None, False],
    ["Body", 17.3227, None, 15.5074, None, False],
    ["Body", 17.1515, None, 15.3203, None, False],
    ["Body", 16.4862, None, 14.5634, None, False],
    ["Body", 14.0778, None, 13.5732, None, False],
    ["Body", 10.7465, None, 11.2198, None, False],
    ["Body", 6.88696, None, 7.40919, None, False],
    ["Body", 4.20288, None, 4.24415, None, False],
    ["Body", 43.1779, None, 43.2542, None, False],
    ["Body", 44.3183, None, 43.5119, None, False],
    ["Body", 46.3076, None, 45.0931, None, False],
    ["Body", 48.6815, None, 46.9516, None, False],
    ["Body", 50.7641, None, 48.3314, None, False],
    ["Body", 49.4226, None, 47.7138, None, False],
    ["Body", 46.1688, None, 45.8837, None, False],
    ["Body", 43.9022, None, 44.0372, None, False],
    ["Body", 43.1779, None, 43.2542, None, False],
    ["Body", 40.5366, None, 40.2339, None, False],
    ["Body", 42.6223, None, 42.0439, None, False],
    ["Body", 45.6172, None, 44.2193, None, False],
    ["Body", 47.6659, None, 45.5195, None, False],
    ["Body", 46.3075, None, 44.7859, None, False],
    ["Body", 43.3017, None, 42.6397, None, False],
    ["Body", 40.5958, None, 40.7824, None, False],
    ["Body", 39.2078, None, 39.6841, None, False],
    ["Body", 34.4314, None, 34.9381, None, False],
    ["Body", 35.9285, None, 36.2043, None, False],
    ["Body", 37.6582, None, 37.7819, None, False],
    ["Body", 40.2148, None, 39.1234, None, False],
    ["Body", 43.9349, None, 41.9498, None, False],
    ["Body", 45.2768, None, 43.2731, None, False],
    ["Body", 44.1119, None, 42.5297, None, False],
    ["Body", 41.1676, None, 40.2394, None, False],
    ["Body", 38.0519, None, 37.8887, None, False],
    ["Body", 35.4703, None, 35.8923, None, False],
    ["Body", 34.4314, None, 34.9381, None, False],
    ["Body", 23.6808, None, 21.4611, None, False],
    ["Body", 26.3179, None, 24.8147, None, False],
    ["Body", 29.7193, None, 28.018, None, False],
    ["Body", 32.7835, None, 31.5102, None, False],
    ["Body", 34.2599, None, 31.7706, None, False],
    ["Body", 32.112, None, 29.9443, None, False],
    ["Body", 27.9605, None, 26.2045, None, False],
    ["Body", 23.6668, None, 22.4723, None, False],
    ["Body", 22.0606, None, 20.7628, None, False],
    ["Body", 22.4307, None, 20.3196, None, False],
    ["Body", 19.3896, None, 17.6067, None, False],
    ["Body", 18.3512, None, 16.2042, None, False],
    ["Body", 15.3972, None, 13.5248, None, False],
    ["Body", 14.4262, None, 13.0614, None, False],
    ["Body", 15.7199, None, 14.7321, None, False],
    ["Body", 16.5352, None, 14.9799, None, False],
    ["Body", 16.1854, None, 14.9376, None, False],
    ["Body", 14.3684, None, 13.4275, None, False],
    ["Body", 15.3221, None, 14.6882, None, False],
    ["Body", 18.7946, None, 16.5907, None, False],
    ["Body", 19.7219, None, 17.7865, None, False],
    ["Body", 22.4688, None, 20.519, None, False],
    ["Body", 25.2223, None, 22.5357, None, False],
    ["Body", 26.5387, None, 23.9203, None, False],
    ["Body", 27.3258, None, 24.9319, None, False],
    ["Body", 25.627, None, 24.2833, None, False],
    ["Body", 23.9063, None, 22.3871, None, False],
    ["Body", 21.3311, None, 19.7041, None, False],
]


def find_vertices(vertices, target_x, target_y, epsilon=1e-4):
    matches = []

    for i, v in enumerate(vertices):
        delta = v.p.x - target_x if target_y is None else v.p.y - target_y
        if abs(delta) <= epsilon:
            matches.append(i)

    return None if len(matches) != 1 else matches[0]


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


@dataclass
class VertexesTransformation:
    bone_name: str
    bone_old_weight: float
    bone_new_weight: float
    bone_pos: list[float]
    bone_rot: list[list[float]]

    vertex_old_pos: list[float]
    vertex_new_pos: list[float]
    is_anchor: bool

    def __init__(
        self,
        bone_name,
        bone_old_weight,
        bone_new_weight,
        bone_pos,
        bone_rot,
        vertex_old_pos,
        vertex_new_pos,
        is_anchor,
    ):
        self.bone_name = bone_name
        self.bone_old_weight = bone_old_weight
        self.bone_new_weight = bone_new_weight
        self.bone_pos = vector_to_array(bone_pos)
        self.bone_rot = matrix_to_array(bone_rot)
        self.vertex_old_pos = vector_to_array(vertex_old_pos)
        self.vertex_new_pos = vector_to_array(vertex_new_pos)
        self.is_anchor = is_anchor


def get_matched_vertices():
    matched_vertices: list[VertexesTransformation] = []

    points = []
    for p in male_points:
        points.append(p.copy())
        p[1] = -p[1]
        p[3] = -p[3]
        points.append(p.copy())

    for body_part in ["Hand", "Body", "Leg", "Foot"]:
        old_bone_name_chunk, old_bone_initial_chunk, old_vertex_chunk = getChunks(
            f"./old/dmdf_c001_{body_part.lower()}.cgf"
        )

        new_bone_name_chunk, new_bone_initial_chunk, new_vertex_chunk = getChunks(
            f"./new/DMDF_C001_{body_part}.cgf"
        )

        old_bone_names = {}
        new_bone_names = {}

        for name_index, name in enumerate(old_bone_name_chunk.names):
            if name in allowed_bones:
                old_bone_names[name_index] = name

        for name_index, name in enumerate(new_bone_name_chunk.names):
            if name in allowed_bones:
                new_bone_names[name_index] = name

        for b_p, old_x, old_y, new_x, new_y, is_anchor in points:
            if b_p != body_part:
                continue
            old_vertex_index = find_vertices(old_vertex_chunk.vertices, old_x, old_y)
            new_vertex_index = find_vertices(new_vertex_chunk.vertices, new_x, new_y)

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
                    link.blending,
                    new_bones_weights[bone_name],
                    old_bone_initial_chunk.initial_pos_matrices[link.bone].pos,
                    old_bone_initial_chunk.initial_pos_matrices[link.bone].rot,
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


def world_to_local(point, bone_pos, bone_rot):
    point = np.asarray(point, dtype=float)
    bone_pos = np.asarray(bone_pos, dtype=float)
    rot = np.asarray(bone_rot, dtype=float)

    return rot.T @ (point - bone_pos)


def local_to_world(vec, bone_rot):
    rot = np.asarray(bone_rot, dtype=float)
    return rot @ vec


def build_profiles():
    matched = get_matched_vertices()

    grouped = defaultdict(list)

    for sample in matched:
        grouped[sample.bone_name].append(sample)

    profiles = {}

    for bone_name, samples in grouped.items():

        bone_pos = samples[0].bone_pos
        bone_rot = samples[0].bone_rot

        control_points = []

        for s in samples:

            old_local = world_to_local(s.vertex_old_pos, bone_pos, bone_rot)

            new_local = world_to_local(s.vertex_new_pos, bone_pos, bone_rot)

            delta_local = old_local - new_local

            cp = ControlPoint(
                local_pos=tuple(new_local),
                delta_local=tuple(delta_local),
                weight=(s.bone_old_weight + s.bone_new_weight) * 0.5,
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
    build_profiles()
