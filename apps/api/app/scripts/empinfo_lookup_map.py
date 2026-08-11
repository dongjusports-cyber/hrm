"""Ánh xạ text Excel → mã lookup_values (birth_place / id_issue_place / education / nationality)."""

from __future__ import annotations

import re
import unicodedata

from app.modules.mdm.lookup_seed import (
    ADMIN_UNITS_34,
    EDUCATION_LEVEL,
    ID_ISSUE_PLACE,
    ID_ISSUE_PLACE_EXTRA,
    NATIONALITY,
)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())


def _fold(s: str) -> str:
    """So khớp không dấu, chữ thường — tránh lệch encoding DB."""
    t = _nfc(s).lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return t


# Tên tỉnh cũ / viết tắt thường gặp trong file GenusSuite → tên chuẩn 34 đơn vị.
_PLACE_ALIASES: dict[str, str] = {
    "ho chi minh": "Thành phố Hồ Chí Minh",
    "tp ho chi minh": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "tphcm": "Thành phố Hồ Chí Minh",
    "hcm": "Thành phố Hồ Chí Minh",
    "sai gon": "Thành phố Hồ Chí Minh",
    "saigon": "Thành phố Hồ Chí Minh",
    "ha noi": "Hà Nội",
    "hn": "Hà Nội",
    "da nang": "Đà Nẵng",
    "can tho": "Cần Thơ",
    "hai phong": "Hải Phòng",
    "hue": "Huế",
    "dak lak": "Đắk Lắk",
    "daklak": "Đắk Lắk",
    "lam dong": "Lâm Đồng",
    "dong nai": "Đồng Nai",
    "tay ninh": "Tây Ninh",
    "tinh tay ninh": "Tây Ninh",
    "binh duong": "Đồng Nai",  # sau sáp nhập 2025 — map gần đúng theo danh sách 34
    "ba ria vung tau": "Đồng Nai",
    "vung tau": "Đồng Nai",
    "long an": "Tây Ninh",
    "cuc canh sat qlhcv ttxh": ID_ISSUE_PLACE_EXTRA,
    "cuc canh sat": ID_ISSUE_PLACE_EXTRA,
}


def resolve_place_code(group: str, raw: str | None) -> str | None:
    """group = birth_place | id_issue_place. Trả mã BIRTH_PLACE030… hoặc None."""
    if not raw:
        return None
    text = _nfc(str(raw))
    if not text or text.lower() in ("none", "null", "-", "."):
        return None

    names = ADMIN_UNITS_34 if group == "birth_place" else ID_ISSUE_PLACE
    prefix = "BIRTH_PLACE" if group == "birth_place" else "ID_ISSUE_PLACE"

    folded = _fold(text)
    alias_target = _PLACE_ALIASES.get(folded)
    if alias_target:
        text = alias_target
        folded = _fold(text)

    for i, name in enumerate(names):
        if _fold(name) == folded or _nfc(name).lower() == text.lower():
            return f"{prefix}{i + 1:03d}"
        # chứa tên tỉnh trong chuỗi dài hơn
        if folded and _fold(name) in folded:
            return f"{prefix}{i + 1:03d}"
    return None


def resolve_education_code(raw) -> str | None:
    """Excel English/số → EDUCATION_LEVELxxx (khớp dropdown UI)."""
    if raw in ("", None):
        return None
    t = _nfc(str(raw)).lower().replace("\xa0", " ").strip()
    if not t:
        return None

    # Ưu tiên khớp theo keyword Excel GenusSuite
    if "university" in t or "đại học" in t or "dai hoc" in _fold(t):
        idx = EDUCATION_LEVEL.index("Đại học")
    elif "college" in t or "cao đẳng" in t or "cao dang" in _fold(t):
        idx = EDUCATION_LEVEL.index("Cao đẳng")
    elif "intermediate" in t or "2 years" in t or "trung cấp" in t or "trung cap" in _fold(t):
        idx = EDUCATION_LEVEL.index("Trung cấp")
    elif "12/12" in t or t.endswith("12") or "phổ thông" in t or "pho thong" in _fold(t):
        idx = EDUCATION_LEVEL.index("Trung học phổ thông")
    elif "9/12" in t:
        idx = EDUCATION_LEVEL.index("Trung học cơ sở")
    elif "under 9" in t or "tiểu học" in t:
        idx = EDUCATION_LEVEL.index("Tiểu học")
    elif t in ("univ", "tc2", "12", "9", "lt9"):
        legacy = {
            "univ": "Đại học",
            "tc2": "Trung cấp",
            "12": "Trung học phổ thông",
            "9": "Trung học cơ sở",
            "lt9": "Tiểu học",
        }
        idx = EDUCATION_LEVEL.index(legacy[t])
    else:
        return None
    return f"EDUCATION_LEVEL{idx + 1:03d}"


def resolve_nationality_code(raw: str | None = None) -> str | None:
    """Mặc định Việt Nam nếu không có nguồn khác."""
    if raw:
        folded = _fold(raw)
        for i, name in enumerate(NATIONALITY):
            if _fold(name) == folded:
                return f"NATIONALITY{i + 1:03d}"
        if folded in ("vie", "vietnam", "vn", "viet nam"):
            return "NATIONALITY001"
    return "NATIONALITY001"


def infer_contract_type(contract_no: str | None) -> str | None:
    """'1514/VTH' → VTH; 'xxxx/HD1' → HD1."""
    if not contract_no:
        return None
    t = _nfc(contract_no).upper()
    m = re.search(r"/(VTH|HD1|HD2|TV|HĐ1|HĐ2)\b", t.replace("Đ", "D"))
    if not m:
        m = re.search(r"/(VTH|HD1|HD2|TV)\b", t)
    if not m:
        return None
    code = m.group(1).replace("HĐ", "HD")
    if code in ("HD1", "HD2", "VTH", "TV"):
        return code
    return None
