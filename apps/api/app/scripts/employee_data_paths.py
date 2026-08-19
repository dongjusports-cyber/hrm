"""Đường dẫn hồ sơ NV — thư mục gốc `Dữ liệu nhân viên/` (không phải luật)."""

from __future__ import annotations

from pathlib import Path

DATA_ROOT_NAME = "Dữ liệu nhân viên"
SNAPSHOT_FOLDER = "Dữ liệu công nhân"
SALARY_FOLDER = "Salary"
LEGACY_SNAPSHOT_SUBPATH = Path("_SNAPSHOTS") / "nhan-vien"


def repo_root() -> Path:
    start = Path(__file__).resolve()
    for anc in start.parents:
        if (anc / "docker-compose.yml").is_file() or (anc / DATA_ROOT_NAME).is_dir():
            return anc
    return start.parents[4]


def employee_data_root() -> Path:
    return repo_root() / DATA_ROOT_NAME


def snapshot_dir() -> Path:
    return employee_data_root() / SNAPSHOT_FOLDER


def salary_dir() -> Path:
    return employee_data_root() / SALARY_FOLDER


def cong_dir() -> Path | None:
    p = employee_data_root() / "Công"
    return p if p.is_dir() else None


def genus_suite_dir() -> Path:
    return employee_data_root() / "GenuSuite HRM"


def annual_leave_source_dir() -> Path:
    return employee_data_root() / "Phép năm GenuSuite"


def find_empinfo_dir() -> Path | None:
    """Excel hồ sơ + trich_xuat + ảnh (`Thông tin danh sách nhân viên`)."""
    root = employee_data_root()
    if not root.is_dir():
        return None
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name.casefold()
        if "danh sách" in name or "danh sach" in name:
            return child
    return None


def default_employee_data_dir(_ignored: Path | None = None) -> Path:
    """Snapshot JSON 1 file / NV."""
    return snapshot_dir()


def resolve_hien_phap(data_dir: Path) -> Path:
    """Giữ tên cũ cho caller: trả về thư mục chứa snapshot + hồ sơ Excel."""
    return resolve_data_root(data_dir)


def resolve_data_root(data_dir: Path) -> Path:
    resolved = data_dir.resolve()
    if resolved.name == "nhan-vien" and resolved.parent.name == "_SNAPSHOTS":
        return resolved.parent.parent
    if resolved.name == SNAPSHOT_FOLDER:
        return resolved.parent
    return resolved.parent


def import_command(_ignored: Path | None = None) -> str:
    rel = Path(DATA_ROOT_NAME) / SNAPSHOT_FOLDER
    return f"python -m app.scripts.import_employee_snapshots \"{rel.as_posix()}\""
