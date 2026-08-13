"""Đường dẫn «Dữ liệu công nhân» — JSON 1 file / NV (trước đây gọi snapshot)."""

from __future__ import annotations

from pathlib import Path

EMPLOYEE_DATA_FOLDER = "Dữ liệu công nhân"
LEGACY_SNAPSHOT_SUBPATH = Path("_SNAPSHOTS") / "nhan-vien"


def default_employee_data_dir(hien_phap: Path) -> Path:
    return hien_phap / EMPLOYEE_DATA_FOLDER


def resolve_hien_phap(data_dir: Path) -> Path:
    """Suy ra thư mục HIEN_PHAP từ thư mục dữ liệu công nhân."""
    resolved = data_dir.resolve()
    if resolved.name == "nhan-vien" and resolved.parent.name == "_SNAPSHOTS":
        return resolved.parent.parent
    return resolved.parent


def import_command(hien_phap: Path | None = None) -> str:
    root = (hien_phap or Path("HIEN_PHAP")).resolve()
    rel = Path("HIEN_PHAP") / EMPLOYEE_DATA_FOLDER
    try:
        rel = default_employee_data_dir(root).relative_to(root.parent)
    except ValueError:
        rel = Path("HIEN_PHAP") / EMPLOYEE_DATA_FOLDER
    return f"python -m app.scripts.import_employee_snapshots {rel.as_posix()}"
