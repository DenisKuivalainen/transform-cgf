"""Finger chain definitions and the per-finger tuning of the retarget.

The patch-5.x rig gives each hand five three-bone finger chains; the old rig
has three.  Bringing the new fingers onto the old hand is a hand-tuned
operation, and in the original code the tuning lived as a ladder of
``if "Finger1" in name: angle0 = 0 ...`` branches buried inside two
500-line methods.

Pulling it out here means the numbers an artist would actually want to
adjust sit in one readable table, and the geometry code that consumes them
reads as a single formula instead of a formula plus a branch ladder.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FingerChain",
    "MaleFingerTuning",
    "FemaleFingerTuning",
    "MALE_TUNING",
    "FEMALE_TUNING",
    "male_chains",
    "female_chains",
    "OLD_RIG_REBASED_CHAINS",
    "HANDS",
    "FINGER_INDICES",
]

#: Bip01 infix for each hand, as it appears in bone names.
HANDS: tuple[str, ...] = ("R", "L")

#: The five fingers of the new rig, thumb first.
FINGER_INDICES: tuple[int, ...] = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class FingerChain:
    """One finger: its three bones plus the bone whose orientation guides it.

    ``reference`` is a *different* finger in most cases.  The old rig has no
    ring or little finger, so those chains are aimed using the orientation of
    a finger that does survive, which is what keeps the collapsed hand from
    splaying.
    """

    root: str
    middle: str
    tip: str
    reference: str

    @property
    def finger_index(self) -> int:
        """0 for the thumb through 4 for the little finger."""
        return int(self.root[-1])

    @property
    def is_thumb(self) -> bool:
        return self.finger_index == 0

    @property
    def is_right_hand(self) -> bool:
        return " R " in self.reference

    @property
    def guided_by_middle_finger(self) -> bool:
        """True when this chain is aimed at the middle finger.

        Such a chain inherits the reference orientation outright rather than
        keeping its own joint-to-joint deltas.
        """
        return self.reference.endswith("Finger2")


@dataclass(frozen=True)
class MaleFingerTuning:
    """Hand-tuned constants for one male finger.

    ``root_angle`` / ``middle_angle`` / ``tip_angle``
        Extra Y-axis swing (degrees) applied at each joint.
    ``length_modifier``
        Scales the bone lengths; the old male hand is stockier.
    ``factor``
        How far the root bone is eased towards its reference orientation,
        0 meaning "leave it alone" and 1 "match the reference exactly".
    """

    root_angle: float
    middle_angle: float
    tip_angle: float
    length_modifier: float
    factor: float


@dataclass(frozen=True)
class FemaleFingerTuning:
    """Hand-tuned constants for one female finger.

    The female retarget is simpler than the male one: a single ``angle`` is
    reused at both the middle and tip joints, and the root is always taken
    straight from the reference bone rather than eased towards it.
    """

    angle: float
    length_modifier: float


MALE_TUNING: dict[int, MaleFingerTuning] = {
    0: MaleFingerTuning(
        root_angle=0, middle_angle=10, tip_angle=30, length_modifier=1.15, factor=2 / 3
    ),
    1: MaleFingerTuning(
        root_angle=0, middle_angle=5, tip_angle=5, length_modifier=1.05, factor=5 / 9
    ),
    2: MaleFingerTuning(
        root_angle=25, middle_angle=10, tip_angle=25, length_modifier=1.05, factor=2 / 9
    ),
    3: MaleFingerTuning(
        root_angle=10, middle_angle=5, tip_angle=5, length_modifier=0.95, factor=4 / 9
    ),
    4: MaleFingerTuning(
        root_angle=5, middle_angle=10, tip_angle=10, length_modifier=1.0, factor=1.0
    ),
}

FEMALE_TUNING: dict[int, FemaleFingerTuning] = {
    0: FemaleFingerTuning(angle=0, length_modifier=0.9),
    1: FemaleFingerTuning(angle=18, length_modifier=1.0),
    2: FemaleFingerTuning(angle=30, length_modifier=1.0),
    3: FemaleFingerTuning(angle=30, length_modifier=1.0),
    4: FemaleFingerTuning(angle=30, length_modifier=1.0),
}

#: Which finger guides each chain, per gender.
_MALE_REFERENCE: dict[int, int] = {0: 0, 1: 2, 2: 3, 3: 2, 4: 3}
_FEMALE_REFERENCE: dict[int, int] = {0: 0, 1: 2, 2: 2, 3: 2, 4: 2}


def _chains(reference_of: dict[int, int]) -> list[FingerChain]:
    return [
        FingerChain(
            root=f"Bip01 {hand} Finger{finger}",
            middle=f"Bip01 {hand} Finger{finger}1",
            tip=f"Bip01 {hand} Finger{finger}2",
            reference=f"Bip01 {hand} Finger{reference_of[finger]}",
        )
        for hand in HANDS
        for finger in FINGER_INDICES
    ]


def male_chains() -> list[FingerChain]:
    """The ten male finger chains, right hand first."""
    return _chains(_MALE_REFERENCE)


def female_chains() -> list[FingerChain]:
    """The ten female finger chains, right hand first."""
    return _chains(_FEMALE_REFERENCE)


#: Chains that get re-based onto the old rig after the bone table is rebuilt.
#:
#: The thumb and index keep their template position but take the *input*
#: model's orientation, so that rings, gloves and sleeves authored for the
#: new hand still sit correctly.  Middle/ring/little are left at their
#: template values.
OLD_RIG_REBASED_CHAINS: tuple[tuple[str, str], ...] = (
    ("Bip01 R Finger0", "Bip01 R Finger01"),
    ("Bip01 R Finger1", "Bip01 R Finger11"),
    ("Bip01 L Finger0", "Bip01 L Finger01"),
    ("Bip01 L Finger1", "Bip01 L Finger11"),
)
