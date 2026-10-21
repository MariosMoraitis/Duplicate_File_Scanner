"""
Tests for scanner.py

How pytest works, in short:
  * Files named test_*.py are collected; functions named test_* are run.
  * A test passes if it finishes without an exception. `assert` raises
    one when its condition is False, which is how tests "fail".
  * Arguments in a test function's signature are *fixtures*: pytest sees
    the name and supplies the value. `tmp_path` is a built-in fixture that
    gives each test its own fresh, empty temporary folder (auto-cleaned).

Run from the project folder with:   pytest -v
"""

import os
import sys
from pathlib import Path

import pytest

from scanner import category_of, find_duplicates


# ---------------------------------------------------------------------------
# Helpers (plain functions, not tests - they don't start with test_)
# ---------------------------------------------------------------------------

def make_files(base: Path, *relative_paths: str) -> None:
    """Create empty files under `base`, making subfolders as needed.

    make_files(tmp_path, "a/photo.jpg", "b/photo.png")
    """
    for rel in relative_paths:
        file_path = base / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()


def names(group) -> list[str]:
    """Just the filenames in a group, sorted, so assertions are easy to read."""
    return sorted(f.path.name for f in group.files)


# ---------------------------------------------------------------------------
# category_of  (a pure function: input -> output, the easiest thing to test)
# ---------------------------------------------------------------------------

# parametrize runs the SAME test once per row. Each row shows up as its own
# result in the report, so you can see exactly which case failed.
@pytest.mark.parametrize(
    "extension, expected",
    [
        (".jpg", "image"),
        (".jpeg", "image"),
        (".png", "image"),
        (".mp4", "video"),
        (".mp3", "audio"),
        (".pdf", "document"),
        (".srt", "other:.srt"),   # unknown -> its own category
        ("", "other:"),           # no extension at all
    ],
)
def test_category_of(extension, expected):
    assert category_of(extension) == expected


def test_jpg_and_png_share_a_category():
    # The whole point of the project, stated as a test.
    assert category_of(".jpg") == category_of(".png")


def test_mp4_and_srt_do_not_share_a_category():
    assert category_of(".mp4") != category_of(".srt")


# ---------------------------------------------------------------------------
# find_duplicates - the behaviours you asked for
# ---------------------------------------------------------------------------

def test_jpg_and_png_with_same_name_are_flagged(tmp_path):
    make_files(tmp_path, "photo_1.jpg", "photo_1.png")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert groups[0].name == "photo_1"
    assert groups[0].category == "image"
    assert names(groups[0]) == ["photo_1.jpg", "photo_1.png"]


def test_video_and_subtitle_are_not_flagged(tmp_path):
    make_files(tmp_path, "movie.mp4", "movie.srt")

    assert find_duplicates(tmp_path) == []


def test_matching_is_case_insensitive(tmp_path):
    make_files(tmp_path, "Photo_1.JPG", "photo_1.png")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert names(groups[0]) == ["Photo_1.JPG", "photo_1.png"]  # original names preserved


def test_single_file_is_not_a_duplicate(tmp_path):
    make_files(tmp_path, "lonely.jpg")

    assert find_duplicates(tmp_path) == []


def test_empty_folder_returns_empty_list(tmp_path):
    assert find_duplicates(tmp_path) == []


def test_different_names_same_category_are_not_flagged(tmp_path):
    make_files(tmp_path, "cat.jpg", "dog.png")

    assert find_duplicates(tmp_path) == []


def test_three_way_match_is_one_group(tmp_path):
    make_files(tmp_path, "pic.jpg", "pic.png", "pic.gif")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert len(groups[0].files) == 3


def test_same_name_in_different_categories_makes_no_group(tmp_path):
    # "song.mp3" and "song.jpg" share a stem but are different kinds of file.
    make_files(tmp_path, "song.mp3", "song.jpg")

    assert find_duplicates(tmp_path) == []


def test_multiple_independent_groups(tmp_path):
    make_files(tmp_path, "a.jpg", "a.png", "b.mp4", "b.mkv", "c.txt")

    groups = find_duplicates(tmp_path)

    assert [g.name for g in groups] == ["a", "b"]  # sorted by name; c is alone


def test_files_without_extensions(tmp_path):
    # Two extensionless files collide only if they share a name (needs two
    # folders since one folder can't hold two identically named files).
    make_files(tmp_path, "x/README", "y/README", "z/README.md")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert groups[0].name == "readme"
    assert groups[0].category == "other:"


# ---------------------------------------------------------------------------
# Folder handling: recursion and the same_folder_only option
# ---------------------------------------------------------------------------

def test_scan_recurses_into_subfolders(tmp_path):
    make_files(tmp_path, "deep/er/still/photo.jpg", "photo.png")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1


def test_across_folders_is_the_default(tmp_path):
    make_files(tmp_path, "a/photo_1.jpg", "b/photo_1.png")

    assert len(find_duplicates(tmp_path)) == 1


def test_same_folder_only_ignores_matches_in_other_folders(tmp_path):
    make_files(tmp_path, "a/photo_1.jpg", "b/photo_1.png")

    assert find_duplicates(tmp_path, same_folder_only=True) == []


def test_same_folder_only_still_finds_matches_within_a_folder(tmp_path):
    make_files(tmp_path, "a/photo_1.jpg", "a/photo_1.png", "b/photo_1.jpg")

    groups = find_duplicates(tmp_path, same_folder_only=True)

    assert len(groups) == 1
    # b/photo_1.jpg must NOT have been pulled into a/'s group
    assert all(f.path.parent.name == "a" for f in groups[0].files)


# ---------------------------------------------------------------------------
# Data returned
# ---------------------------------------------------------------------------

def test_file_sizes_are_recorded(tmp_path):
    (tmp_path / "pic.jpg").write_bytes(b"x" * 100)
    (tmp_path / "pic.png").write_bytes(b"y" * 2500)

    group = find_duplicates(tmp_path)[0]
    sizes = {f.path.name: f.size for f in group.files}

    assert sizes == {"pic.jpg": 100, "pic.png": 2500}


def test_paths_are_real_paths_that_exist(tmp_path):
    make_files(tmp_path, "pic.jpg", "pic.png")

    group = find_duplicates(tmp_path)[0]

    assert all(isinstance(f.path, Path) and f.path.exists() for f in group.files)


def test_accepts_string_paths_too(tmp_path):
    # The GUI passes a str from the folder dialog, not a Path.
    make_files(tmp_path, "pic.jpg", "pic.png")

    assert len(find_duplicates(str(tmp_path))) == 1


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need admin rights on Windows")
def test_broken_symlink_does_not_crash_the_scan(tmp_path):
    make_files(tmp_path, "pic.jpg", "pic.png")
    os.symlink(tmp_path / "does_not_exist", tmp_path / "pic.gif")  # points at nothing

    groups = find_duplicates(tmp_path)

    # The scan survived, and the unreadable link was skipped, not included.
    assert len(groups) == 1
    assert names(groups[0]) == ["pic.jpg", "pic.png"]


# ---------------------------------------------------------------------------
# Multiple root folders
# ---------------------------------------------------------------------------
# find_duplicates should accept a LIST of folders, so you can compare
# separate locations (Downloads vs Pictures) that don't share a parent.

def test_two_separate_folders_are_compared_with_each_other(tmp_path):
    make_files(tmp_path, "downloads/photo_1.jpg", "pictures/photo_1.png")

    # Scanning either folder alone finds nothing...
    assert find_duplicates(tmp_path / "downloads") == []
    assert find_duplicates(tmp_path / "pictures") == []

    # ...but scanning both together finds the pair.
    groups = find_duplicates([tmp_path / "downloads", tmp_path / "pictures"])
    assert len(groups) == 1
    assert names(groups[0]) == ["photo_1.jpg", "photo_1.png"]


def test_same_folder_only_applies_across_multiple_roots(tmp_path):
    make_files(tmp_path, "a/photo_1.jpg", "b/photo_1.png")

    groups = find_duplicates([tmp_path / "a", tmp_path / "b"], same_folder_only=True)

    assert groups == []


def test_same_root_given_twice_is_not_counted_twice(tmp_path):
    make_files(tmp_path, "a/only.jpg")

    # If the folder were scanned twice, only.jpg would "duplicate" itself.
    assert find_duplicates([tmp_path / "a", tmp_path / "a"]) == []


def test_nested_roots_do_not_double_count(tmp_path):
    # The user picks a folder AND one of its subfolders.
    make_files(tmp_path, "a/pic.png", "a/sub/pic.jpg")

    groups = find_duplicates([tmp_path / "a", tmp_path / "a" / "sub"])

    assert len(groups) == 1
    assert names(groups[0]) == ["pic.jpg", "pic.png"]   # exactly 2 files, not 3


def test_nested_roots_with_no_real_duplicate_find_nothing(tmp_path):
    make_files(tmp_path, "a/sub/solo.jpg")

    assert find_duplicates([tmp_path / "a", tmp_path / "a" / "sub"]) == []


def test_empty_list_of_roots_returns_nothing():
    assert find_duplicates([]) == []


def test_missing_folder_is_skipped_not_fatal(tmp_path):
    make_files(tmp_path, "real/pic.jpg", "real/pic.png")

    groups = find_duplicates([tmp_path / "does_not_exist", tmp_path / "real"])

    assert len(groups) == 1