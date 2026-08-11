"""Đẩy punch lên DJ HRM API (chỉ push — không nhận lệnh phá DB)."""

from __future__ import annotations

from typing import Any

import httpx

from dj_agent.sql_reader import PunchRow


class ApiPusher:
    def __init__(self, base_url: str, agent_token: str, agent_name: str = "dj-agent") -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_token = agent_token
        self.agent_name = agent_name

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-Agent-Token": self.agent_token,
            "Content-Type": "application/json",
        }

    def push_punches(
        self,
        punches: list[PunchRow],
        *,
        synced_from: str | None = None,
        synced_to: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "punches": [p.to_api_dict() for p in punches],
            "synced_from": synced_from,
            "synced_to": synced_to,
            "agent_name": self.agent_name,
        }
        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                f"{self.base_url}/api/integrations/mitapro/push",
                headers=self._headers,
                json=payload,
            )
            if res.status_code >= 400:
                detail = res.text
                try:
                    detail = res.json().get("detail", detail)
                except Exception:
                    pass
                raise RuntimeError(f"API từ chối push ({res.status_code}): {detail}")
            return res.json()

    def list_pending(self) -> list[dict[str, Any]]:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(
                f"{self.base_url}/api/integrations/mitapro/pending",
                headers=self._headers,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Không lấy pending ({res.status_code}): {res.text}")
            return res.json()

    def claim_pending(self, job_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(
                f"{self.base_url}/api/integrations/mitapro/pending/{job_id}/claim",
                headers=self._headers,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Không claim job ({res.status_code}): {res.text}")
            return res.json()

    def report_error(self, message: str) -> dict[str, Any]:
        """Báo sync lỗi → API tạo AI alert cho Admin (P2.5)."""
        with httpx.Client(timeout=30.0) as client:
            res = client.post(
                f"{self.base_url}/api/integrations/mitapro/error",
                headers=self._headers,
                json={"message": message[:2000], "agent_name": self.agent_name},
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Không gửi báo lỗi ({res.status_code}): {res.text}")
            return res.json()
