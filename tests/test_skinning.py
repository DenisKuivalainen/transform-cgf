"""The per-vertex weight passes, each exercised on its own.

The passes mutate a PyFFI link array in place.  A plain list supports the
same operations, so the tests build one directly rather than carrying a
whole mesh around.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pyffi.formats.cgf import CgfFormat

from transform_cgf.errors import UnmappedBoneError
from transform_cgf.skinning import (
    DOMINANCE_THRESHOLD,
    collapse_extra_fingers,
    dissolve_middle_phalanges,
    drop_zero_weights,
    merge_duplicate_links,
    normalise_dominant_finger,
    remap_bones,
    renormalise,
    rewrite_vertex_weights,
)

#: A bone table shaped like the patch-5.x right hand, enough for the passes.
NAMES = [
    "Bip01 R Hand",
    "Bip01 R Finger0",
    "Bip01 R Finger01",
    "Bip01 R Finger02",
    "Bip01 R Finger1",
    "Bip01 R Finger11",
    "Bip01 R Finger12",
    "Bip01 R Finger2",
    "Bip01 R Finger21",
    "Bip01 R Finger22",
    "Bip01 R Finger3",
    "Bip01 R Finger31",
    "Bip01 R Finger32",
    "Bip01 R Finger4",
    "Bip01 R Finger41",
    "Bip01 R Finger42",
    "Bip01 R Forearm",
]

INDEX = {name: i for i, name in enumerate(NAMES)}


def link(bone: str, blending: float) -> CgfFormat.BoneLink:
    item = CgfFormat.BoneLink()
    item.bone = INDEX[bone]
    item.blending = blending
    return item


def links(*pairs) -> list:
    return [link(bone, blending) for bone, blending in pairs]


def described(link_list) -> list[tuple[str, float]]:
    return [(NAMES[item.bone], pytest.approx(item.blending)) for item in link_list]


def weights(link_list) -> dict[str, float]:
    return {NAMES[item.bone]: item.blending for item in link_list}


class TestCollapseExtraFingers:
    def test_ring_and_little_roots_become_the_middle_finger(self):
        current = links(("Bip01 R Finger3", 0.4), ("Bip01 R Finger4", 0.6))
        collapse_extra_fingers(current, NAMES)
        assert {NAMES[item.bone] for item in current} == {"Bip01 R Finger2"}

    def test_weights_are_carried_over_untouched(self):
        current = links(("Bip01 R Finger3", 0.4))
        collapse_extra_fingers(current, NAMES)
        assert current[0].blending == pytest.approx(0.4)

    def test_phalanges_are_left_for_a_later_pass(self):
        current = links(("Bip01 R Finger31", 1.0), ("Bip01 R Finger42", 1.0))
        collapse_extra_fingers(current, NAMES)
        assert {NAMES[i.bone] for i in current} == {
            "Bip01 R Finger31",
            "Bip01 R Finger42",
        }

    def test_surviving_fingers_are_not_touched(self):
        current = links(("Bip01 R Finger0", 0.5), ("Bip01 R Finger2", 0.5))
        collapse_extra_fingers(current, NAMES)
        assert weights(current) == {
            "Bip01 R Finger0": pytest.approx(0.5),
            "Bip01 R Finger2": pytest.approx(0.5),
        }


class TestMergeDuplicateLinks:
    def test_sums_repeated_bones(self):
        current = links(("Bip01 R Finger2", 0.3), ("Bip01 R Finger2", 0.2))
        merge_duplicate_links(current)
        assert described(current) == [("Bip01 R Finger2", 0.5)]

    def test_keeps_first_appearance_order(self):
        current = links(
            ("Bip01 R Hand", 0.1), ("Bip01 R Finger2", 0.2), ("Bip01 R Hand", 0.3)
        )
        merge_duplicate_links(current)
        assert [NAMES[i.bone] for i in current] == ["Bip01 R Hand", "Bip01 R Finger2"]

    def test_leaves_a_clean_list_alone(self):
        current = links(("Bip01 R Hand", 0.4), ("Bip01 R Finger2", 0.6))
        merge_duplicate_links(current)
        assert described(current) == [
            ("Bip01 R Hand", 0.4),
            ("Bip01 R Finger2", 0.6),
        ]

    def test_reuse_keeps_the_original_objects(self):
        current = links(("Bip01 R Hand", 0.4))
        original = current[0]
        merge_duplicate_links(current, reuse=True)
        assert current[0] is original

    def test_without_reuse_the_objects_are_replaced(self):
        current = links(("Bip01 R Hand", 0.4))
        original = current[0]
        merge_duplicate_links(current)
        assert current[0] is not original
        assert current[0].blending == pytest.approx(0.4)


class TestNormaliseDominantFinger:
    def test_palm_weight_is_split_evenly_with_the_fingers(self):
        current = links(("Bip01 R Hand", 0.7), ("Bip01 R Finger1", 0.3))
        assert normalise_dominant_finger(current, NAMES)

        result = weights(current)
        assert result["Bip01 R Hand"] == pytest.approx(0.5)
        assert sum(v for k, v in result.items() if k != "Bip01 R Hand") == pytest.approx(
            0.5
        )

    def test_several_fingers_share_the_half_in_proportion(self):
        current = links(
            ("Bip01 R Hand", 0.5), ("Bip01 R Finger1", 0.3), ("Bip01 R Finger2", 0.1)
        )
        normalise_dominant_finger(current, NAMES)

        result = weights(current)
        assert result["Bip01 R Finger1"] == pytest.approx(0.375)
        assert result["Bip01 R Finger2"] == pytest.approx(0.125)

    def test_a_root_and_its_middle_phalanx_become_root_and_tip(self):
        current = links(("Bip01 R Finger1", 0.5), ("Bip01 R Finger11", 0.4))
        assert normalise_dominant_finger(current, NAMES)
        assert described(current) == [
            ("Bip01 R Finger1", 0.5),
            ("Bip01 R Finger12", 0.5),
        ]

    def test_a_middle_phalanx_and_tip_go_entirely_to_the_tip(self):
        current = links(("Bip01 R Finger11", 0.5), ("Bip01 R Finger12", 0.4))
        assert normalise_dominant_finger(current, NAMES)
        assert described(current) == [("Bip01 R Finger12", 1.0)]

    def test_nothing_happens_below_the_threshold(self):
        current = links(
            ("Bip01 R Hand", 0.3), ("Bip01 R Finger1", 0.3), ("Bip01 R Forearm", 0.4)
        )
        assert not normalise_dominant_finger(current, NAMES)
        assert len(current) == 3

    def test_the_threshold_is_exclusive(self):
        half = DOMINANCE_THRESHOLD / 2
        current = links(("Bip01 R Hand", half), ("Bip01 R Finger1", half))
        assert not normalise_dominant_finger(current, NAMES)

    def test_the_palm_case_wins_over_the_joint_cases(self):
        current = links(
            ("Bip01 R Hand", 0.5), ("Bip01 R Finger1", 0.4), ("Bip01 R Finger11", 0.1)
        )
        normalise_dominant_finger(current, NAMES)
        assert "Bip01 R Hand" in weights(current)


class TestDissolveMiddlePhalanges:
    def test_a_middle_phalanx_is_split_between_root_and_tip(self):
        current = links(("Bip01 R Finger11", 0.8))
        dissolve_middle_phalanges(current, NAMES)
        assert described(current) == [
            ("Bip01 R Finger1", 0.4),
            ("Bip01 R Finger12", 0.4),
        ]

    def test_every_middle_phalanx_is_removed(self):
        current = links(
            ("Bip01 R Finger01", 0.3),
            ("Bip01 R Finger21", 0.3),
            ("Bip01 R Finger41", 0.4),
        )
        dissolve_middle_phalanges(current, NAMES)
        assert not any("1" == NAMES[i.bone][-1] for i in current)

    def test_total_weight_is_preserved(self):
        current = links(("Bip01 R Finger11", 0.8), ("Bip01 R Hand", 0.2))
        dissolve_middle_phalanges(current, NAMES)
        assert sum(i.blending for i in current) == pytest.approx(1.0)

    def test_tips_and_roots_are_left_alone(self):
        current = links(("Bip01 R Finger1", 0.5), ("Bip01 R Finger12", 0.5))
        dissolve_middle_phalanges(current, NAMES)
        assert described(current) == [
            ("Bip01 R Finger1", 0.5),
            ("Bip01 R Finger12", 0.5),
        ]

    def test_terminates_on_an_empty_list(self):
        current = []
        dissolve_middle_phalanges(current, NAMES)
        assert current == []


class TestDropZeroWeights:
    def test_removes_every_zero(self):
        current = links(
            ("Bip01 R Hand", 0.0), ("Bip01 R Finger1", 0.5), ("Bip01 R Finger2", 0.0)
        )
        drop_zero_weights(current)
        assert described(current) == [("Bip01 R Finger1", 0.5)]

    def test_leaves_non_zero_weights_alone(self):
        current = links(("Bip01 R Hand", 0.5), ("Bip01 R Finger1", 0.5))
        drop_zero_weights(current)
        assert len(current) == 2

    def test_can_empty_the_list(self):
        current = links(("Bip01 R Hand", 0.0))
        drop_zero_weights(current)
        assert current == []


class TestRemapBones:
    TARGET = ["Bip01 R Hand", "Bip01 R Finger0", "Bip01 R Finger01"]

    def test_mapped_bones_move_to_their_slot(self):
        current = links(("Bip01 R Hand", 1.0))
        remap_bones(current, NAMES, {INDEX["Bip01 R Hand"]: 0}, self.TARGET, {})
        assert current[0].bone == 0

    def test_unmapped_bones_go_through_the_fallback(self):
        current = links(("Bip01 R Finger02", 1.0))
        remap_bones(
            current,
            NAMES,
            {},
            self.TARGET,
            {"Bip01 R Finger02": "Bip01 R Finger01"},
        )
        assert self.TARGET[current[0].bone] == "Bip01 R Finger01"

    def test_the_index_mapping_wins_over_the_fallback(self):
        current = links(("Bip01 R Hand", 1.0))
        remap_bones(
            current,
            NAMES,
            {INDEX["Bip01 R Hand"]: 0},
            self.TARGET,
            {"Bip01 R Hand": "Bip01 R Finger01"},
        )
        assert current[0].bone == 0

    def test_a_bone_in_neither_table_is_an_error(self):
        current = links(("Bip01 R Forearm", 1.0))
        with pytest.raises(UnmappedBoneError, match="Bip01 R Forearm"):
            remap_bones(current, NAMES, {}, self.TARGET, {})


class TestRenormalise:
    def make(self, *pairs):
        return SimpleNamespace(bone_links=links(*pairs), num_bone_links=0)

    def test_weights_end_up_summing_to_one(self):
        weight = self.make(("Bip01 R Hand", 0.3), ("Bip01 R Finger1", 0.3))
        renormalise(weight)
        assert sum(i.blending for i in weight.bone_links) == pytest.approx(1.0)

    def test_the_first_link_absorbs_the_correction(self):
        weight = self.make(("Bip01 R Hand", 0.1), ("Bip01 R Finger1", 0.25))
        renormalise(weight)
        assert weight.bone_links[0].blending == pytest.approx(0.75)
        assert weight.bone_links[1].blending == pytest.approx(0.25)

    def test_a_single_link_becomes_one(self):
        weight = self.make(("Bip01 R Hand", 0.42))
        renormalise(weight)
        assert weight.bone_links[0].blending == pytest.approx(1.0)

    def test_the_count_is_updated(self):
        weight = self.make(("Bip01 R Hand", 0.5), ("Bip01 R Finger1", 0.5))
        renormalise(weight)
        assert weight.num_bone_links == 2

    def test_an_empty_list_is_survivable(self):
        weight = SimpleNamespace(bone_links=[], num_bone_links=99)
        renormalise(weight)
        assert weight.num_bone_links == 0


class TestWholeSequence:
    """All eight passes, on a bone table shaped like the real one.

    The fallback table has to cover the ring and little finger *roots* even
    though pass 1 collapses them, because pass 4 re-creates a root link when
    it splits a middle phalanx.  That is not obvious, and getting it wrong
    here is what a missing fallback entry looks like in production.
    """

    TARGET = [
        "Bip01 R Hand",
        "Bip01 R Finger0",
        "Bip01 R Finger01",
        "Bip01 R Finger1",
        "Bip01 R Finger11",
        "Bip01 R Finger2",
        "Bip01 R Finger21",
    ]
    MAPPING = {
        INDEX["Bip01 R Hand"]: 0,
        INDEX["Bip01 R Finger0"]: 1,
        INDEX["Bip01 R Finger01"]: 2,
        INDEX["Bip01 R Finger1"]: 3,
        INDEX["Bip01 R Finger11"]: 4,
        INDEX["Bip01 R Finger2"]: 5,
        INDEX["Bip01 R Finger21"]: 6,
    }
    FALLBACK = {
        "Bip01 R Finger02": "Bip01 R Finger01",
        "Bip01 R Finger12": "Bip01 R Finger11",
        "Bip01 R Finger22": "Bip01 R Finger21",
        "Bip01 R Finger3": "Bip01 R Finger2",
        "Bip01 R Finger31": "Bip01 R Finger21",
        "Bip01 R Finger32": "Bip01 R Finger21",
        "Bip01 R Finger4": "Bip01 R Finger2",
        "Bip01 R Finger41": "Bip01 R Finger21",
        "Bip01 R Finger42": "Bip01 R Finger21",
    }

    def run(self, *pairs):
        weight = SimpleNamespace(bone_links=links(*pairs), num_bone_links=0)
        rewrite_vertex_weights(weight, NAMES, self.MAPPING, self.TARGET, self.FALLBACK)
        return weight

    def landed(self, weight) -> set[str]:
        return {self.TARGET[item.bone] for item in weight.bone_links}

    def test_a_ring_finger_vertex_lands_on_the_middle_finger(self):
        weight = self.run(("Bip01 R Finger3", 0.6), ("Bip01 R Finger31", 0.4))
        assert self.landed(weight) <= {"Bip01 R Finger2", "Bip01 R Finger21"}

    def test_a_little_finger_vertex_lands_on_the_middle_finger(self):
        weight = self.run(("Bip01 R Finger4", 0.5), ("Bip01 R Finger42", 0.5))
        assert self.landed(weight) <= {"Bip01 R Finger2", "Bip01 R Finger21"}

    @pytest.mark.parametrize(
        "pairs",
        [
            (("Bip01 R Hand", 0.9), ("Bip01 R Finger1", 0.1)),
            (("Bip01 R Finger41", 1.0),),
            (("Bip01 R Finger3", 0.6), ("Bip01 R Finger31", 0.4)),
            (
                ("Bip01 R Finger2", 0.34),
                ("Bip01 R Finger21", 0.33),
                ("Bip01 R Finger22", 0.33),
            ),
            (("Bip01 R Hand", 0.25), ("Bip01 R Finger0", 0.25), ("Bip01 R Finger1", 0.5)),
        ],
    )
    def test_weights_always_sum_to_one(self, pairs):
        weight = self.run(*pairs)
        assert sum(i.blending for i in weight.bone_links) == pytest.approx(1.0)

    def test_everything_lands_inside_the_old_rig(self):
        weight = self.run(("Bip01 R Finger01", 0.5), ("Bip01 R Finger11", 0.5))
        for item in weight.bone_links:
            assert 0 <= item.bone < len(self.TARGET)

    def test_the_link_count_matches_the_list(self):
        weight = self.run(("Bip01 R Hand", 0.5), ("Bip01 R Finger2", 0.5))
        assert weight.num_bone_links == len(weight.bone_links)

    def test_no_duplicate_bones_remain(self):
        weight = self.run(
            ("Bip01 R Finger3", 0.3), ("Bip01 R Finger4", 0.3), ("Bip01 R Finger2", 0.4)
        )
        bones = [i.bone for i in weight.bone_links]
        assert len(bones) == len(set(bones))

    def test_a_missing_fallback_for_a_recreated_root_is_caught(self):
        """Dropping the Finger4 root entry breaks a little-finger vertex."""
        incomplete = {k: v for k, v in self.FALLBACK.items() if k != "Bip01 R Finger4"}
        weight = SimpleNamespace(bone_links=links(("Bip01 R Finger41", 1.0)))
        with pytest.raises(UnmappedBoneError, match="Finger4"):
            rewrite_vertex_weights(
                weight, NAMES, self.MAPPING, self.TARGET, incomplete
            )
