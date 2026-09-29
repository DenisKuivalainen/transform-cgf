"""Finger chain definitions and the tuning table."""

from __future__ import annotations

import pytest

from transform_cgf.finger_chains import (
    FEMALE_TUNING,
    MALE_TUNING,
    OLD_RIG_REBASED_CHAINS,
    FingerChain,
    female_chains,
    male_chains,
)


@pytest.fixture(params=[male_chains, female_chains], ids=["male", "female"])
def chains(request):
    return request.param()


class TestChainLayout:
    def test_five_fingers_on_each_of_two_hands(self, chains):
        assert len(chains) == 10

    def test_every_bone_name_is_distinct(self, chains):
        bones = [name for c in chains for name in (c.root, c.middle, c.tip)]
        assert len(bones) == len(set(bones)) == 30

    def test_bones_of_a_chain_share_a_stem(self, chains):
        for chain in chains:
            assert chain.middle == chain.root + "1"
            assert chain.tip == chain.root + "2"

    def test_reference_is_on_the_same_hand(self, chains):
        for chain in chains:
            hand = " R " if " R " in chain.root else " L "
            assert hand in chain.reference

    def test_both_hands_are_covered(self, chains):
        assert sum(1 for c in chains if c.is_right_hand) == 5

    def test_exactly_one_thumb_per_hand(self, chains):
        assert sum(1 for c in chains if c.is_thumb) == 2

    def test_a_thumb_references_itself(self, chains):
        for chain in chains:
            if chain.is_thumb:
                assert chain.reference == chain.root


class TestChainProperties:
    def test_finger_index_comes_from_the_name(self):
        chain = FingerChain(
            "Bip01 R Finger3", "Bip01 R Finger31", "Bip01 R Finger32", "Bip01 R Finger2"
        )
        assert chain.finger_index == 3
        assert not chain.is_thumb
        assert chain.is_right_hand
        assert chain.guided_by_middle_finger

    def test_left_hand_is_detected(self):
        chain = FingerChain(
            "Bip01 L Finger0", "Bip01 L Finger01", "Bip01 L Finger02", "Bip01 L Finger0"
        )
        assert not chain.is_right_hand
        assert chain.is_thumb

    def test_female_chains_all_aim_at_the_middle_finger_except_thumbs(self):
        for chain in female_chains():
            assert chain.guided_by_middle_finger is not chain.is_thumb


class TestTuning:
    @pytest.mark.parametrize("tuning", [MALE_TUNING, FEMALE_TUNING])
    def test_covers_every_finger(self, tuning):
        assert sorted(tuning) == [0, 1, 2, 3, 4]

    def test_male_ease_factors_are_a_sane_fraction(self):
        for tuning in MALE_TUNING.values():
            assert 0.0 < tuning.factor <= 1.0

    def test_length_modifiers_stay_near_one(self):
        for table in (MALE_TUNING, FEMALE_TUNING):
            for tuning in table.values():
                assert 0.8 <= tuning.length_modifier <= 1.2

    def test_the_male_thumb_is_the_one_that_lengthens_most(self):
        assert MALE_TUNING[0].length_modifier == max(
            t.length_modifier for t in MALE_TUNING.values()
        )


class TestRebasedChains:
    def test_covers_thumb_and_index_on_both_hands(self):
        assert len(OLD_RIG_REBASED_CHAINS) == 4
        roots = {root for root, _ in OLD_RIG_REBASED_CHAINS}
        assert roots == {
            "Bip01 R Finger0",
            "Bip01 R Finger1",
            "Bip01 L Finger0",
            "Bip01 L Finger1",
        }

    def test_middle_bone_follows_the_root(self):
        for root, middle in OLD_RIG_REBASED_CHAINS:
            assert middle == root + "1"
