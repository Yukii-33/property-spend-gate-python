from property_spend_service import (
    InfraiClient,
    InspectionReminder,
    MaintenanceRequest,
    PropertyWorkload,
    TenantDocument,
    configure_migration,
    decide_spend,
)


def main() -> None:
    workload = PropertyWorkload(
        maintenance=(MaintenanceRequest("m-104", "building-7", "leaking kitchen tap"),),
        tenant_documents=(TenantDocument("doc-22", "tenant-8", "lease"),),
        inspections=(InspectionReminder("i-19", "building-7", "2026-11-03"),),
        estimated_usd=4.50,
    )
    decision = decide_spend(workload, monthly_cap_usd=10.00)
    print({"allowed": decision.allowed, "reason": decision.reason, "estimated_usd": workload.estimated_usd})
    if decision.allowed:
        client = InfraiClient()
        configure_migration(client, monthly_cap_usd=10.00)
        print("Infrai monthly budget configured for the same key used by the workload call.")


if __name__ == "__main__":
    main()
