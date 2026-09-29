"""Shared fixtures.

The fixtures that need game assets all route through :func:`data_file`,
which skips the test when the asset is absent.  That keeps the suite
runnable in a checkout with ``tests/data/`` removed - see the README there.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from pyffi.formats.cgf import CgfFormat

from transform_cgf import Model, transform_cgf
from transform_cgf.chunks import SkeletonChunks, find_chunks

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"

#: Where a real, client-extracted template set lives if the user has one.
#: Preferred over anything in tests/data, because the recorded outputs were
#: produced with it and so can be compared byte for byte.
REAL_TEMPLATE_DIR = REPO_ROOT / "templates"

#: Body parts covered by the golden fixtures.
PARTS = ("Body", "Hand", "Shoulder")

#: The model the fixtures were converted with.
FIXTURE_MODEL = "dm"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "slow: runs a full conversion; deselect with -m 'not slow'"
    )
    # PyFFI logs a chunk-size warning for every Aion file; it is expected.
    logging.getLogger("pyffi").setLevel(logging.ERROR)


def data_file(name: str) -> Path:
    """Path to a fixture asset, skipping the test if it is not present."""
    path = DATA_DIR / name
    if not path.is_file():
        pytest.skip(f"game-asset fixture {name} is not present in tests/data/")
    return path


def load(path: Path) -> CgfFormat.Data:
    with Path(path).open("rb") as stream:
        data = CgfFormat.Data()
        data.inspect_version_only(stream)
        data.read(stream)
    return data


def chunks_of(path: Path, *, require_mesh: bool = True) -> SkeletonChunks:
    return find_chunks(load(path), require_mesh=require_mesh)


# -- fixtures -------------------------------------------------------------


@pytest.fixture(scope="session")
def template_dir() -> Path:
    """Where to load old-rig templates from.

    Prefers a real template set at the repository root, falling back to
    anything dropped into ``tests/data``.  Templates are game assets and are
    not committed, so a fresh checkout has neither and the tests that need
    one skip themselves.
    """
    for candidate in (REAL_TEMPLATE_DIR, DATA_DIR):
        if (candidate / "templatedm.cgf").is_file():
            return candidate

    pytest.skip(
        "no old-rig template found; put templatedm.cgf in ./templates/ "
        "(see README) to run the conversion tests"
    )


@pytest.fixture(scope="session")
def templates_are_authentic(template_dir: Path) -> bool:
    """True when the templates came from the client rather than tests/data.

    The recorded ``output_*.cgf`` fixtures were produced with the real
    templates, so with those in place the conversion can be checked for exact
    byte equality.  A reconstructed template (see tools/rebuild_template.py)
    only reproduces them to float32 precision.
    """
    return template_dir == REAL_TEMPLATE_DIR


@pytest.fixture(scope="session")
def model() -> Model:
    return Model(FIXTURE_MODEL)


@pytest.fixture(scope="session")
def template_chunks(template_dir: Path) -> SkeletonChunks:
    return chunks_of(template_dir / "templatedm.cgf", require_mesh=False)


#: The smallest fixture mesh. Tests that only need *a* character mesh use
#: this one, because parsing the body takes five times as long.
SMALLEST_PART = "Shoulder"


@pytest.fixture(params=PARTS)
def part(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def source_chunks() -> SkeletonChunks:
    """A freshly parsed patch-5.x mesh. Safe to mutate."""
    return chunks_of(data_file(f"input_{SMALLEST_PART}.cgf"))


@pytest.fixture
def any_source_chunks(part: str) -> SkeletonChunks:
    """Like ``source_chunks``, but once per body part."""
    return chunks_of(data_file(f"input_{part}.cgf"))


@pytest.fixture(scope="session")
def expected_chunks() -> dict:
    """The recorded good outputs, parsed once. Read-only."""
    return {
        name: chunks_of(data_file(f"output_{name}.cgf")) for name in PARTS
    }


@pytest.fixture(scope="session")
def converted(tmp_path_factory: pytest.TempPathFactory, template_dir: Path) -> dict:
    """Convert every fixture part once, and share the results.

    A full conversion is several seconds per mesh, so this is deliberately
    session-scoped; the tests that use it only read the output.
    """
    out_dir = tmp_path_factory.mktemp("converted")
    results = {}
    for name in PARTS:
        source = data_file(f"input_{name}.cgf")
        results[name] = transform_cgf(
            source,
            out_dir / f"{name}.cgf",
            model=FIXTURE_MODEL,
            template_dir=template_dir,
        )
    return results


@pytest.fixture(scope="session")
def converted_chunks(converted: dict) -> dict:
    """This run's outputs, parsed once. Read-only."""
    return {name: chunks_of(result.output_path) for name, result in converted.items()}
