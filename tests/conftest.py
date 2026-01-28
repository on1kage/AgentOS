import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

@pytest.fixture(scope="session", autouse=True)
def _hermetic_store_root(tmp_path_factory):
    p = tmp_path_factory.mktemp("agentos_store")
    os.environ["AGENTOS_STORE_ROOT"] = str(p)
    (p / "evidence").mkdir(parents=True, exist_ok=True)
    (p / "events").mkdir(parents=True, exist_ok=True)
    return p
