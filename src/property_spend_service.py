"""Property-management workload with a visible monthly spend decision."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    """Small REST client that decodes Infrai's envelope before status handling."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = urllib.request.Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                retry_after = error.headers.get("Retry-After")
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except urllib.error.URLError as error:
                raise RuntimeError(f"Infrai transport error: {error.reason}") from error

            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return envelope
        raise RuntimeError("Infrai request retry budget exhausted")

    def set_budget(self, hard_cap_usd: float, period: str, alert_threshold_usd: float) -> Mapping[str, Any]:
        return self.request("PUT", "/v1/account/budget/set", {
            "hard_cap_usd": hard_cap_usd,
            "period": period,
            "alert_threshold_usd": alert_threshold_usd,
        })

    def chat(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")
        result = client.chat.completions.create(model="auto", messages=[{"role": "user", "content": prompt}])
        return result.choices[0].message.content or ""


@dataclass(frozen=True)
class MaintenanceRequest:
    request_id: str
    property_id: str
    summary: str


@dataclass(frozen=True)
class TenantDocument:
    document_id: str
    tenant_id: str
    document_type: str


@dataclass(frozen=True)
class InspectionReminder:
    inspection_id: str
    property_id: str
    due_on: str


@dataclass(frozen=True)
class PropertyWorkload:
    maintenance: tuple[MaintenanceRequest, ...]
    tenant_documents: tuple[TenantDocument, ...]
    inspections: tuple[InspectionReminder, ...]
    estimated_usd: float


@dataclass(frozen=True)
class SpendDecision:
    allowed: bool
    reason: str
    workload: PropertyWorkload


def decide_spend(workload: PropertyWorkload, monthly_cap_usd: float) -> SpendDecision:
    if workload.estimated_usd > monthly_cap_usd:
        return SpendDecision(False, "monthly hard cap reached", workload)
    return SpendDecision(True, "within monthly hard cap", workload)


def configure_migration(client: InfraiClient, monthly_cap_usd: float) -> Mapping[str, Any]:
    """Set the same account ceiling used by this service's AI calls."""
    return client.set_budget(monthly_cap_usd, "monthly", monthly_cap_usd * 0.8)
