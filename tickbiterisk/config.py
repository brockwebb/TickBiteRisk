from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_MANIFEST = PROJECT_ROOT / "docs" / "data-manifest.md"
DEFAULT_BUILD_DIR = PROJECT_ROOT / "build" / "etl"
