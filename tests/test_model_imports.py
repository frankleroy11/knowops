"""Guard against cross-module foreign keys that only resolve inside the API process.

Celery tasks import a subset of the models. If a foreign key points at a table
from another module that was never imported, SQLAlchemy fails at flush time with
NoReferencedTableError - which previously broke every ingestion task.
"""

import subprocess
import sys

IMPORT_PATHS = [
    "app.modules.knowledge.models",
    "app.modules.ingestion.service",
    "app.modules.retrieval.service",
]

PROBE = """
from sqlalchemy.orm import configure_mappers
import {module}
configure_mappers()
print("ok")
"""


def test_model_import_paths_resolve_foreign_keys():
    for module in IMPORT_PATHS:
        result = subprocess.run(
            [sys.executable, "-c", PROBE.format(module=module)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"{module}: {result.stderr.strip()[-600:]}"
        assert result.stdout.strip() == "ok"
