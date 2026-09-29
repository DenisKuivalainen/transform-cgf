"""Convenience runner, kept for habit. The CLI is usually easier:

    transform-cgf DMCH_cash_S8EV_Hand.cgf --model dm
    python -m transform_cgf mesh/ --model dm --output converted/

Edit INPUT and MODEL below and run `python run_transform_cgf.py`.

This works from a fresh checkout without installing anything; the CLI names
above need `pip install -e .` first.
"""

import sys
from pathlib import Path

# The package lives under src/, so make it importable when this script is run
# straight out of the repository rather than from an installed copy.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from transform_cgf import TransformCgfError, transform_cgf  # noqa: E402

INPUT = "DMCH_cash_S8EV_Hand.cgf"
MODEL = "dm"

# Output directory, or an exact .cgf path. None puts it in transform_output/
# next to the input.
OUTPUT = None


def main() -> int:
    try:
        result = transform_cgf(INPUT, OUTPUT, model=MODEL)
    except TransformCgfError as exc:
        # Unlike the pre-1.0 version, failures raise rather than print.
        print(f"failed: {exc}")
        return 1

    print(
        f"{result.output_path} "
        f"({result.source_bone_count} bones -> {result.target_bone_count}, "
        f"{result.vertex_count} vertices)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
