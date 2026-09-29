"""Convert Aion character meshes from the patch-5.x rig back to the old one.

Newer character assets carry a larger skeleton (151 bones for female models,
149 for male) than the old one (107 / 105), use five finger chains per hand
instead of three, and share one body shape between both playable races.  An
older client cannot load them.  This package rewrites them so it can.

Typical use::

    from transform_cgf import transform_cgf

    transform_cgf("DMCH_cash_S8EV_Hand.cgf", model="dm")

See ``transform_cgf.pipeline`` for the stages the conversion runs through.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional, Union

from . import cgf_io
from .errors import (
    AlreadyOldFormatError,
    InvalidModelError,
    MalformedCgfError,
    NotAPlayerModelError,
    TemplateNotFoundError,
    TransformCgfError,
    UnmappedBoneError,
    UnsupportedModelError,
)
from .model import MODEL_CODES, Model, ModelCode
from .pipeline import TransformPipeline, TransformResult, transform_file

__all__ = [
    "transform_cgf",
    "transform_file",
    "TransformPipeline",
    "TransformResult",
    "Model",
    "ModelCode",
    "MODEL_CODES",
    "TransformCgfError",
    "InvalidModelError",
    "TemplateNotFoundError",
    "MalformedCgfError",
    "UnsupportedModelError",
    "AlreadyOldFormatError",
    "NotAPlayerModelError",
    "UnmappedBoneError",
    "__version__",
]

__version__ = "1.0.0"


def transform_cgf(
    input: Union[str, Path],
    output: Union[str, Path, None] = None,
    input_folder: Union[str, Path, None] = None,
    model: Union[Model, ModelCode, str] = "lm",
    template_dir: Union[str, Path, None] = None,
) -> TransformResult:
    """Transform one patch-5.x ``.cgf`` into the format older patches use.

    Args:
        input: The ``.cgf`` file to convert.  May be a bare name, in which
            case ``input_folder`` says where to find it.
        output: Where to write the result.  A path ending in ``.cgf`` is
            used verbatim; anything else is treated as a directory and the
            input's file name is kept.  When omitted, a ``transform_output``
            directory is created next to the input.
        input_folder: Directory holding ``input``.  Joined with ``input`` as
            a path, so a trailing separator is neither needed nor a problem.
        model: Target model code - ``lf``, ``df``, ``lm`` or ``dm`` (race
            letter then gender letter).  Selects the old-rig template and
            decides whether the body reskin and glove inflation run.
        template_dir: Where to look for ``template{lf,df,lm,dm}.cgf``.
            Defaults to the ``TRANSFORM_CGF_TEMPLATES`` environment variable
            if set, otherwise ``./templates``.

    Returns:
        A :class:`~transform_cgf.pipeline.TransformResult` describing what
        was written.

    Raises:
        InvalidModelError: ``model`` is not one of the four codes.
        TemplateNotFoundError: the old-rig template is missing.
        AlreadyOldFormatError: the input already uses the old skeleton.
        NotAPlayerModelError: the input is not a character mesh.
        MalformedCgfError: the input is missing a chunk, or a bone, the
            conversion needs.
        UnmappedBoneError: a vertex references a bone with no old-rig
            counterpart, which means the bone tables need an entry adding.

    Note:
        Unlike the pre-1.0 function of the same name, this raises on failure
        instead of printing and returning ``None``.  Catch
        :class:`TransformCgfError` to handle every failure mode at once.
    """
    parsed_model = Model.parse(model)
    input_path = cgf_io.resolve_input_path(input, input_folder)
    output_path = cgf_io.resolve_output_path(input_path, output)

    return transform_file(input_path, output_path, parsed_model, template_dir)
