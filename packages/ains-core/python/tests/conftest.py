import os
import tempfile
import subprocess
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

# Your real app - metrics auto-init via middleware
from ains.api import app


@contextmanager
def temp_test_db():
    """Temp DB that runs your init_db.py"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_ains.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        
        # Run YOUR init_db.py (creates 13 tables)
        subprocess.run(["python", "init_db.py"], check=True, cwd=".")
        yield


@pytest.fixture(scope="session")
def client():
    """TestClient with fresh temp DB per session"""
    with temp_test_db():
        with TestClient(app) as c:
            yield c


@pytest.fixture(autouse=True)
def fresh_db_per_test(client):
    """Reset DB before EVERY test (runs init_db.py each time)"""
    subprocess.run(["python", "init_db.py"], check=True, cwd=".")
    yield
