"""Pure, testable core logic for grouping files into ZIP archives."""

from __future__ import annotations

import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "ArchiveResult",
    "CompressionMethod",
    "GroupOptions",
    "PackOptions",
    "group_files",
    "pack_archives",
    "scan_files",
]


class CompressionMethod(str, Enum):
    DEFLATE = "deflate"
    STORE = "store"

    def to_zipfile(self) -> int:
        return zipfile.ZIP_DEFLATED if self is CompressionMethod.DEFLATE else zipfile.ZIP_STORED


@dataclass(frozen=True)
class GroupOptions:
    max_bytes: int
    extensions: frozenset[str] | None = None
    recursive: bool = True


@dataclass(frozen=True)
class PackOptions:
    compression: CompressionMethod = CompressionMethod.DEFLATE
    compresslevel: int = 6


@dataclass
class ArchiveResult:
    path: Path
    files: list[Path]
    size_bytes: int


def scan_files(src: Path, options: GroupOptions) -> list[Path]:
    if not src.is_dir():
        raise NotADirectoryError(src)

    it: Iterable[Path] = src.rglob("*") if options.recursive else src.glob("*")
    exts = options.extensions

    files: list[Path] = []
    for p in it:
        if not p.is_file():
            continue
        if exts is not None and p.suffix.lower() not in exts:
            continue
        files.append(p)

    files.sort(key=lambda p: str(p).lower())
    return files


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def group_files(files: list[Path], options: GroupOptions) -> list[list[Path]]:
    if options.max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    ordered = sorted(files, key=_size, reverse=True)
    groups: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0

    for f in ordered:
        size = _size(f)
        if current and current_size + size > options.max_bytes:
            groups.append(current)
            current, current_size = [], 0
        current.append(f)
        current_size += size
    if current:
        groups.append(current)

    return groups


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def pack_archives(
    groups: list[list[Path]],
    src: Path,
    out_dir: Path,
    *,
    prefix: str = "archive",
    pack_options: PackOptions | None = None,
    progress: Callable[[int, int, ArchiveResult], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[ArchiveResult]:
    if not prefix:
        raise ValueError("prefix must be non-empty")

    opts = pack_options or PackOptions()
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(groups)
    width = max(2, len(str(total)))
    results: list[ArchiveResult] = []

    for i, group in enumerate(groups, start=1):
        if should_cancel and should_cancel():
            break

        arc_path = _unique_path(out_dir / f"{prefix}_{i:0{width}d}.zip")
        level = opts.compresslevel if opts.compression is CompressionMethod.DEFLATE else None

        with zipfile.ZipFile(
            arc_path,
            "w",
            compression=opts.compression.to_zipfile(),
            compresslevel=level,
        ) as zf:
            for f in group:
                zf.write(f, arcname=f.relative_to(src))

        result = ArchiveResult(path=arc_path, files=group, size_bytes=arc_path.stat().st_size)
        results.append(result)

        if progress:
            progress(i, total, result)

    return results