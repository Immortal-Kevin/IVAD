from pathlib import Path
import pytest
from ivad_app.core.application import ApplicationServices

@pytest.fixture
def services(tmp_path):
    app = ApplicationServices(Path(__file__).resolve().parents[1], tmp_path / 'application', step_seconds=0.01)
    yield app
    app.close()
