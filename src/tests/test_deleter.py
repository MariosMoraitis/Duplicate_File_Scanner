from pathlib import Path

import pytest

import deleter

@pytest.fixture
def fake_trash(monkeypatch):

    calls: list[str] = []

    def fake_send2trash(path):
        calls.append(path)

    monkeypatch.setattr(deleter, "send2trash", fake_send2trash)
    return calls

def test_every_path_is_sent_to_trash(fake_trash):

    paths = [Path("/x/a.jpg"), Path("/x/b.png")]

    deleter.delete_files(paths)

    assert fake_trash == [str(Path("/x/a.jpg")), str(Path("/x/b.png"))]

def test_success_is_reported(fake_trash):

    paths = [Path("/x/a.jpg"), Path("/x/b.png")]
    deleted, failed = deleter.delete_files(paths)

    assert deleted == paths
    assert failed == []

def test_empty_list(fake_trash):

    deleted, failed = deleter.delete_files([])

    assert deleted == []
    assert failed == []
    assert fake_trash == []

def test_failure_doesnt_stop_rest(monkeypatch):

    def flaky_send2trash(path):
        if path.endswith("locked.jpg"):
            raise PermissionError("file in use")

    monkeypatch.setattr(deleter, "send2trash", flaky_send2trash)

    good1, bad, good2 = Path("/x/a.jpg"), Path("/x/locked.jpg"), Path("/x/c.jpg")
    deleted, failed = deleter.delete_files([good1, bad, good2])

    assert deleted == [good1, good2]
    assert len(failed) == 1
    assert failed[0][0] == bad
    assert "file in use" in failed[0][1]

def test_real_life_is_removed_from_dir(tmp_path, monkeypatch):

    keep = tmp_path / "keep.jpg"
    remove = tmp_path / "remove.png"
    keep.touch()
    remove.touch()

    monkeypatch.setattr(deleter, "send2trash", lambda p: Path(p).unlink())
    deleted, failed = deleter.delete_files([remove])

    assert deleted == [remove]
    assert not remove.exists()
    assert keep.exists()