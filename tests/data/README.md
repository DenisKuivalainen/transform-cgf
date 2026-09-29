# Test fixtures

These `.cgf` files are Aion game assets, included here as regression
fixtures. They are **not** covered by the project's MIT grant, for the same
reason the reference meshes under `tools/reference/` are not.

| File | What it is |
|---|---|
| `input_Body.cgf`, `input_Hand.cgf`, `input_Shoulder.cgf` | Patch-5.x `DMCH_cash_S8EV_*` meshes, 149 bones |
| `output_Body.cgf`, `output_Hand.cgf`, `output_Shoulder.cgf` | The same meshes after a known-good conversion with `model="dm"`, 105 bones |
| `templatedm.cgf` | Old-rig dark-male template |

`templatedm.cgf` was reconstructed from the input/output pair above by
`tools/rebuild_template.py` rather than extracted from the client, because
the conversion is invertible for exactly the bone data a template supplies.
It reproduces the recorded outputs to within float32 file precision, which
is what `tests/test_golden.py` asserts.

If you would rather not carry game assets in the repository, delete this
directory: every test that needs it skips itself when it is absent.
