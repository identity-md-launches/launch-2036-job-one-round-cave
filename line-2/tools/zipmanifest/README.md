# ZipManifest

Create a reviewable, read-only manifest of every member in an untrusted ZIP
before extraction. It hashes file contents, reports the archive SHA-256, and
refuses traversal paths, duplicate names, symlinks/special files, excessive
archive bytes or entries, oversized files, total output, or compression
ratios. It never writes archive contents and uses only Python's standard
library.

Run this one command from the repository root:

```sh
python3 -B line-2/tools/zipmanifest/demo.py
```

Tried here: the demo accepted a two-member in-memory archive and reported the
exact file hash, then refused a `../escape.txt` member before any extraction.
The demo creates only disposable files under `test/scratch/`. For a real
archive, use `python3 -B line-2/tools/zipmanifest/zipmanifest.py incoming.zip`
and review the emitted digest and entries before passing the same archive to a
bounded extractor such as ZipGate/SafeZip.

This is a preflight report, not publisher authentication or a hard OS sandbox.
The archive must remain unchanged while a later extractor rereads it; use the
extractor's own approved digest and limits as the final enforcement step.
