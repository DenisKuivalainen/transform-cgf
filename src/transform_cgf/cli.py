"""Command-line interface.

The original shipped a ``run_transform_cgf.py`` with the input path and
model as module-level constants to be edited before each run.  Converting a
character means converting four or five meshes, so batching and a real
argument list are the difference between a minute's work and twenty.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Sequence

from . import __version__, cgf_io
from .errors import TransformCgfError, UnsupportedModelError
from .model import MODEL_CODES, Model
from .pipeline import transform_file

__all__ = ["main", "build_parser"]

logger = logging.getLogger("transform_cgf")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transform-cgf",
        description=(
            "Convert Aion character meshes (.cgf) from the patch-5.x "
            "skeleton back to the layout older clients expect."
        ),
        epilog=(
            "Old-rig templates are game assets and are not shipped with this "
            "tool. Put template{lf,df,lm,dm}.cgf in ./templates, or point "
            "--templates (or $%s) at them." % cgf_io.TEMPLATE_DIR_ENV
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        metavar="INPUT",
        help=".cgf file(s) to convert; directories are searched for *.cgf",
    )
    parser.add_argument(
        "-m",
        "--model",
        required=True,
        choices=MODEL_CODES,
        help="target model: race letter (l/d) then gender letter (f/m)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "output directory, or an exact .cgf path when converting a "
            "single file; default: a transform_output/ next to each input"
        ),
    )
    parser.add_argument(
        "-t",
        "--templates",
        type=Path,
        default=None,
        metavar="DIR",
        help="directory holding the old-rig templates (default: ./templates)",
    )
    parser.add_argument(
        "-k",
        "--keep-going",
        action="store_true",
        help="carry on after a file that cannot be converted",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log each stage",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _expand(inputs: Iterable[Path]) -> list[Path]:
    """Turn the argument list into a flat list of ``.cgf`` files."""
    found: list[Path] = []
    for path in inputs:
        if path.is_dir():
            found.extend(sorted(path.rglob("*.cgf")))
        else:
            found.append(path)
    return found


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    model = Model(args.model)
    files = _expand(args.inputs)

    if not files:
        logger.error("no .cgf files found")
        return 2

    if args.output is not None and args.output.suffix.lower() == cgf_io.CGF_SUFFIX:
        if len(files) > 1:
            logger.error(
                "--output names a single .cgf file but %d inputs were given",
                len(files),
            )
            return 2

    failures = 0
    for path in files:
        output_path = cgf_io.resolve_output_path(path, args.output)
        try:
            result = transform_file(path, output_path, model, args.templates)
        except UnsupportedModelError as exc:
            # Not an error so much as a file that did not need converting;
            # common when a whole directory is pointed at the tool.
            logger.info("skipped %s: %s", path.name, exc)
            continue
        except TransformCgfError as exc:
            failures += 1
            logger.error("failed %s: %s", path.name, exc)
            if not args.keep_going:
                return 1
            continue

        logger.info(
            "%s -> %s (%d bones -> %d, %d vertices)",
            path.name,
            result.output_path,
            result.source_bone_count,
            result.target_bone_count,
            result.vertex_count,
        )

    return 1 if failures else 0
