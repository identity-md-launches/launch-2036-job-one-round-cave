"""Read-only, bounded ZIP manifest preflight for a cooperative workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import PurePosixPath


class Rejected(ValueError):
    pass


def _positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def _safe_name(name: str) -> None:
    if not name or "\\" in name or name.startswith("/"):
        raise Rejected(f"unsafe member path: {name!r}")
    path = PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts):
        raise Rejected(f"unsafe member path: {name!r}")


def manifest(archive: str, *, max_entries: int = 1000,
             max_archive_bytes: int = 32 * 1024 * 1024,
             max_file_bytes: int = 16 * 1024 * 1024,
             max_total_bytes: int = 64 * 1024 * 1024,
             max_ratio: int = 200) -> dict:
    if not os.path.isfile(archive) or os.path.islink(archive):
        raise Rejected("archive must be a regular file")
    archive_hash = hashlib.sha256()
    total = 0
    seen = set()
    entries = []
    archive_bytes = 0
    with open(archive, "rb") as source:
        while True:
            chunk = source.read(min(1024 * 1024, max_archive_bytes + 1 - archive_bytes))
            if not chunk:
                break
            archive_bytes += len(chunk)
            if archive_bytes > max_archive_bytes:
                raise Rejected("archive-byte limit exceeded")
            archive_hash.update(chunk)
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if len(infos) > max_entries:
                raise Rejected("entry limit exceeded")
            for info in infos:
                _safe_name(info.filename)
                if info.filename in seen:
                    raise Rejected(f"duplicate member path: {info.filename!r}")
                seen.add(info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if stat.S_ISLNK(mode) or (file_type and file_type not in
                                          (stat.S_IFREG, stat.S_IFDIR)):
                    raise Rejected(f"special member refused: {info.filename!r}")
                is_dir = info.is_dir() or info.filename.endswith("/")
                if is_dir:
                    entries.append({"path": info.filename, "kind": "directory"})
                    continue
                if info.file_size > max_file_bytes:
                    raise Rejected(f"file limit exceeded: {info.filename!r}")
                compressed = max(1, info.compress_size)
                if info.file_size > compressed * max_ratio:
                    raise Rejected(f"compression ratio exceeded: {info.filename!r}")
                digest = hashlib.sha256()
                size = 0
                with zf.open(info, "r") as member:
                    while True:
                        chunk = member.read(min(1024 * 64, max_file_bytes + 1 - size))
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > max_file_bytes:
                            raise Rejected(f"file grew beyond limit: {info.filename!r}")
                        digest.update(chunk)
                if size != info.file_size:
                    raise Rejected(f"size mismatch: {info.filename!r}")
                total += size
                if total > max_total_bytes:
                    raise Rejected("total file-byte limit exceeded")
                entries.append({"path": info.filename, "kind": "file",
                                "bytes": size, "sha256": digest.hexdigest()})
    except zipfile.BadZipFile as exc:
        raise Rejected(f"invalid ZIP: {exc}") from exc
    entries.sort(key=lambda item: item["path"])
    return {"ok": True, "archive_sha256": archive_hash.hexdigest(),
            "archive_bytes": archive_bytes,
            "entries": entries, "file_bytes": total, "entry_count": len(entries)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    parser.add_argument("--max-entries", type=_positive, default=1000)
    parser.add_argument("--max-archive-bytes", type=_positive, default=32 * 1024 * 1024)
    parser.add_argument("--max-file-bytes", type=_positive, default=16 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=_positive, default=64 * 1024 * 1024)
    parser.add_argument("--max-ratio", type=_positive, default=200)
    args = parser.parse_args(argv)
    try:
        report = manifest(args.archive, max_entries=args.max_entries,
                          max_archive_bytes=args.max_archive_bytes,
                          max_file_bytes=args.max_file_bytes,
                          max_total_bytes=args.max_total_bytes,
                          max_ratio=args.max_ratio)
    except (OSError, Rejected, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
