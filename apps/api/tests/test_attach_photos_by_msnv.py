from pathlib import Path

from app.scripts.attach_photos_by_msnv import _iter_photos


def test_iter_photos_by_msnv_skips_tiny_and_nested(tmp_path: Path):
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "5290.jpg").write_bytes(b"x" * 600)
    (photos / "tiny.jpg").write_bytes(b"no")
    (tmp_path / "1514.jpg").write_bytes(b"y" * 600)
    names = {p.stem for p in _iter_photos(tmp_path)}
    assert names == {"5290", "1514"}
