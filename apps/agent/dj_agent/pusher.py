"""Đẩy punch lên DJ HRM API (chỉ push — không nhận lệnh phá DB)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from dj_agent.sql_reader import PunchRow

log = logging.getLogger("dj_agent")

_DEFAULT_TIMEOUT = 300.0
_DEFAULT_CHUNK = 800


class ApiPusher:
    def __init__(
        self,
        base_url: str,
        agent_token: str,
        agent_name: str = "dj-agent",
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        push_chunk_size: int = _DEFAULT_CHUNK,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_token = agent_token
        self.agent_name = agent_name
        self.push_chunk_size = max(50, push_chunk_size)
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

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
        claimed_job_id: str | None = None,
    ) -> dict[str, Any]:
        chunk_size = self.push_chunk_size
        if len(punches) <= chunk_size:
            return self._push_chunk(
                punches,
                synced_from=synced_from,
                synced_to=synced_to,
                claimed_job_id=claimed_job_id,
                chunk_final=True,
            )

        total = len(punches)
        chunks = [punches[i : i + chunk_size] for i in range(0, total, chunk_size)]
        log.info(
            "Chia %s punch thành %s chunk (tối đa %s/lần)",
            total,
            len(chunks),
            chunk_size,
        )

        active_job_id = claimed_job_id
        last: dict[str, Any] = {}
        for idx, chunk in enumerate(chunks):
            is_final = idx == len(chunks) - 1
            last = self._push_chunk(
                chunk,
                synced_from=synced_from if is_final else None,
                synced_to=synced_to if is_final else None,
                claimed_job_id=active_job_id,
                chunk_final=is_final,
            )
            if active_job_id is None:
                job = last.get("job") or {}
                jid = job.get("id")
                if jid:
                    active_job_id = str(jid)
            log.info(
                "Chunk %s/%s — %s punch%s",
                idx + 1,
                len(chunks),
                len(chunk),
                " (cuối)" if is_final else "",
            )
        return last

    def _push_chunk(
        self,
        punches: list[PunchRow],
        *,
        synced_from: str | None,
        synced_to: str | None,
        claimed_job_id: str | None,
        chunk_final: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "punches": [p.to_api_dict() for p in punches],
            "synced_from": synced_from,
            "synced_to": synced_to,
            "agent_name": self.agent_name,
            "chunk_final": chunk_final,
        }
        if claimed_job_id:
            payload["claimed_job_id"] = claimed_job_id
        res = self._client.post(
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
        res = self._client.get(
            f"{self.base_url}/api/integrations/mitapro/pending",
            headers=self._headers,
        )
        if res.status_code >= 400:
            raise RuntimeError(f"Không lấy pending ({res.status_code}): {res.text}")
        return res.json()

    def claim_pending(self, job_id: str) -> dict[str, Any]:
        res = self._client.post(
            f"{self.base_url}/api/integrations/mitapro/pending/{job_id}/claim",
            headers=self._headers,
        )
        if res.status_code >= 400:
            raise RuntimeError(f"Không claim job ({res.status_code}): {res.text}")
        return res.json()

    def report_error(self, message: str) -> dict[str, Any]:
        """Báo sync lỗi → API tạo AI alert cho Admin (P2.5)."""
        res = self._client.post(
            f"{self.base_url}/api/integrations/mitapro/error",
            headers=self._headers,
            json={"message": message[:2000], "agent_name": self.agent_name},
        )
        if res.status_code >= 400:
            raise RuntimeError(f"Không gửi báo lỗi ({res.status_code}): {res.text}")
        return res.json()
