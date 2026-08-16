"""QA-09 — ảnh hồ sơ chỉ được lấy trong thư mục upload, không theo path tuyệt đối ngoài."""

from app.modules.mdm import service as mdm_service
from app.modules.mdm.models import Employee


def test_employee_photo_ignores_absolute_path_outside_upload(db, tmp_path, monkeypatch):
    photo_root = tmp_path / "employee_photos"
    photo_root.mkdir()
    secret = tmp_path / "secret.jpg"
    secret.write_bytes(b"secret")
    inside = photo_root / "ok.jpg"
    inside.write_bytes(b"ok")

    monkeypatch.setattr(
        mdm_service,
        "_photo_dir",
        lambda create=True: photo_root,
    )

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.photo_path = str(secret)
    db.commit()
    assert mdm_service._employee_photo_file(emp) is None

    emp.photo_path = "ok.jpg"
    db.commit()
    found = mdm_service._employee_photo_file(emp)
    assert found is not None
    assert found.resolve() == inside.resolve()
