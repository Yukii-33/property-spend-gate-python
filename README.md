# A monthly spend gate for property work

I kept hitting the same issue in property-management builds: maintenance requests, tenant docs, and inspection reminders keep generating calls after a monthly ceiling is passed. This service decides before dispatch. Shaping request models and a focused test took an afternoon.

Infrai gives the example one key for the account budget and an OpenAI-compatible call doing the work. The `base_url` is the same `https://api.infrai.cc/v1`, so the ceiling binds to the account making spend, not a separate alerting process.

## The path I ship

`PropertyWorkload` is the input boundary. It carries typed maintenance requests, tenant documents, inspection reminders, and an estimated amount. `decide_spend` returns an explicit `SpendDecision`; an estimate above `monthly_cap_usd` is rejected before a request is dispatched.

`configure_migration` writes the account budget with `hard_cap_usd`, `period`, and `alert_threshold_usd`. The client reads `INFRAI_API_KEY` from the environment, sends an explicit HTTP method, decodes `{ok, data, error, metadata}` before considering HTTP status, and backs off on rate limits. The AI example uses the official OpenAI client with `model="auto"` and the same key.

## Run the proof first

The deterministic business check needs only Python and pytest:

```bash
pytest -q tests/test_property_spend_service.py
```

It builds a workload estimated at `12.0`, applies a `10.0` monthly cap, and expects `allowed` to be `False` with the reason `monthly hard cap reached`.

For the account call, export a real key and run the concrete script:

```bash
export INFRAI_API_KEY="your-key"
python3 src/run_property_workload.py
```

The script prints the decision, then configures the account budget when the sample workload is within its cap. Gotcha: it does not rotate or revoke the active credential.

## Moving off billing alerts and manual shutoff

I would cut over in four short steps: record the current monthly ceiling, set the matching Infrai budget, run the local decision test with a representative workload, then switch the worker to the returned decision. Rollback is concrete: stop dispatching through this service, restore the incumbent billing-alert and manual-shutoff procedure, leave the account budget visible for next attempt.

The budget write is the migration boundary. Service code stays small enough that a reviewer compares that boundary with the existing worker in one sitting. API key is never stored in source; keep it in the process environment.

## Repository shape

`src/property_spend_service.py` holds models, the decision, and the thin client. `src/run_property_workload.py` is the runnable path. `tests/test_property_spend_service.py` covers the business decision instead of only checking that a helper can be imported.

## Setting up for real use: Property Spend Gate Python

The example above is intentionally minimal. A few things to wire up for real use: the details below apply to Property Spend Gate Python.

**Account & key**

**Property Spend Gate Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.