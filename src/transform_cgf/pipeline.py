"""The conversion pipeline: the stages, in order, and what each one is for.

Each stage is implemented in its own module; this file exists so that the
*shape* of the conversion is readable in one screen, which in the original
it was not - the whole thing ran as a sequence of side effects inside a
constructor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from pyffi.formats.cgf import CgfFormat

from . import cgf_io, retarget, skinning
from .bone_maps import VERTEX_BONE_FALLBACK_MAP
from .chunks import SkeletonChunks, find_chunks, validate_convertible
from .fingers import reposition_fingers
from .gloves import inflate_gloves
from .model import Model
from .reskin.deform import ReskinDeformer, VertexBone
from .reskin.profiles import load_profiles

__all__ = ["TransformResult", "TransformPipeline", "transform_file"]

logger = logging.getLogger(__name__)

#: Meshes whose name contains this are hand/glove meshes.
_HAND_MESH_MARKER = "hand"


@dataclass(frozen=True)
class TransformResult:
    """What a conversion produced, for callers that want more than a file."""

    input_path: Path
    output_path: Path
    model: Model
    source_bone_count: int
    target_bone_count: int
    vertex_count: int
    reskinned: bool
    gloves_inflated: bool


class TransformPipeline:
    """Converts one ``.cgf`` from the patch-5.x rig to the old rig.

    Build it with the paths and model, then call :meth:`run`.  An instance
    holds the parsed file, so it is single-use; :func:`transform_file` is
    the convenience wrapper most callers want.
    """

    def __init__(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        model: Model,
        template_dir: Union[str, Path, None] = None,
    ) -> None:
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.model = model
        self.template_dir = template_dir

        self._deformer: Optional[ReskinDeformer] = None

    # -- stages ---------------------------------------------------------

    def run(self) -> TransformResult:
        """Execute every stage and write the result."""
        template = self._load_template()
        data, chunks = self._load_input()

        validate_convertible(chunks, template, label=str(self.input_path))

        source_bone_count = chunks.bone_count
        vertex_count = len(chunks.vertices)

        # The per-link offsets encode a constant that has to be recovered
        # from the input's own skeleton, before that skeleton is rebuilt.
        bone_offset = skinning.average_bone_offset(chunks)

        # Fingers move while all ten chains still exist; afterwards there is
        # no ring finger left to read a pose from.
        reposition_fingers(chunks, template, is_male=self.model.is_male)

        self._retarget(chunks, template)

        reskinned = self._reskin(chunks)
        gloves_inflated = self._inflate_gloves(chunks)

        # Offsets are rebuilt last: every stage above moves either vertices
        # or bones, and the offset is the relationship between the two.
        skinning.rebuild_link_offsets(chunks, bone_offset)

        cgf_io.write_cgf(data, self.output_path)

        return TransformResult(
            input_path=self.input_path,
            output_path=self.output_path,
            model=self.model,
            source_bone_count=source_bone_count,
            target_bone_count=chunks.bone_count,
            vertex_count=vertex_count,
            reskinned=reskinned,
            gloves_inflated=gloves_inflated,
        )

    # -- internals ------------------------------------------------------

    def _load_template(self) -> SkeletonChunks:
        path = cgf_io.template_path(self.model, self.template_dir)
        return find_chunks(cgf_io.read_cgf(path), require_mesh=False)

    def _load_input(self) -> tuple[CgfFormat.Data, SkeletonChunks]:
        data = cgf_io.read_cgf(self.input_path)
        chunks = find_chunks(data)
        cgf_io.stamp_sign(chunks.source_info)
        return data, chunks

    def _retarget(self, chunks: SkeletonChunks, template: SkeletonChunks) -> None:
        rebuild = retarget.build_bone_table(chunks, template)
        retarget.rebase_old_rig_fingers(rebuild, template)

        for vertex_weight in chunks.vertex_weights:
            skinning.rewrite_vertex_weights(
                vertex_weight,
                rebuild.source_names,
                rebuild.index_mapping,
                rebuild.names,
                VERTEX_BONE_FALLBACK_MAP,
            )

        retarget.commit(chunks, rebuild)

    @property
    def deformer(self) -> ReskinDeformer:
        """The reskin field for this model's gender, loaded on first use."""
        if self._deformer is None:
            self._deformer = ReskinDeformer(load_profiles(self.model.profile_name))
        return self._deformer

    def _reskin(self, chunks: SkeletonChunks) -> bool:
        """Move the shared body onto the old race-specific one.

        Only dark models need this; light models already match the body the
        old client expects.
        """
        if not self.model.is_dark:
            return False

        names = chunks.names
        for index, vertex in enumerate(chunks.vertices):
            x, y, z = self.deformer.transform_vertex(
                [vertex.p.x, vertex.p.y, vertex.p.z],
                [
                    VertexBone(names[link.bone], link.blending)
                    for link in chunks.vertex_weights[index].bone_links
                ],
            )
            vertex.p.x = x
            vertex.p.y = y
            vertex.p.z = z

        return True

    def _inflate_gloves(self, chunks: SkeletonChunks) -> bool:
        if not self.model.is_male:
            return False
        if _HAND_MESH_MARKER not in self.input_path.name.lower():
            return False

        return inflate_gloves(chunks, self.deformer, is_dark=self.model.is_dark)


def transform_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    model: Model,
    template_dir: Union[str, Path, None] = None,
) -> TransformResult:
    """Convert one file. See :func:`transform_cgf.transform_cgf` for the API."""
    return TransformPipeline(input_path, output_path, model, template_dir).run()
