"""CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from .core import (
    CompressionMethod,
    GroupOptions,
    PackOptions,
    group_files,
    pack_archives,
    scan_files,
)


def _parse_ext(raw: str | None) -> frozenset[str] | None:
    if not raw:
        return None
    items = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return frozenset(x if x.startswith(".") else f".{x}" for x in items) or None


def main() -> int:
    ap = argparse.ArgumentParser(prog="zipper", description="Группировка файлов в ZIP.")
    ap.add_argument("source", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--size", type=float, default=15.0, metavar="MB")
    ap.add_argument("--ext", type=str, default=None, help="например: .jpg,.png")
    ap.add_argument("--prefix", type=str, default="archive")
    ap.add_argument("--compression", choices=[m.value for m in CompressionMethod], default=CompressionMethod.DEFLATE.value)
    ap.add_argument("--no-recursive", action="store_true")
    args = ap.parse_args()

    src: Path = args.source.resolve()
    if not src.is_dir():
        print(f"error: {src} is not a directory", file=sys.stderr)
        return 1

    out: Path = (args.out or (src.parent / "archives")).resolve()
    if out == src or out.is_relative_to(src):
        print("error: output must not be inside source", file=sys.stderr)
        return 1

    group_opts = GroupOptions(
        max_bytes=int(args.size * 1024 * 1024),
        extensions=_parse_ext(args.ext),
        recursive=not args.no_recursive,
    )
    pack_opts = PackOptions(compression=CompressionMethod(args.compression))

    files = scan_files(src, group_opts)
    if not files:
        print("No matching files.")
        return 0
    groups = group_files(files, group_opts)

    def on_progress(i: int, n: int, res: Any) -> None:
        print(f"[{i}/{n}] {res.path.name}: {len(res.files)} file(s), {res.size_bytes} B")

    results = pack_archives(groups, src, out, prefix=args.prefix, pack_options=pack_opts, progress=on_progress)
    print(f"Done: {len(results)} archive(s) in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())