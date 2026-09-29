#!/usr/bin/env python3
"""Recover an old-rig template from a matched input/output pair.

Templates are extracted game assets, so they cannot be shipped with this
project.  But the conversion turns out to be invertible for exactly the bone
data a template supplies, so if you have one mesh from before a conversion
and the same mesh after it, you can reconstruct the template that produced
it and use that to convert everything else.

    python tools/rebuild_template.py before.cgf after.cgf templates/templatedm.cgf

How it works, bone by bone:

* **Everything except the fingers** is carried through the conversion
  untouched, so the output's own values are already the template's.
* **Middle and ring fingers** take their pose from the template outright, so
  again the output *is* the template.
* **The thumb and index roots** are re-aimed at the input's orientation, and
  their middle bones follow.  Both the joint bend and the bone length survive
  that re-aim, so they can be read back off the output directly.
* **The male thumb** is additionally eased two thirds of the way from the
  input's orientation towards the template's.  Scaling that rotation by 3/2
  about the same axis undoes it and recovers the template orientation exactly.

The result reproduces the recorded output to within the 32-bit float
precision the file format stores, which is far below anything visible.

This only works for a male model - the female path never reads a template
orientation, so there is nothing to invert.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from transform_cgf.cgf_io import read_cgf, write_cgf  # noqa: E402
from transform_cgf.chunks import find_chunks  # noqa: E402
from transform_cgf.math3d import partial_rotation  # noqa: E402

#: The male thumb is eased this far towards the template; see MALE_TUNING[0].
THUMB_EASE_FACTOR = 2 / 3

THUMB_CHAINS = (
    ("Bip01 L Finger0", "Bip01 L Finger01"),
    ("Bip01 R Finger0", "Bip01 R Finger01"),
)


def rebuild(before_path: Path, after_path: Path) -> object:
    """Return the converted file's data, with its thumbs put back."""
    before = find_chunks(read_cgf(before_path))
    after_data = read_cgf(after_path)
    after = find_chunks(after_data)

    for root_name, middle_name in THUMB_CHAINS:
        source_rot = before.matrices[before.index_of(root_name)].rot
        root = after.matrices[after.index_of(root_name)]
        middle = after.matrices[after.index_of(middle_name)]

        # Undo the ease: the output sits 2/3 of the way from the input's
        # orientation to the template's, about a single axis.
        template_rot = source_rot * partial_rotation(
            source_rot.get_transpose() * root.rot, 1.0 / THUMB_EASE_FACTOR
        )

        # These two survive the re-aim unchanged, so they read straight off.
        knuckle_bend = root.rot.get_transpose() * middle.rot
        bone_vector = (middle.pos - root.pos) * root.rot.get_transpose()

        middle.pos = root.pos + bone_vector * template_rot
        middle.rot = template_rot * knuckle_bend
        root.rot = template_rot

    return after_data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("before", type=Path, help="the mesh before conversion")
    parser.add_argument("after", type=Path, help="the same mesh after conversion")
    parser.add_argument("output", type=Path, help="where to write the template")
    args = parser.parse_args(argv)

    write_cgf(rebuild(args.before, args.after), args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
