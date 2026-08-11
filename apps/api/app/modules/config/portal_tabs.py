"""
Seed metadata 8 ô Portal Lv1 (file 02§2.2).
Không hard-code tên trong UI logic — FE đọc từ API.
"""

from typing import Any

MODULE_KEYS: list[str] = [
    "overview",
    "hr",
    "timekeeping",
    "payroll",
    "insurance",
    "report",
    "dispute",
    "config",
]

DEFAULT_PORTAL_TABS: list[dict[str, Any]] = [
    {
        "key": "overview",
        "name": "Tổng Quan",
        "description": "Biểu đồ, cảnh báo nhanh",
        "sort_order": 1,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "hr",
        "name": "Nhân Sự",
        "description": "Hồ sơ, bộ phận, hợp đồng",
        "sort_order": 2,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "timekeeping",
        "name": "Chấm Công",
        "description": "Công, trễ/sớm, đồng bộ máy chấm",
        "sort_order": 3,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "payroll",
        "name": "Tính Lương",
        "description": "Kỳ lương, bảng lương, tính toán",
        "sort_order": 4,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "insurance",
        "name": "Bảo Hiểm Thuế",
        "description": "BHXH, BHYT, BHTN, TNCN",
        "sort_order": 5,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "report",
        "name": "Báo Cáo / KPI",
        "description": "Chuyên cần, OT, nghỉ việc",
        "sort_order": 6,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "dispute",
        "name": "Khiếu Nại",
        "description": "Khiếu nại công nhân, xử lý, AI rà soát",
        "sort_order": 7,
        "enabled": True,
        "admin_only": False,
    },
    {
        "key": "config",
        "name": "Cấu Hình",
        "description": "Policy, người dùng, Agent, AI, nhật ký — chỉ Admin",
        "sort_order": 8,
        "enabled": True,
        "admin_only": True,
    },
]
