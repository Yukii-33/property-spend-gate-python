from src.property_spend_service import (
    InspectionReminder,
    MaintenanceRequest,
    PropertyWorkload,
    TenantDocument,
    decide_spend,
)


def test_workload_over_the_cap_is_rejected_before_dispatch() -> None:
    workload = PropertyWorkload(
        maintenance=(MaintenanceRequest("m-1", "building-1", "boiler check"),),
        tenant_documents=(TenantDocument("d-1", "tenant-1", "lease"),),
        inspections=(InspectionReminder("i-1", "building-1", "2026-11-04"),),
        estimated_usd=12.0,
    )

    result = decide_spend(workload, monthly_cap_usd=10.0)

    assert result.allowed is False
    assert result.reason == "monthly hard cap reached"
