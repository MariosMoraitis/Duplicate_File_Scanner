import os
import sys
from pathlib import Path

import pytest

from scanner import category_of, find_duplicates

def make_files(base:Path, *relative_path:str):

    for rel in relative_path:
        file_path = base / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

def names(group) -> list[str]:
    return sorted(f.path.name for f in group.files)

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

def test_jpg_and_png_share_category():
    assert category_of(".jpg") == category_of(".png")

def test_mp4_and_srt_dont_share_category():
    assert category_of(".mp4") != category_of(".srt")

def test_jpg_and_png_with_same_name_flagged(tmp_path):

    make_files(tmp_path, "photo_1.jpg", "photo_1.png")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert groups[0].name == "photo_1"
    assert groups[0].category == "image"
    assert names(groups[0]) == ["photo_1.jpg", "photo_1.png"]

def test_video_and_subs_are_not_flagged(tmp_path):

    make_files(tmp_path, "movie.mp4", "movie.srt")
    assert find_duplicates(tmp_path) == []

def test_matching_case_insensitive(tmp_path):

    make_files(tmp_path, "Photo_1.jpg", "photo_1.png")
    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert names(groups[0]) == ["Photo_1.jpg", "photo_1.png"]

def test_single_file_isnt_duplicate(tmp_path):

    make_files(tmp_path, "lonely.png")
    assert find_duplicates(tmp_path) == []

def test_empty_folder(tmp_path):
    assert find_duplicates(tmp_path) == []

def test_different_names_same_category(tmp_path):

    make_files(tmp_path, "cat.jpg", "dog.jpg")
    assert find_duplicates(tmp_path) == []

def test_threeway_match_is_one_group(tmp_path):

    make_files(tmp_path, 'pic.jpg', 'pic.png', 'pic.gif')
    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert len(groups[0].files) == 3

def test_same_name_different_category(tmp_path):

    make_files(tmp_path, "song.mp3", "song.jpg")
    assert find_duplicates(tmp_path) == []

def test_multiple_independent_groups(tmp_path):

    make_files(tmp_path, "a.jpg", "a.png", "b.mp4", "b.mkv", "c.txt")
    groups = find_duplicates(tmp_path)
    assert [g.name for g in groups] == ['a', 'b']

def test_files_no_extension(tmp_path):

    make_files(tmp_path, "x/Readme", "y/Readme", "z/Readme.md")
    groups = find_duplicates(tmp_path)

    assert len(groups) == 1
    assert groups[0].name == 'readme'
    assert groups[0].category == "other:"

def test_scan_recurses_subfolders(tmp_path):

    make_files(tmp_path, "deep/er/still/photo.jpg", "photo.png")
    groups = find_duplicates(tmp_path)
    assert len(groups) == 1

def test_across_folders_is_default(tmp_path):

    make_files(tmp_path, "a/photo_1.jpg","b/photo_1.png")
    assert len(find_duplicates(tmp_path)) == 1

def test_same_folder_only_ignores_matches_in_other_folders(tmp_path):

    make_files(tmp_path, "a/photo.jpg", "b/photo.png")
    assert find_duplicates(tmp_path, same_folder_only=True) == []

def test_same_folder_only_works(tmp_path):

    make_files(tmp_path, "a/photo.jpg", "a/photo.png", "b/photo.png")
    groups = find_duplicates(tmp_path, same_folder_only=True)

    assert len(groups) == 1
    assert all(f.path.parent.name == 'a' for f in groups[0].files)

def test_file_sizes_are_recorded(tmp_path):

    (tmp_path / "pic.jpg").write_bytes(b'x' * 100)
    (tmp_path / "pic.png").write_bytes(b'y' * 2500)

    group = find_duplicates(tmp_path)[0]
    sizes = {f.path.name: f.size for f in group.files}

    assert sizes == {'pic.png': 2500, 'pic.jpg': 100}

def test_paths_are_real(tmp_path):

    make_files(tmp_path, 'pic.jpg', 'pic.png')
    group = find_duplicates(tmp_path)[0]
    assert all(isinstance(f.path, Path) and f.path.exists() for f in group.files)

def test_accept_string_paths(tmp_path):

    make_files(tmp_path, "pic.jpg", "pic.png")
    assert len(find_duplicates(str(tmp_path))) == 1

@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need admin rights")
def test_broken_symlink(tmp_path):

    make_files(tmp_path, 'pic.png', 'pic.jpg')
    os.symlink(tmp_path / "does_not_exist", tmp_path / "pic.gif") # points at nothing

    groups = find_duplicates(tmp_path)
    assert len(groups) == 1
    assert names(groups[0]) == ['pic.jpg', 'pic.png']