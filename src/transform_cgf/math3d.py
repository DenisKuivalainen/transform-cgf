"""Small rotation / vector helpers built on PyFFI's ``Matrix33`` and ``Vector3``.

These were previously private methods on the transform class even though none
of them touched its state.  They are pure functions of their arguments, so
they live here where they can be unit-tested on their own.

Convention note: PyFFI multiplies a ``Vector3`` by a ``Matrix33`` as a *row*
vector (``v * M``), which is the convention CryEngine's ``.cgf`` bone matrices
use.  Every helper below is written to match that, so ``local * rot + pos``
takes a bone-local point to world space.
"""

from __future__ import annotations

from math import acos, cos, radians, sin
from typing import Iterable, Sequence

from pyffi.formats.cgf import CgfFormat

__all__ = [
    "identity",
    "rotation_x",
    "rotation_y",
    "partial_rotation",
    "make_vector",
    "mean",
    "to_local",
    "to_world",
]

#: Below this angle (radians) a rotation is treated as the identity.
_ANGLE_EPSILON = 1e-8


def identity() -> CgfFormat.Matrix33:
    """Return a fresh identity matrix."""
    m = CgfFormat.Matrix33()
    m.set_identity()
    return m


def rotation_x(angle_degrees: float) -> CgfFormat.Matrix33:
    """Rotation of ``-angle_degrees`` about the X axis.

    The sign is inverted to match the original ``_get_finger0_rotation``,
    whose callers pass the angle they want the thumb to swing *towards*.
    """
    angle = radians(-angle_degrees)
    c = cos(angle)
    s = sin(angle)

    r = CgfFormat.Matrix33()
    r.m_11 = 1.0
    r.m_12 = 0.0
    r.m_13 = 0.0
    r.m_21 = 0.0
    r.m_22 = c
    r.m_23 = -s
    r.m_31 = 0.0
    r.m_32 = s
    r.m_33 = c
    return r


def rotation_y(angle_degrees: float, mirrored: bool = False) -> CgfFormat.Matrix33:
    """Rotation about the Y axis, negated when ``mirrored``.

    Finger tuning angles are authored for one hand; the other hand mirrors
    them, which for a Y-axis swing is simply a sign flip.
    """
    angle = radians(angle_degrees if not mirrored else -angle_degrees)
    c = cos(angle)
    s = sin(angle)

    r = CgfFormat.Matrix33()
    r.m_11 = c
    r.m_12 = 0.0
    r.m_13 = s
    r.m_21 = 0.0
    r.m_22 = 1.0
    r.m_23 = 0.0
    r.m_31 = -s
    r.m_32 = 0.0
    r.m_33 = c
    return r


def partial_rotation(rotation: CgfFormat.Matrix33, factor: float) -> CgfFormat.Matrix33:
    """Scale ``rotation`` to ``factor`` of its angle about the same axis.

    ``factor=0`` gives the identity and ``factor=1`` gives ``rotation`` back;
    values in between interpolate, which is how the finger retarget eases a
    bone part of the way towards its old-rig orientation.  Values above 1
    extrapolate, which the template-recovery tooling relies on.
    """
    trace = rotation.m_11 + rotation.m_22 + rotation.m_33
    cos_angle = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
    angle = acos(cos_angle)

    if abs(angle) < _ANGLE_EPSILON:
        return identity()

    two_sin = 2.0 * sin(angle)

    x = (rotation.m_32 - rotation.m_23) / two_sin
    y = (rotation.m_13 - rotation.m_31) / two_sin
    z = (rotation.m_21 - rotation.m_12) / two_sin

    angle *= factor

    c = cos(angle)
    s = sin(angle)
    t = 1.0 - c

    m = CgfFormat.Matrix33()
    m.m_11 = t * x * x + c
    m.m_12 = t * x * y - s * z
    m.m_13 = t * x * z + s * y

    m.m_21 = t * x * y + s * z
    m.m_22 = t * y * y + c
    m.m_23 = t * y * z - s * x

    m.m_31 = t * x * z - s * y
    m.m_32 = t * y * z + s * x
    m.m_33 = t * z * z + c
    return m


def make_vector(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> CgfFormat.Vector3:
    """Build a ``Vector3``; PyFFI's constructor takes no coordinates."""
    v = CgfFormat.Vector3()
    v.x = x
    v.y = y
    v.z = z
    return v


def mean(vectors: Sequence[CgfFormat.Vector3]) -> CgfFormat.Vector3:
    """Component-wise arithmetic mean of ``vectors``.

    Raises ``ZeroDivisionError`` on an empty sequence rather than silently
    returning the origin, because an empty sample means the caller looked at
    a mesh with no weighted vertices and should hear about it.
    """
    total = CgfFormat.Vector3()
    for v in vectors:
        total += v

    count = len(vectors)
    total.x = total.x / count
    total.y = total.y / count
    total.z = total.z / count
    return total


def to_local(
    point: CgfFormat.Vector3,
    bone_pos: CgfFormat.Vector3,
    bone_rot: CgfFormat.Matrix33,
) -> CgfFormat.Vector3:
    """Express a world-space ``point`` in a bone's local frame."""
    return (point - bone_pos) * bone_rot.get_transpose()


def to_world(
    local: CgfFormat.Vector3,
    bone_pos: CgfFormat.Vector3,
    bone_rot: CgfFormat.Matrix33,
) -> CgfFormat.Vector3:
    """Inverse of :func:`to_local`."""
    return local * bone_rot + bone_pos
