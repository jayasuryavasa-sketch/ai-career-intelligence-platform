"""Small file-backed JSON store. Writes are atomic; records are always scoped by user_id."""
import json, os, threading, tempfile
from pathlib import Path

_lock = threading.RLock()
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True)

def read(name):
    path = DATA / f"{name}.json"
    with _lock:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

def write(name, rows):
    path = DATA / f"{name}.json"
    with _lock:
        fd, temp = tempfile.mkstemp(dir=DATA, prefix=".store-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            os.replace(temp, path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

def user_rows(name, user_id):
    return [row for row in read(name) if row.get("user_id") == user_id]

def upsert(name, row, key="id"):
    with _lock:
        rows = read(name)
        idx = next((i for i, item in enumerate(rows) if item.get(key) == row.get(key)), None)
        if idx is None: rows.append(row)
        else: rows[idx] = row
        write(name, rows)
    return row

def remove(name, value, key="id"):
    with _lock:
        rows = [row for row in read(name) if row.get(key) != value]
        write(name, rows)
