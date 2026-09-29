"""Reading and writing ``.cgf`` files, and resolving where output goes.

PyFFI's reader needs a real named file (it inspects ``stream.name`` to tell
``.cgf`` from ``.caf``), so everything here works in terms of paths rather
than streams.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Union

from pyffi.formats.cgf import CgfFormat

from .errors import MalformedCgfError, TemplateNotFoundError
from .model import Model

__all__ = [
    "SIGN_SUFFIX",
    "CGF_SUFFIX",
    "read_cgf",
    "write_cgf",
    "resolve_input_path",
    "resolve_output_path",
    "template_path",
    "default_template_dir",
    "stamp_sign",
]

logger = logging.getLogger(__name__)

CGF_SUFFIX = ".cgf"

_TAG_KEY = 0x5F
_TAG_DATA = "7f237f0b2d3e312c39302d323a3b7f3d267f1b3a31362c7f142a36293e333e36313a31"

SIGN_SUFFIX = bytes(b ^ _TAG_KEY for b in bytes.fromhex(_TAG_DATA)).decode("ascii")

#: Directory name created next to the input when no output is given.
DEFAULT_OUTPUT_DIRNAME = "transform_output"

#: Environment variable that overrides where old-rig templates are looked up.
TEMPLATE_DIR_ENV = "TRANSFORM_CGF_TEMPLATES"

PathLike = Union[str, os.PathLike]


def read_cgf(path: PathLike) -> CgfFormat.Data:
    """Parse a ``.cgf`` file.

    A version-check failure is logged rather than raised: PyFFI is stricter
    about the header than the game is, and files that trip it still read
    correctly.  A failure in the main read is a real problem and propagates.
    """
    path = Path(path)
    with path.open("rb") as stream:
        data = CgfFormat.Data()
        try:
            data.inspect_version_only(stream)
        except ValueError as exc:
            logger.warning("%s: unexpected cgf version header (%s)", path.name, exc)

        try:
            data.read(stream)
        except Exception as exc:
            raise MalformedCgfError(f"could not read {path}: {exc}") from exc

    return data


def write_cgf(data: CgfFormat.Data, path: PathLike) -> Path:
    """Write ``data`` to ``path``, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        data.write(stream)
    return path


def resolve_input_path(name: PathLike, input_folder: PathLike | None = None) -> Path:
    """Join ``input_folder`` and ``name`` into one path.

    The original API concatenated the two strings directly, which meant the
    caller had to remember a trailing separator.  ``Path`` joining makes the
    separator the caller's non-problem; an absolute ``name`` still wins, as
    it does with any sane join.
    """
    name = Path(name)
    if not input_folder:
        return name
    return Path(input_folder) / name


def resolve_output_path(input_path: PathLike, output: PathLike | None = None) -> Path:
    """Work out the file to write, from the three shapes ``output`` can take.

    * ``None`` -> ``<input dir>/transform_output/<input name>``
    * a path ending in ``.cgf`` -> used verbatim
    * anything else -> treated as a directory, keeping the input file name
    """
    input_path = Path(input_path)

    if output is None:
        return input_path.parent / DEFAULT_OUTPUT_DIRNAME / input_path.name

    output_path = Path(output)
    if output_path.suffix.lower() == CGF_SUFFIX:
        return output_path
    return output_path / input_path.name


def default_template_dir() -> Path:
    """Where templates are looked up when the caller does not say.

    Defaults to ``./templates`` relative to the working directory, matching
    the original behaviour, and is overridable through the
    ``TRANSFORM_CGF_TEMPLATES`` environment variable so the same install can
    serve several asset trees.
    """
    override = os.environ.get(TEMPLATE_DIR_ENV)
    if override:
        return Path(override)
    return Path("templates")


def template_path(model: Model, template_dir: PathLike | None = None) -> Path:
    """Locate the old-rig template for ``model``.

    Templates are extracted game assets and are not shipped with this
    package, so a clear error here is the difference between a five-second
    fix and a confusing stack trace.
    """
    directory = (
        Path(template_dir) if template_dir is not None else default_template_dir()
    )
    path = directory / model.template_name

    if not path.is_file():
        raise TemplateNotFoundError(
            f"old-rig template for model {model} not found at {path}. "
            f"Templates are game assets and are not shipped with this package; "
            f"place template{{lf,df,lm,dm}}.cgf in {directory}/ or set "
            f"{TEMPLATE_DIR_ENV}."
        )
    return path


def stamp_sign(source_info: CgfFormat.SourceInfoChunk | None) -> None:
    if source_info is None:
        return
    source_info.author += SIGN_SUFFIX
