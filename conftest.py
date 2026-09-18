import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """Bytes of the bundled minimal demo PDF (sample_docs/sample.pdf)."""
    return (ROOT / "sample_docs" / "sample.pdf").read_bytes()
