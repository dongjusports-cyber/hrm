"""
AI provider tách rời nghiệp vụ (quyết định #11 / 05§5.2).
Đổi model/API Gemini không sửa module dispute/payroll.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

_HTTP_CLIENT: httpx.Client | None = None


def _http_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(timeout=30.0)
    return _HTTP_CLIENT


@dataclass
class ProviderResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    model_name: str = ""
    stub: bool = False


SYSTEM_PROMPT_BASE = (
    "Bạn là Trợ Lý AI — trợ lý HRM nhà máy DONGJU. "
    "Luôn trả lời 100% tiếng Việt; chỉ giữ mã MSNV, mã kỳ (YYYY-MM) và tên riêng. "
    "CHỈ ĐỌC: không được tự sửa lương, không đổi chính sách, không xác nhận/từ chối khiếu nại, "
    "không xóa dữ liệu. Chỉ phân tích và đề xuất; nếu cần sửa số liệu thì bảo người dùng liên hệ HR/Admin. "
    "Không bịa số — thiếu dữ liệu thì nói rõ thiếu. "
    "Khi payload có khối «Dữ liệu nhân viên» hoặc «khiếu nại» từ hệ thống, hãy dùng đúng số đó để trả lời."
)


def generate_text(
    *,
    api_key: str,
    model_name: str,
    system: str,
    user_message: str,
    max_output_tokens: int = 1024,
) -> ProviderResult:
    """Gọi Gemini generateContent; stub khi key trống hoặc DJHRM_AI_STUB=1."""
    use_stub = os.environ.get("DJHRM_AI_STUB", "").strip() in ("1", "true", "yes")
    if use_stub or not api_key.strip():
        return _stub_result(model_name, user_message)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "temperature": 0.3,
        },
    }
    res = _http_client().post(url, params={"key": api_key}, json=payload)
    if res.status_code >= 400:
        detail = res.text[:500]
        raise RuntimeError(f"Gemini API lỗi {res.status_code}: {detail}")
    data = res.json()

    text = _extract_text(data)
    usage = data.get("usageMetadata") or {}
    return ProviderResult(
        text=text or "Trợ Lý AI: mô hình không trả nội dung.",
        tokens_in=int(usage.get("promptTokenCount") or 0),
        tokens_out=int(usage.get("candidatesTokenCount") or 0),
        model_name=model_name,
        stub=False,
    )


def resolve_api_key(db_encrypted: str | None) -> str:
    """Ưu tiên key Admin lưu DB; fallback biến môi trường GEMINI_API_KEY."""
    if db_encrypted:
        from app.modules.ai.crypto_key import decrypt_secret

        plain = decrypt_secret(db_encrypted)
        if plain:
            return plain
    return (get_settings().gemini_api_key or "").strip()


def _extract_text(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _stub_result(model_name: str, user_message: str) -> ProviderResult:
    snippet = user_message.strip().replace("\n", " ")[:180]
    text = (
        "Trợ Lý AI (chế độ giả lập — chưa gọi Gemini thật):\n"
        f"- Đã nhận câu hỏi: {snippet or '(trống)'}\n"
        "- Đây là phân tích giả lập chỉ đọc: đối chiếu công/OT/phụ cấp trên ảnh chụp phiếu; "
        "không tự sửa số liệu.\n"
        "- Đề xuất: HR kiểm tra chấm công Mitapro / bảng công tay, rồi quyết định đóng hoặc "
        "phát hành lại phiếu sau khi chỉnh.\n"
        "- Để bật Gemini thật: Admin dán khóa API tại Cấu Hình → AI Gemini, "
        "hoặc cấu hình biến môi trường GEMINI_API_KEY."
    )
    return ProviderResult(
        text=text,
        tokens_in=0,
        tokens_out=0,
        model_name=model_name or "stub",
        stub=True,
    )
