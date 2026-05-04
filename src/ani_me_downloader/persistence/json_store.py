# coding: utf-8
"""Atomic JSON read/write helpers."""
import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path, data) -> None:
    """Write JSON to a temp file in the same dir, then atomically replace."""
    path = Path(path)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    )
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def read_json(path, default):
    """Return parsed JSON or `default` if missing/corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default
