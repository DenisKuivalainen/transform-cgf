"""Rewriting per-vertex skin weights for the old rig, and the bone offsets.

Collapsing five fingers into three is mostly a weighting problem.  A vertex
weighted half to the ring finger cannot simply be handed to the middle
finger: the hand would pinch.  The passes below run in order on each
vertex's link list and together turn a patch-5.x weighting into one the old
rig can animate:

1. :func:`collapse_extra_fingers` - ring and little finger roots become the
   middle finger, in the *source* index space;
2. :func:`merge_duplicate_links` - step 1 creates duplicates;
3. :func:`normalise_dominant_finger` - where a vertex is dominated by one
   joint pair, re-split it cleanly so the collapsed joint still bends;
4. :func:`dissolve_middle_phalanges` - the old rig has no middle phalanx,
   so its weight is shared between the joints either side;
5. :func:`drop_zero_weights` - housekeeping;
6. :func:`remap_bones` - finally move to old-rig bone indices;
7. :func:`merge_duplicate_links` again - remapping creates duplicates;
8. :func:`renormalise` - make the weights sum to exactly one.

Every pass mutates the link list in place, which is what PyFFI's array type
supports and what lets the whole file be written back out unchanged apart
from these edits.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping, Sequence

from pyffi.formats.cgf import CgfFormat

from .chunks import SkeletonChunks
from .errors import UnmappedBoneError
from .math3d import mean

__all__ = [
    "collapse_extra_fingers",
    "merge_duplicate_links",
    "normalise_dominant_finger",
    "dissolve_middle_phalanges",
    "drop_zero_weights",
    "remap_bones",
    "renormalise",
    "rewrite_vertex_weights",
    "average_bone_offset",
    "rebuild_link_offsets",
    "DOMINANCE_THRESHOLD",
]

#: A finger root the old rig does not have.
_EXTRA_FINGER_ROOT = re.compile(r"Finger([34])$")

#: Any finger root (``...Finger0`` through ``...Finger4``).
_FINGER_ROOT = re.compile(r"Finger\d$")

#: A middle phalanx (``...Finger01``, ``...Finger21``, ...).
_MIDDLE_PHALANX = re.compile(r"Finger(\d)1")

#: Combined weight above which a joint pair is treated as owning the vertex
#: outright, and is re-split into a clean half-and-half instead of being
#: left with whatever the new rig happened to author.
DOMINANCE_THRESHOLD = 0.75

_FINGER_COUNT = 5


def _make_link(bone: int, blending: float) -> CgfFormat.BoneLink:
    link = CgfFormat.BoneLink()
    link.bone = bone
    link.blending = blending
    return link


def _replace_links(links, new_links: Sequence[CgfFormat.BoneLink]) -> None:
    """Swap a link list's contents, in place."""
    while links:
        links.pop()
    for link in new_links:
        links.append(link)


# -- pass 1 ---------------------------------------------------------------


def collapse_extra_fingers(links, names: Sequence[str]) -> None:
    """Point ring and little finger roots at the middle finger root.

    Indices stay in the *source* bone table; the move to old-rig indices
    happens later, in :func:`remap_bones`.
    """
    for link in links:
        bone_name = names[link.bone]
        match = _EXTRA_FINGER_ROOT.search(bone_name)
        if not match:
            continue

        merged_name = bone_name.replace(f"Finger{match.group(1)}", "Finger2")
        link.bone = names.index(merged_name)


# -- passes 2 and 7 -------------------------------------------------------


def merge_duplicate_links(links, *, reuse: bool = False) -> None:
    """Sum the weights of links that point at the same bone.

    ``reuse`` keeps the existing link objects rather than building fresh
    ones.  Both are correct - every link's ``offset`` is recomputed at the
    end of the pipeline - but the two call sites differ in the original and
    are kept distinct so a byte-for-byte comparison stays meaningful.
    """
    merged: dict[int, CgfFormat.BoneLink] = {}

    for link in links:
        existing = merged.get(link.bone)
        if existing is not None:
            existing.blending += link.blending
        elif reuse:
            merged[link.bone] = link
        else:
            merged[link.bone] = _make_link(link.bone, link.blending)

    _replace_links(links, list(merged.values()))


# -- pass 3 ---------------------------------------------------------------


def _first_index(links, names: Sequence[str], suffix: str) -> int | None:
    return next(
        (i for i, link in enumerate(links) if names[link.bone].endswith(suffix)),
        None,
    )


def normalise_dominant_finger(links, names: Sequence[str]) -> bool:
    """Re-split a vertex that one joint pair dominates.

    Three shapes are handled, in this order, for each finger in turn.  The
    first that fires wins and the vertex is done:

    * **hand + finger root** - the vertex sits on the palm.  Give the hand
      half and share the other half across whichever finger roots are
      present, so the palm skin follows the fingers evenly.
    * **finger root + middle phalanx** - the middle phalanx is about to
      disappear, so hand the weight to the root and the tip, half each.
    * **middle phalanx + tip** - entirely past the vanishing joint; give it
      all to the tip.

    Returns whether anything was changed, which is useful in tests.
    """
    for finger in range(_FINGER_COUNT):
        hand_idx = _first_index(links, names, "Hand")
        root_idx = _first_index(links, names, f"Finger{finger}")
        middle_idx = _first_index(links, names, f"Finger{finger}1")
        tip_idx = _first_index(links, names, f"Finger{finger}2")

        if hand_idx is not None and root_idx is not None:
            hand = links[hand_idx]
            root = links[root_idx]

            if hand.blending + root.blending > DOMINANCE_THRESHOLD:
                finger_total = sum(
                    link.blending
                    for link in links
                    if _FINGER_ROOT.search(names[link.bone])
                )

                rebuilt = [_make_link(hand.bone, 0.5)]
                for link in links:
                    if not _FINGER_ROOT.search(names[link.bone]):
                        continue
                    share = (
                        link.blending / finger_total * 0.5 if finger_total > 0 else 0
                    )
                    rebuilt.append(_make_link(link.bone, share))

                _replace_links(links, rebuilt)
                return True

        if root_idx is not None and middle_idx is not None:
            if (
                links[root_idx].blending + links[middle_idx].blending
                > DOMINANCE_THRESHOLD
            ):
                tip_bone = names.index(
                    names[links[middle_idx].bone].replace(
                        f"Finger{finger}1", f"Finger{finger}2"
                    )
                )
                _replace_links(
                    links,
                    [
                        _make_link(links[root_idx].bone, 0.5),
                        _make_link(tip_bone, 0.5),
                    ],
                )
                return True

        if middle_idx is not None and tip_idx is not None:
            if (
                links[middle_idx].blending + links[tip_idx].blending
                > DOMINANCE_THRESHOLD
            ):
                _replace_links(links, [_make_link(links[tip_idx].bone, 1.0)])
                return True

    return False


# -- pass 4 ---------------------------------------------------------------


def dissolve_middle_phalanges(links, names: Sequence[str]) -> None:
    """Remove every middle-phalanx link, splitting it root/tip.

    Splitting into root and *tip* rather than root and middle is deliberate:
    spreading the weight across the whole finger keeps the silhouette smooth,
    where root+middle leaves a visible crease at the knuckle.
    """
    while any(_MIDDLE_PHALANX.search(names[link.bone]) for link in links):
        for position, link in enumerate(list(links)):
            bone_name = names[link.bone]
            match = _MIDDLE_PHALANX.search(bone_name)
            if not match:
                continue

            finger = match.group(1)

            while position < len(links) and links[position].bone == link.bone:
                links.pop(position)

            root = names.index(
                bone_name.replace(f"Finger{finger}1", f"Finger{finger}")
            )
            tip = names.index(
                bone_name.replace(f"Finger{finger}1", f"Finger{finger}2")
            )

            for bone in (root, tip):
                links.append(_make_link(bone, link.blending * 0.5))


# -- pass 5 ---------------------------------------------------------------


def drop_zero_weights(links) -> None:
    """Discard links that contribute nothing."""
    while any(link.blending == 0 for link in links):
        for position, link in enumerate(links):
            if link.blending == 0:
                links.pop(position)


# -- pass 6 ---------------------------------------------------------------


def remap_bones(
    links,
    names: Sequence[str],
    index_mapping: Mapping[int, int],
    target_names: Sequence[str],
    fallback_map: Mapping[str, str],
) -> None:
    """Move every link from source bone indices to old-rig bone indices.

    A bone that survives the retarget is looked up in ``index_mapping``.  One
    that does not is redirected through ``fallback_map`` to the nearest bone
    that does.  A bone in neither is a gap in the mapping tables, and is
    raised rather than quietly welded to the root - a silently mis-weighted
    vertex is far harder to notice in game than a failed conversion.
    """
    for link in links:
        if link.bone in index_mapping:
            link.bone = index_mapping[link.bone]
            continue

        bone_name = names[link.bone]
        if bone_name in fallback_map:
            link.bone = target_names.index(fallback_map[bone_name])
            continue

        raise UnmappedBoneError(
            f"Vertex references removed bone index {link.bone} - {bone_name}"
        )


# -- pass 8 ---------------------------------------------------------------


def renormalise(vertex_weight) -> None:
    """Make the weights sum to exactly 1, absorbing the error in the first.

    The passes above split and merge weights repeatedly, so the total drifts.
    The engine renormalises too, but only approximately, and a visible seam
    between two body parts is usually this drift.
    """
    links = vertex_weight.bone_links
    vertex_weight.num_bone_links = len(links)

    if len(links) > 0:
        others = sum(link.blending for link in links[1:])
        links[0].blending = 1.0 - others


# -- the whole sequence ---------------------------------------------------


def rewrite_vertex_weights(
    vertex_weight,
    names: Sequence[str],
    index_mapping: Mapping[int, int],
    target_names: Sequence[str],
    fallback_map: Mapping[str, str],
) -> None:
    """Run every weight pass, in order, on one vertex."""
    links = vertex_weight.bone_links

    collapse_extra_fingers(links, names)
    merge_duplicate_links(links)
    normalise_dominant_finger(links, names)
    dissolve_middle_phalanges(links, names)
    drop_zero_weights(links)
    remap_bones(links, names, index_mapping, target_names, fallback_map)
    merge_duplicate_links(links, reuse=True)
    renormalise(vertex_weight)


# -- bone offsets ---------------------------------------------------------


def average_bone_offset(chunks: SkeletonChunks) -> CgfFormat.Vector3:
    """The mesh-wide constant hidden in every ``BoneLink.offset``.

    A link's offset is the vertex's position in its bone's frame, plus a
    per-file constant whose derivation is not known.  Recovering it as the
    mean residual over every weighted link is accurate to well under a
    texel, and it has to be recovered before the offsets can be rebuilt on
    the new skeleton.
    """
    residuals = []

    for index, vertex in enumerate(chunks.vertices):
        for link in chunks.vertex_weights[index].bone_links:
            if link.blending == 0:
                continue

            matrix = chunks.matrices[link.bone]
            residuals.append(vertex.p - (matrix.pos + link.offset * matrix.rot))

    return mean(residuals)


def rebuild_link_offsets(
    chunks: SkeletonChunks, bone_offset: CgfFormat.Vector3
) -> None:
    """Recompute every link offset against the rebuilt skeleton."""
    for index, vertex in enumerate(chunks.vertices):
        for link in chunks.vertex_weights[index].bone_links:
            matrix = chunks.matrices[link.bone]
            link.offset = (
                vertex.p - matrix.pos - bone_offset
            ) * matrix.rot.get_transpose()
