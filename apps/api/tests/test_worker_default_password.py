"""Mật khẩu mặc định worker: 4 số cuối CCCD, không có thì 4 số cuối MSNV."""

from app.modules.worker.service import default_password_from_cccd


def test_default_password_uses_last4_cccd():
    assert default_password_from_cccd("079123456789", "5290") == "6789"
    assert default_password_from_cccd("079-123-456-321", "1514") == "6321"


def test_default_password_falls_back_to_msnv_when_no_cccd():
    assert default_password_from_cccd(None, "5290") == "5290"
    assert default_password_from_cccd("", "1514") == "1514"
    assert default_password_from_cccd("12", "1732") == "1732"


def test_default_password_pads_short_msnv():
    assert default_password_from_cccd(None, "99") == "0099"
    assert default_password_from_cccd(None, "AB12C3") == "0123"
