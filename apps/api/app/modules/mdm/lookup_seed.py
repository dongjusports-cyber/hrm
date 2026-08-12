"""Dữ liệu seed cho `lookup_values` (21§21.4, hạng mục 2.1) — danh mục phẳng, không quy tắc.

Chủ chốt 2026-08-11: 34 đơn vị hành chính sau sáp nhập (6 thành phố trực thuộc TW + 28 tỉnh).
HR sửa/thêm qua Admin › Danh mục (2.8) nếu cần.
"""

from __future__ import annotations

# (group_code, code, name)  — sort_order = thứ tự xuất hiện trong danh sách, is_active=True.

ETHNICITY = [
    "Kinh", "Tày", "Thái", "Mường", "Khơ-me", "Hoa", "Nùng", "H'Mông", "Dao", "Gia-rai",
    "Ê-đê", "Ba-na", "Xơ-đăng", "Sán Chay", "Cơ-ho", "Chăm", "Sán Dìu", "Hrê", "Mnông",
    "Ra-glai", "Xtiêng", "Bru-Vân Kiều", "Thổ", "Giáy", "Cơ-tu", "Gié-triêng", "Mạ",
    "Khơ-mú", "Co", "Tà-ôi", "Chơ-ro", "Kháng", "Xinh-mun", "Hà Nhì", "Chu-ru", "Lào",
    "La Chí", "Phù Lá", "La Hủ", "La Ha", "Pà Thẻn", "Lự", "Ngái", "Chứt", "Lô Lô",
    "Mảng", "Cơ Lao", "Bố Y", "Cống", "Si La", "Pu Péo", "Rơ Măm", "Brâu", "Ơ Đu",
]

RELIGION = [
    "Không",
    "Phật giáo",
    "Công giáo",
    "Tin Lành",
    "Cao Đài",
    "Phật giáo Hòa Hảo",
    "Hồi giáo",
    "Bà-la-môn",
    "Tịnh độ Cư sĩ Phật hội",
    "Khác",
]

NATIONALITY = [
    "Việt Nam", "Trung Quốc", "Hàn Quốc", "Nhật Bản", "Đài Loan", "Hoa Kỳ", "Pháp",
    "Anh", "Đức", "Nga", "Lào", "Campuchia", "Thái Lan", "Singapore", "Malaysia",
    "Indonesia", "Philippines", "Ấn Độ", "Úc", "Canada", "Khác",
]

EDUCATION_LEVEL = [
    "Chưa qua đào tạo",
    "Tiểu học",
    "Trung học cơ sở",
    "Trung học phổ thông",
    "Sơ cấp nghề",
    "Trung cấp",
    "Cao đẳng",
    "Đại học",
    "Sau đại học",
]

# Mã code lưu vào employees.marital_status (§23.3 — không gõ tự do).
MARITAL_STATUS: list[tuple[str, str]] = [
    ("single", "Độc thân"),
    ("married", "Đã kết hôn"),
    ("divorced", "Ly hôn / ly thân"),
    ("widowed", "Góa"),
]

# 6 thành phố trực thuộc Trung ương + 28 tỉnh — Chủ chốt 2026-08-11.
# Ghi chú: Đồng Nai dự kiến lên TP trực thuộc TW từ 30/4/2026; danh sách giữ trong 28 tỉnh
# theo bản Chủ gửi (tổng 34 đơn vị).
ADMIN_UNITS_34 = [
    # Thành phố trực thuộc Trung ương
    "Hà Nội",
    "Hải Phòng",
    "Huế",
    "Đà Nẵng",
    "Cần Thơ",
    "Thành phố Hồ Chí Minh",
    # Tỉnh
    "Lai Châu",
    "Điện Biên",
    "Sơn La",
    "Lạng Sơn",
    "Cao Bằng",
    "Tuyên Quang",
    "Lào Cai",
    "Thái Nguyên",
    "Phú Thọ",
    "Bắc Ninh",
    "Hưng Yên",
    "Ninh Bình",
    "Quảng Ninh",
    "Thanh Hóa",
    "Nghệ An",
    "Hà Tĩnh",
    "Quảng Trị",
    "Quảng Ngãi",
    "Gia Lai",
    "Khánh Hòa",
    "Lâm Đồng",
    "Đắk Lắk",
    "Đồng Nai",
    "Tây Ninh",
    "Vĩnh Long",
    "Đồng Tháp",
    "Cà Mau",
    "An Giang",
]

ID_ISSUE_PLACE_EXTRA = "Cục Cảnh sát QLHC về TTXH"
ID_ISSUE_PLACE = [*ADMIN_UNITS_34, ID_ISSUE_PLACE_EXTRA]


def _rows(group_code: str, names: list[str]) -> list[tuple[str, str, str, int]]:
    """(group_code, code, name, sort_order) — code theo thứ tự danh sách."""
    return [(group_code, f"{group_code.upper()}{i + 1:03d}", name, i) for i, name in enumerate(names)]


def _rows_explicit(group_code: str, pairs: list[tuple[str, str]]) -> list[tuple[str, str, str, int]]:
    return [(group_code, code, name, i) for i, (code, name) in enumerate(pairs)]


LOOKUP_VALUES_SEED: list[tuple[str, str, str, int]] = (
    _rows("ethnicity", ETHNICITY)
    + _rows("religion", RELIGION)
    + _rows("nationality", NATIONALITY)
    + _rows("education_level", EDUCATION_LEVEL)
    + _rows("birth_place", ADMIN_UNITS_34)
    + _rows("id_issue_place", ID_ISSUE_PLACE)
    + _rows_explicit("marital_status", MARITAL_STATUS)
)

ADMIN_UNITS_BIRTH_COUNT = len(ADMIN_UNITS_34)
ADMIN_UNITS_ID_ISSUE_COUNT = len(ID_ISSUE_PLACE)
