"""Locating and validating the chunks the transform operates on.

A ``.cgf`` file is a flat list of typed chunks.  Four of them carry the
skeleton and skinning data this tool rewrites, and the original code found
them with a copy-pasted ``for chunk in data.chunks`` loop in two separate
modules.  :class:`SkeletonChunks` is that loop's result as one object, with
the small conveniences (name -> index lookup, the matrix list) that every
caller was re-deriving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from pyffi.formats.cgf import CgfFormat

from .errors import AlreadyOldFormatError, MalformedCgfError, NotAPlayerModelError

__all__ = ["SkeletonChunks", "find_chunks", "validate_convertible", "MIN_PLAYER_BONES"]

#: A playable-character mesh carries at least this many bones.  Props,
#: weapons and scenery carry far fewer and must not be fed to the transform.
MIN_PLAYER_BONES = 100


@dataclass
class SkeletonChunks:
    """The four chunks that together describe a skinned character mesh.

    Attributes are live references into the parsed ``CgfFormat.Data``; the
    transform mutates them in place and then writes the same ``Data`` back
    out, which is how PyFFI expects a round-trip edit to work.
    """

    bone_names: CgfFormat.BoneNameListChunk
    bone_anim: CgfFormat.BoneAnimChunk
    bone_initial: CgfFormat.BoneInitialPosChunk
    mesh: Optional[CgfFormat.MeshChunk] = None
    source_info: Optional[CgfFormat.SourceInfoChunk] = None

    # -- bone table -----------------------------------------------------

    @property
    def names(self) -> list[str]:
        """Bone names in table order."""
        return [name for name in self.bone_names.names]

    @property
    def bone_count(self) -> int:
        return self.bone_names.num_names

    @property
    def matrices(self):
        """The per-bone initial-pose matrices, in bone-table order."""
        return self.bone_initial.initial_pos_matrices

    def index_of(self, name: str) -> int:
        """Index of ``name`` in the bone table.

        Raises :class:`MalformedCgfError` rather than ``ValueError`` so a
        missing bone surfaces as a file problem, which is what it is.
        """
        try:
            return self.names.index(name)
        except ValueError:
            raise MalformedCgfError(f"bone {name!r} is not in the bone table") from None

    def name_of(self, index: int) -> str:
        return self.bone_names.names[index]

    def has_bone(self, name: str) -> bool:
        return name in self.names

    # -- mesh -----------------------------------------------------------

    @property
    def vertices(self):
        return self.require_mesh().vertices

    @property
    def vertex_weights(self):
        return self.require_mesh().vertex_weights

    def require_mesh(self) -> CgfFormat.MeshChunk:
        if self.mesh is None:
            raise MalformedCgfError("file has no mesh chunk with vertex weights")
        return self.mesh

    def iter_links(self) -> Iterator[tuple[int, object]]:
        """Yield ``(vertex_index, bone_link)`` over the whole mesh."""
        for index, weight in enumerate(self.vertex_weights):
            for link in weight.bone_links:
                yield index, link


def find_chunks(data: CgfFormat.Data, *, require_mesh: bool = True) -> SkeletonChunks:
    """Pick the skeleton and mesh chunks out of a parsed ``.cgf``.

    ``require_mesh`` is off when loading a template, which is read only for
    its bone table and may legitimately carry no skinned mesh.
    """
    bone_names = None
    bone_anim = None
    bone_initial = None
    mesh = None
    source_info = None

    for chunk in data.chunks:
        if isinstance(chunk, CgfFormat.BoneNameListChunk):
            bone_names = chunk
        elif isinstance(chunk, CgfFormat.BoneAnimChunk):
            bone_anim = chunk
        elif isinstance(chunk, CgfFormat.BoneInitialPosChunk):
            bone_initial = chunk
        elif isinstance(chunk, CgfFormat.MeshChunk) and chunk.has_vertex_weights:
            mesh = chunk
        elif isinstance(chunk, CgfFormat.SourceInfoChunk):
            source_info = chunk

    missing = [
        label
        for label, chunk in (
            ("BoneNameList", bone_names),
            ("BoneAnim", bone_anim),
            ("BoneInitialPos", bone_initial),
        )
        if chunk is None
    ]
    if require_mesh and mesh is None:
        missing.append("Mesh(with vertex weights)")
    if missing:
        raise MalformedCgfError(
            "file is missing required chunk(s): " + ", ".join(missing)
        )

    return SkeletonChunks(
        bone_names=bone_names,
        bone_anim=bone_anim,
        bone_initial=bone_initial,
        mesh=mesh,
        source_info=source_info,
    )


def validate_convertible(
    source: SkeletonChunks, template: SkeletonChunks, *, label: str
) -> None:
    """Reject inputs the transform cannot meaningfully convert.

    ``label`` is the file name, used only to make the message actionable.
    """
    if source.bone_count == template.bone_count:
        raise AlreadyOldFormatError(f"{label} is already in old format.")
    if source.bone_count < MIN_PLAYER_BONES:
        raise NotAPlayerModelError(f"{label} is not a PC model.")
