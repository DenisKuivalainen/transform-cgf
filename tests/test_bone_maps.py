"""Invariants the bone lookup tables have to satisfy.

These tables are the part of the project most likely to be edited by hand
when a new asset trips the conversion, so they get their own guard rails.

They are also where the project's history shows most plainly: a handful of
entries treat the left and right hands differently.  Those are pinned below
under :data:`KNOWN_ASYMMETRIES` rather than asserted away, so that changing
one is a deliberate act with a failing test to confirm it.
"""

from __future__ import annotations

import pytest

from transform_cgf.bone_maps import BONE_NAME_MAP, VERTEX_BONE_FALLBACK_MAP
from transform_cgf.skinning import rewrite_vertex_weights

#: Entries where the two hands are mapped differently.  Harmless in practice
#: - every finger bone takes its rest pose from the template, and no vertex
#: survives the weight passes still pointing at a middle phalanx - but they
#: are not intentional, and they are not symmetric.
#: Bones listed in *both* tables with different targets.  ``remap_bones``
#: consults BONE_NAME_MAP first, so for a bone that survives the retarget the
#: fallback entry can never fire and these are dead text.  The ``Sub_L_``
#: entry pointing at ``R_Sup`` is a copy-paste from the right-hand block and
#: would be a live bug if that bone ever stopped surviving.
KNOWN_SHADOWED_FALLBACKS = {
    "Leye_bone": ("Leye_bone", "Bip01 Head"),
    "Reye_bone": ("Reye_bone", "Bip01 Head"),
    "Sub_L_bone_skin03": ("L_Sup", "R_Sup"),
}

KNOWN_ASYMMETRIES = {
    "Bip01 L Finger3": "Bip01 L Finger2",
    "Bip01 L Finger31": "Bip01 L Finger21",
    "Bip01 R Finger31": "Bip01 R Finger2",
    "Bip01 R Finger32": "Bip01 R Finger21",
}


class TestStructure:
    def test_neither_table_is_empty(self):
        assert BONE_NAME_MAP
        assert VERTEX_BONE_FALLBACK_MAP

    def test_all_keys_and_values_are_non_empty_strings(self):
        for table in (BONE_NAME_MAP, VERTEX_BONE_FALLBACK_MAP):
            for key, value in table.items():
                assert isinstance(key, str) and key.strip()
                assert isinstance(value, str) and value.strip()

    def test_the_only_disagreements_are_the_known_shadowed_ones(self):
        """Overlap is allowed; a *new* disagreement is a mistake.

        Where both tables name a bone, ``remap_bones`` uses BONE_NAME_MAP,
        so a differing fallback is unreachable.  Pinning the set means a new
        one shows up as a failure rather than as silently dead text.
        """
        conflicts = {
            name: (BONE_NAME_MAP[name], VERTEX_BONE_FALLBACK_MAP[name])
            for name in set(BONE_NAME_MAP) & set(VERTEX_BONE_FALLBACK_MAP)
            if BONE_NAME_MAP[name] != VERTEX_BONE_FALLBACK_MAP[name]
        }
        assert conflicts == KNOWN_SHADOWED_FALLBACKS

    def test_the_left_sub_bone_family_is_mapped_to_the_right_side(self):
        """Documents a copy-paste in the fallback table.

        Every ``Sub_L_bone_skin*`` vertex fallback points at ``R_Sup``.  It
        is inert today because those bones survive the retarget and the
        fallback is never consulted, but it is wrong, and a change that made
        the fallback reachable would mirror those vertices.
        """
        left_family = {
            name: target
            for name, target in VERTEX_BONE_FALLBACK_MAP.items()
            if name.startswith("Sub_L_bone_skin") and target.endswith("_Sup")
        }
        assert left_family
        assert set(left_family.values()) == {"R_Sup"}

    def test_a_fallback_never_redirects_onwards(self):
        """Redirects resolve in one hop, so lookup order cannot matter."""
        onward = {
            source: target
            for source, target in VERTEX_BONE_FALLBACK_MAP.items()
            if target in VERTEX_BONE_FALLBACK_MAP
            and VERTEX_BONE_FALLBACK_MAP[target] != target
        }
        assert not onward, f"multi-hop redirects: {onward}"

    def test_fallback_targets_are_bones_the_old_rig_keeps(self):
        kept = set(BONE_NAME_MAP.values())
        unknown = {
            source: target
            for source, target in VERTEX_BONE_FALLBACK_MAP.items()
            if target not in kept
        }
        assert not unknown, f"fallbacks point at bones that do not survive: {unknown}"

    def test_the_root_survives(self):
        assert BONE_NAME_MAP["Bip01"] == "Bip01"


class TestFingerHandling:
    def test_no_surviving_bone_is_a_fourth_or_fifth_finger(self):
        """The old rig has three fingers; nothing may map onto a fourth."""
        for target in BONE_NAME_MAP.values():
            assert not target.endswith(("Finger3", "Finger4"))

    def test_tip_phalanges_fall_back_to_the_middle_phalanx(self):
        for hand in ("L", "R"):
            for finger in range(5):
                source = f"Bip01 {hand} Finger{finger}2"
                assert source in VERTEX_BONE_FALLBACK_MAP, source

    def test_finger_roots_all_resolve_somewhere(self):
        for hand in ("L", "R"):
            for finger in range(5):
                name = f"Bip01 {hand} Finger{finger}"
                assert name in BONE_NAME_MAP or name in VERTEX_BONE_FALLBACK_MAP

    def test_known_asymmetries_are_still_exactly_these(self):
        """Pins the left/right quirks so a fix has to be intentional."""
        actual = {
            name: BONE_NAME_MAP[name]
            for name in KNOWN_ASYMMETRIES
            if name in BONE_NAME_MAP
        }
        assert actual == KNOWN_ASYMMETRIES

    def test_the_right_hand_has_no_finger3_root_entry(self):
        """Its weights are collapsed by the skinning pass instead."""
        assert "Bip01 R Finger3" not in BONE_NAME_MAP


class TestAgainstTemplate:
    """Cross-check the tables against a real old-rig bone table."""

    def test_every_fallback_target_exists_in_the_template(self, template_chunks):
        template_names = set(template_chunks.names)
        missing = sorted(
            t for t in VERTEX_BONE_FALLBACK_MAP.values() if t not in template_names
        )
        assert not missing, f"fallback targets missing from the old rig: {missing}"

    def test_every_template_bone_can_be_filled(
        self, template_chunks, any_source_chunks
    ):
        """No old-rig slot is left without an input bone to fill it."""
        filled = {
            BONE_NAME_MAP[name]
            for name in any_source_chunks.names
            if name in BONE_NAME_MAP
        }
        unfilled = sorted(set(template_chunks.names) - filled)
        assert not unfilled, f"old-rig bones with no source: {unfilled}"

    def test_unmapped_bones_are_ones_no_vertex_survives_on(
        self, any_source_chunks, template_chunks
    ):
        """Eight input bones have no entry in either table.

        That is only safe because the weight passes dissolve every link to
        them first.  This runs those passes and checks it holds.
        """
        unmapped = {
            name
            for name in any_source_chunks.names
            if name not in BONE_NAME_MAP and name not in VERTEX_BONE_FALLBACK_MAP
        }
        assert unmapped, "the premise of this test no longer holds"

        names = any_source_chunks.names
        index_mapping = {
            index: template_chunks.names.index(BONE_NAME_MAP[name])
            for index, name in enumerate(names)
            if name in BONE_NAME_MAP
            and BONE_NAME_MAP[name] in template_chunks.names
        }

        # Raises UnmappedBoneError if any vertex still points at one of them.
        for vertex_weight in any_source_chunks.vertex_weights:
            rewrite_vertex_weights(
                vertex_weight,
                names,
                index_mapping,
                template_chunks.names,
                VERTEX_BONE_FALLBACK_MAP,
            )
