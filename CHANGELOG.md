# Changelog

## 1.0.0 — refactor

The conversion produces **byte-identical output** to the previous version for
the same inputs and template. That was verified by running both
implementations over the three `DMCH_cash_S8EV_*` meshes and comparing the
written files with `cmp`; `tests/test_golden.py` now pins the same result.

### Structure

- The 1,280-line `transform_cgf.py` and its single `_TransformCgf` class,
  which did all its work as side effects inside `__init__`, is now fourteen
  modules under `src/transform_cgf/`, each with one job. The stage order that
  used to be readable only by scrolling through a constructor is now
  `pipeline.py`.
- The two large lookup tables moved to `bone_maps.py`, and the finger tuning
  that was spread across a ladder of `if "Finger1" in name:` branches inside
  two 500-line methods is now a table in `finger_chains.py`.
- `reskin/reskin_vertex.py` split into `reskin/profiles.py` (data and loading)
  and `reskin/deform.py` (the displacement field). Profile JSON moved into the
  package as `reskin/data/`, so it is found by import rather than by working
  directory.
- `reskin/create_bone_profiles.py` became `tools/build_bone_profiles.py`, with
  its reference meshes under `tools/reference/`. It regenerates the checked-in
  profiles byte for byte, and a test asserts it.

### API

- **`transform_cgf()` now raises instead of printing.** It used to catch
  `ValueError`, print it and return `None`, so a failed conversion looked like
  a successful one. Failures now raise a subclass of `TransformCgfError`
  (`InvalidModelError`, `TemplateNotFoundError`, `AlreadyOldFormatError`,
  `NotAPlayerModelError`, `MalformedCgfError`, `UnmappedBoneError`). **This is
  the one breaking change.**
- It returns a `TransformResult` — output path, bone counts, vertex count, and
  whether the reskin and glove stages ran.
- `input_folder` is joined as a path, so a trailing separator is no longer
  required. It used to be string-concatenated, and omitting the separator
  silently produced a wrong path.
- Added `template_dir`, and the `TRANSFORM_CGF_TEMPLATES` environment variable,
  so templates no longer have to sit in the working directory.
- An invalid `model` is rejected immediately rather than part-way through.

### New

- A real CLI: `transform-cgf` / `python -m transform_cgf`, replacing
  `run_transform_cgf.py`, which had its input path and model as constants to
  be edited before each run. It converts whole directories, skips
  already-converted files rather than failing on them, and returns a
  meaningful exit status.
- `tools/rebuild_template.py`, which recovers an old-rig template from a
  matched before/after pair. The conversion turns out to be invertible for
  exactly the bone data a template supplies, which makes the project testable
  without shipping a template.
- 380 tests, `pyproject.toml`, and `py.typed`-level type hints throughout.

### Performance

Roughly **1.8× faster** (35.4s → 19.5s for the three test meshes). The reskin
field transformed every control point into the evaluated bone's local space
once per vertex; those transforms do not depend on the vertex, so they are now
computed once and cached.

Getting that speedup without changing a single output bit needed three
deliberate choices, each commented where it appears in `reskin/deform.py`:

- Control-point distances are ranked with a cheap whole-array pass, then
  re-measured one at a time for the handful that survive. NumPy's whole-array
  and single-vector norms take different code paths and disagree in the last
  bit, and those bits reach the output through the Gaussian weights.
- The four neighbour weights use scalar `exp`, for the same reason.
- The weighted sum is accumulated in a loop rather than as a matrix product.

### Fixed

- `_get_finger0_rotation` took a `direction_right` argument it ignored.
- `Reskin.__init__` took an `is_hand` argument it never used.
- A dead branch in the glove inflation (`if not close_to_anchors:` inside a
  block only reachable when `close_to_anchors` is false) and its unreachable
  `else`.
- A duplicated, unused local in the finger repositioning.
- `tools/build_bone_profiles.py`: the original chained four progressively
  tighter match tolerances with `or`, but the fallbacks were unreachable —
  the function returns a 2-tuple, which is always truthy. Only the first was
  ever used, so only the first remains. Behaviour, and the generated data,
  are unchanged.
- `.gitattributes` now marks `*.cgf` as binary. With `* text=auto` alone, a
  checkout on a machine configured for CRLF could corrupt the reference
  meshes.

### Documented, not changed

Two inherited quirks in `bone_maps.py` are pinned by tests rather than
"fixed", because both are unreachable today and changing either would alter
output:

- the left/right asymmetry in the ring-finger mapping;
- the `Sub_L_bone_skin*` vertex fallbacks pointing at `R_Sup`.

See "Known quirks" in the README.
