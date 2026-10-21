"""
scanner.py - finds files that share a name but differ only by "equivalent"
extensions (photo_1.jpg + photo_1.png).

No GUI code lives here. That separation means you can test this file from
a terminal, and later swap customtkinter for something else without
touching the logic.
"""

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Extension categories
# ---------------------------------------------------------------------------
# Two files "collide" only if they share a stem AND belong to the same
# category. Anything not listed here (like .srt) becomes its own category,
# so movie.mp4 + movie.srt is NOT flagged.
#
# Feel free to edit these sets - this is the "rules" of your program.

CATEGORIES: dict[str, set[str]] = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic"},
    "video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "document": {".pdf", ".doc", ".docx", ".odt", ".rtf"},
    "text": {".txt", ".md"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
}

# Build a reverse lookup once: {".jpg": "image", ".png": "image", ...}
# A dict lookup is O(1); looping over CATEGORIES for every file would be slow.
EXT_TO_CATEGORY: dict[str, str] = {
    ext: category for category, exts in CATEGORIES.items() for ext in exts
}


def category_of(extension: str) -> str:
    """Return the category for an extension like '.jpg'.

    Unknown extensions get a category of their own (e.g. 'other:.srt'),
    so they only ever match files with the exact same extension.
    """
    return EXT_TO_CATEGORY.get(extension, f"other:{extension}")


# ---------------------------------------------------------------------------
# 2. Data containers
# ---------------------------------------------------------------------------
# A dataclass is a class whose boilerplate (__init__, __repr__...) is written
# for you. Use it when a class is mostly "a bundle of named values".

@dataclass(frozen=True)  # frozen = immutable, which also makes it hashable
class FileInfo:
    path: Path
    size: int  # bytes


@dataclass
class DuplicateGroup:
    name: str          # the shared stem, e.g. "photo_1"
    category: str      # e.g. "image"
    files: list[FileInfo]


# ---------------------------------------------------------------------------
# 3. The scan itself
# ---------------------------------------------------------------------------

def _normalize_roots(roots) -> list[Path]:
    """Turn whatever the caller passed into a clean list of root folders.

    Accepts one path (str/Path) or any iterable of them. Removes exact
    repeats AND folders nested inside another selected folder - otherwise
    their files would be visited twice and a file would "duplicate" itself.
    """
    if isinstance(roots, (str, os.PathLike)):
        roots = [roots]

    # resolve() makes paths absolute so "a/../a" and "a" compare as equal.
    # The set removes exact repeats; sorting by depth puts parents BEFORE
    # their children, so one pass is enough to spot the nested ones.
    resolved = sorted({Path(r).resolve() for r in roots}, key=lambda p: len(p.parts))

    kept: list[Path] = []
    for root in resolved:
        if not any(root.is_relative_to(parent) for parent in kept):
            kept.append(root)
    return kept


def _iter_files(roots):
    """Yield (directory, filename) for every file under every root.

    This is a *generator*: `yield` hands back one item at a time and pauses,
    instead of building a giant list first. The caller just writes a plain
    `for` loop and never needs to know there are several roots behind it.
    """
    for root in _normalize_roots(roots):
        # os.walk yields (current_dir, subdirs, filenames) for every folder
        # in the tree, top to bottom.
        for dirpath, _subdirs, filenames in os.walk(root):
            for filename in filenames:
                yield dirpath, filename


def find_duplicates(roots, same_folder_only: bool = False) -> list[DuplicateGroup]:
    """Walk one or more root folders and return groups of files that share
    a name + category.

    `roots` may be a single path or a list of paths. Files from ALL roots go
    into the same buckets, so separate locations are compared with each other.

    same_folder_only=True  -> only compare files living in the same directory
    same_folder_only=False -> compare across the entire tree
    """
    # defaultdict(list): accessing a missing key creates an empty list for
    # it, so we can append without checking whether the key exists first.
    buckets: dict[tuple, list[FileInfo]] = defaultdict(list)

    for dirpath, filename in _iter_files(roots):
        path = Path(dirpath) / filename

        try:
            size = path.stat().st_size
        except OSError:
            # Broken symlink, permission problem, file vanished mid-scan...
            # One bad file shouldn't kill the whole scan.
            continue

        # .lower() so "Photo_1.JPG" matches "photo_1.png"
        stem = path.stem.lower()
        category = category_of(path.suffix.lower())

        # The key is the heart of the whole program: files with an
        # identical key land in the same bucket. Tuples can be dict
        # keys because they're immutable.
        key = (stem, category)
        if same_folder_only:
            key = (dirpath, *key)

        buckets[key].append(FileInfo(path, size))

    # A bucket with only one file isn't a duplicate - drop it.
    groups = []
    for key, files in buckets.items():
        if len(files) > 1:
            stem, category = key[-2], key[-1]  # works for both key shapes
            groups.append(DuplicateGroup(stem, category, sorted(files, key=lambda f: str(f.path))))

    groups.sort(key=lambda g: g.name)
    return groups


# ---------------------------------------------------------------------------
# Quick manual test:  python scanner.py /some/folder
# `__name__ == "__main__"` is only true when you run THIS file directly,
# not when another file imports it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    for group in find_duplicates(folder):
        print(f"\n[{group.category}] {group.name}")
        for f in group.files:
            print(f"   {f.size:>10,} B  {f.path}")