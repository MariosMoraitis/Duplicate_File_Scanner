from pathlib import Path
from send2trash import send2trash

def delete_files(paths: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:

    deleted: list[Path] = []
    failed: list[tuple[Path, str]] = []

    for path in paths:
        try:
            send2trash(str(path))
            deleted.append(path)
        except Exception as e:
            failed.append((path, str(e)))

    return deleted, failed