import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CATEGORIES: dict[str, set[str]] = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic"},
    "video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "document": {".pdf", ".doc", ".docx", ".odt", ".rtf"},
    "text": {".txt", ".md"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
}

EXT_TO_CATEGORY: dict[str, str] = {
    ext: category for category, exts in CATEGORIES.items() for ext in exts
}

def category_of(extension:str) -> str:
    return EXT_TO_CATEGORY.get(extension, f"other:{extension}")


@dataclass(frozen=True)
class FileInfo:
    path: Path
    size: int # bytes

@dataclass
class DuplicateGroup:
    name: str
    category: str
    files: list[FileInfo]

def find_duplicates(root: str | Path, same_folder_only:bool = False) -> list[DuplicateGroup]:

    buckets: dict[tuple, list[FileInfo]] = defaultdict(list)

    for dirpath, _subdirs, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename

            try:
                size = path.stat().st_size
            except OSError:
                continue

            stem = path.stem.lower()
            category = category_of(path.suffix.lower())

            key = (stem, category)
            if same_folder_only:
                key = (dirpath, *key)

            buckets[key].append(FileInfo(path, size))

    groups = []
    for key, files in buckets.items():
        if len(files) > 1:
            stem, category = key[-2], key[-1]
            groups.append(DuplicateGroup(stem, category, sorted(files, key=lambda f: str(f.path))))

    groups.sort(key=lambda g: g.name)
    return groups

##### Manual test #####
if __name__ == '__main__':
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    for group in find_duplicates(folder):
        print(f"\n[{group.category}] {group.name}")
        for f in group.files:
            print(f"    {f.size:10,} B  {f.path}")