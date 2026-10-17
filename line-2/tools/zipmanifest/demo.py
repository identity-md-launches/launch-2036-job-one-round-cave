import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zipmanifest import Rejected, manifest


def archive(*members):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members:
            zf.writestr(name, data)
    return out.getvalue()


def main():
    root = Path("test/scratch/zipmanifest")
    root.mkdir(parents=True, exist_ok=True)
    safe = root / "safe.zip"
    safe.write_bytes(archive(("docs/readme.txt", b"manifested bytes"),
                             ("empty/", b"")))
    report = manifest(str(safe), max_entries=3, max_total_bytes=100)
    assert report["ok"] and report["file_bytes"] == 16
    bad = root / "bad.zip"
    bad.write_bytes(archive(("../escape.txt", b"no")))
    try:
        manifest(str(bad))
    except Rejected as exc:
        refused = str(exc)
    else:
        raise AssertionError("unsafe path was accepted")
    print(json.dumps({"ok": True, "safe_manifest": report,
                      "unsafe_archive_refused": refused}, indent=2,
                     sort_keys=True))


if __name__ == "__main__":
    main()
