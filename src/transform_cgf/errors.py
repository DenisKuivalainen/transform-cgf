"""Exception hierarchy for :mod:`transform_cgf`.

Every failure the package raises deliberately derives from
:class:`TransformCgfError`, so callers can catch the whole family with a
single ``except`` and still discriminate on the concrete type when they
care about the reason.
"""

from __future__ import annotations

__all__ = [
    "TransformCgfError",
    "InvalidModelError",
    "TemplateNotFoundError",
    "MalformedCgfError",
    "UnsupportedModelError",
    "AlreadyOldFormatError",
    "NotAPlayerModelError",
    "UnmappedBoneError",
]


class TransformCgfError(Exception):
    """Base class for every error raised by this package."""


class InvalidModelError(TransformCgfError, ValueError):
    """The requested model code is not one of ``lf``, ``df``, ``lm``, ``dm``."""


class TemplateNotFoundError(TransformCgfError, FileNotFoundError):
    """The old-rig template for the requested model could not be located."""


class MalformedCgfError(TransformCgfError, ValueError):
    """A ``.cgf`` file is missing a chunk the transform depends on."""


class UnsupportedModelError(TransformCgfError, ValueError):
    """The input file is not something this tool can convert.

    Base class for the two concrete cases below so callers that merely want
    to skip unconvertible files can catch one type.
    """


class AlreadyOldFormatError(UnsupportedModelError):
    """The input already uses the old skeleton, so there is nothing to do."""


class NotAPlayerModelError(UnsupportedModelError):
    """The input has too few bones to be a playable-character mesh."""


class UnmappedBoneError(TransformCgfError, RuntimeError):
    """A vertex references a bone that has no counterpart in the old rig."""
