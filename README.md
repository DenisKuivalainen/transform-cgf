DO NOT modify any `.cfg` files in this folder, as the script uses them as references for the old skeleton.

Use Python 3.11.

To test the script, modify `INPUT_FILE` and/or `model` in `run_transform_cgf.py`.

To use the script:

```python
from transform_cgf import transform_cgf

transform_cgf(INPUT_FILE, model="lf")
# or
transform_cgf(INPUT_FILE, OUTPUT_FOLDER, model="lf")
```

**NOTE!** Input file should have standard Аiоn naming, e.g. it should start with `LF`, `DF`, `LM` or `LF` (lower or capital).
