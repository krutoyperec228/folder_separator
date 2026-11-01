"""Zipper — group files into ZIP archives of a target size."""

from .core import (
    ArchiveResult,
    CompressionMethod,
    GroupOptions,
    PackOptions,
    group_files,
    pack_archives,
    scan_files,
)

__all__ = [
    "ArchiveResult",
    "CompressionMethod",
    "GroupOptions",
    "PackOptions",
    "group_files",
    "pack_archives",
    "scan_files",
]

__version__ = "1.0.0"