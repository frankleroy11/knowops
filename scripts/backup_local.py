"""Offline application backup: MySQL authority + original uploads.

Stop API and KnowOps workers before invoking --writers-stopped. Milvus is derived
and must be rebuilt after restore; this is not an online distributed snapshot.
"""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--writers-stopped", action="store_true", required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(target, 0o700)
    container = subprocess.check_output(
        ["docker", "compose", "ps", "-q", "mysql"], cwd=ROOT, text=True
    ).strip()
    if not container:
        raise RuntimeError("Project MySQL container not running")
    sql = target / "mysql.sql"
    # Variable expansion happens inside this project's container, never in tool text.
    command = [
        "docker",
        "exec",
        container,
        "sh",
        "-c",
        ('MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump -u"$MYSQL_USER" --single-transaction '
        '--no-tablespaces --set-gtid-purged=OFF --hex-blob "$MYSQL_DATABASE"'),
    ]
    with sql.open("xb") as f:
        os.chmod(sql, 0o600)
        subprocess.run(command, stdout=f, check=True)
    archive = target / "storage.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(ROOT / "storage", arcname="storage")
    os.chmod(archive, 0o600)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "authority": "mysql + original files",
        "milvus": "not included; rebuild required",
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (sql, archive)},
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Backup created:", target)


if __name__ == "__main__":
    main()
