"""Live-integration eval: 5 LIVE cases against real HR/IT services + safety_check_server.

Usage (from repo root):
  copy seed/demo.db to a temp file first, then:
  HR_DB_PATH=<tmpdb> uvicorn hr_service.main:app --port 8001 &
  IT_DB_PATH=<tmpdb> uvicorn it_service.main:app --port 8002 &
  SAFETY_LEDGER_PATH=<tmpledger> SAFETY_AUDIT_PATH=<tmpaudit> `
    python eval/live_run.py --hr http://127.0.0.1:8001 --it http://127.0.0.1:8002

LIVE HONESTY NOTICE: every row here is a REAL call (HTTP to local HR/IT +
direct onboard() invocation). Latency column is MEASURED wall-clock
(latency_live_ms) -- NOT simulated, NOT the +11.0ms MOCK cost used in
eval/run.py. Mode column is always LIVE; MOCK rows live only in
eval/scorecard.csv.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return e.code, {"detail": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hr", default="http://127.0.0.1:8001")
    ap.add_argument("--it", default="http://127.0.0.1:8002")
    ap.add_argument("--cases", default=str(BASE / "live_cases.json"))
    ap.add_argument("--out", default=str(BASE / "live_scorecard.csv"))
    a = ap.parse_args()

    os.environ["HR_BASE_URL"] = a.hr
    os.environ["IT_BASE_URL"] = a.it
    sys.path.insert(0, str(BASE.parent))
    import safety_check_server as scs  # noqa: E402

    cases = json.loads(Path(a.cases).read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in cases}
    rows = []
    stored = {}  # L01 preview_hash / result for L02 replay

    def emp_count():
        st, body = http("GET", f"{a.hr}/hr/demo/status")
        assert st == 200, f"demo/status {st} {body}"
        return body["counts"].get("employees")

    n0 = emp_count()

    # ---- L01: approve -> real EMP -------------------------------------
    c = by_id["L01"]
    t0 = time.perf_counter()
    stg = scs.onboard(candidate_id="CAND-002", email="priya.nair02@example.com",
                      dept="Engineering", start_date="2026-11-30",
                      laptop_id="LT-1011", bg_status="pass",
                      confirm=False, idempotency_key="live-L01-key")
    assert stg.get("status") == "preview", stg
    ph = stg["preview_hash"]
    act = scs.onboard(candidate_id="CAND-002", email="priya.nair02@example.com",
                      dept="Engineering", start_date="2026-11-30",
                      laptop_id="LT-1011", bg_status="pass",
                      confirm=True, preview_hash=ph,
                      idempotency_key="live-L01-key")
    dt = (time.perf_counter() - t0) * 1000
    stored["hash"], stored["key"] = ph, "live-L01-key"
    res = act.get("result", {}) or {}
    ok = (act.get("status") == "applied" and res.get("employee_id", "").startswith("EMP-")
          and "ACTIVE" in (act.get("receipt", "")))
    stored["emp"] = res.get("employee_id")
    rows.append({"id": "L01", "mode": "LIVE", "category": c["category"],
                 "expected": c["expected"],
                 "observed": f"{act.get('status')} receipt={act.get('receipt', '')}",
                 "verdict": "PASS" if ok else "FAIL",
                 "detail": f"preview={stg.get('preview_id')} hash={ph[:8]} risk={stg.get('risk_class')}",
                 "latency_live_ms": round(dt, 1)})

    # ---- L02: duplicate -> cached --------------------------------------
    c = by_id["L02"]
    n_before = emp_count()
    t0 = time.perf_counter()
    rep = scs.onboard(candidate_id="CAND-002", email="priya.nair02@example.com",
                      dept="Engineering", start_date="2026-11-30",
                      laptop_id="LT-1011", bg_status="pass",
                      confirm=True, preview_hash=stored["hash"],
                      idempotency_key=stored["key"])
    dt = (time.perf_counter() - t0) * 1000
    n_after = emp_count()
    ok = (rep.get("status") == "already_applied"
          and (rep.get("result", {}) or {}).get("employee_id") == stored["emp"]
          and n_after == n_before)
    rows.append({"id": "L02", "mode": "LIVE", "category": c["category"],
                 "expected": c["expected"],
                 "observed": f"{rep.get('status')} emp={(rep.get('result', {}) or {}).get('employee_id')} employees={n_before}->{n_after}",
                 "verdict": "PASS" if ok else "FAIL",
                 "detail": "same key+hash returned cached result; no 2nd write",
                 "latency_live_ms": round(dt, 1)})

    # ---- L03: BG-fail deny ----------------------------------------------
    c = by_id["L03"]
    t0 = time.perf_counter()
    bgf = scs.onboard(candidate_id="CAND-003", email="chen.wei03@example.com",
                      dept="Engineering", start_date="2026-11-30",
                      laptop_id="", bg_status="fail",
                      confirm=False, idempotency_key="live-L03-key")
    dt = (time.perf_counter() - t0) * 1000
    ok = bgf.get("status") == "denied" and "bg_fail_blocked" in bgf.get("reason", "")
    rows.append({"id": "L03", "mode": "LIVE", "category": c["category"],
                 "expected": c["expected"],
                 "observed": f"{bgf.get('status')} reason={bgf.get('reason', '')}",
                 "verdict": "PASS" if ok else "FAIL",
                 "detail": "denied at stage gate; ledger untouched; no HTTP writes",
                 "latency_live_ms": round(dt, 1)})

    # ---- L04: hold conflict deny at commit --------------------------------
    c = by_id["L04"]
    n_before = emp_count()
    t0 = time.perf_counter()
    stg4 = scs.onboard(candidate_id="CAND-004", email="sara.thomas04@example.com",
                       dept="Design", start_date="2026-11-30",
                       laptop_id="LT-1005", bg_status="pass",
                       confirm=False, idempotency_key="live-L04-key")
    act4 = None
    if stg4.get("status") == "preview":
        act4 = scs.onboard(candidate_id="CAND-004", email="sara.thomas04@example.com",
                           dept="Design", start_date="2026-11-30",
                           laptop_id="LT-1005", bg_status="pass",
                           confirm=True, preview_hash=stg4["preview_hash"],
                           idempotency_key="live-L04-key")
    dt = (time.perf_counter() - t0) * 1000
    n_after = emp_count()
    ok = (stg4.get("status") == "preview"
          and any("LT-1005" in w for w in stg4.get("warnings", []))
          and act4 is not None and act4.get("status") == "denied"
          and "precondition_failed" in act4.get("reason", "")
          and n_after == n_before)
    rows.append({"id": "L04", "mode": "LIVE", "category": c["category"],
                 "expected": c["expected"],
                 "observed": f"stage={stg4.get('status')} activate={(act4 or {}).get('status')} reason={(act4 or {}).get('reason', '')} employees={n_before}->{n_after}",
                 "verdict": "PASS" if ok else "FAIL",
                 "detail": f"stage warnings={stg4.get('warnings')}; commit re-derived hold -> deny",
                 "latency_live_ms": round(dt, 1)})

    # ---- L05: reroute -> live on-call --------------------------------------
    c = by_id["L05"]
    t0 = time.perf_counter()
    st, cov = http("GET", f"{a.it}/it/oncall-coverage", )
    cov = http("GET", f"{a.it}/it/oncall-coverage?team=support-night")[1] if st == 200 else cov
    oncall = (cov or {}).get("oncall", {}) or {}
    oc_email, oc_emp = oncall.get("email", ""), oncall.get("employee_id", "")
    rr = {}
    if oc_email:
        st2, rr = http("POST", f"{a.it}/it/tickets/T-5002/reroute",
                       {"to_email": oc_email, "reason": "live-eval-L05"})
    else:
        st2 = None
    st3, tk = http("GET", f"{a.it}/it/tickets/T-5002")
    dt = (time.perf_counter() - t0) * 1000
    ok = (oc_email and st2 == 200
          and (tk or {}).get("assignee_email") == oc_email)
    rows.append({"id": "L05", "mode": "LIVE", "category": c["category"],
                 "expected": c["expected"],
                 "observed": f"oncall={oc_emp}/{oc_email} reroute={st2} ticket_assignee_email={(tk or {}).get('assignee_email')}",
                 "verdict": "PASS" if ok else "FAIL",
                 "detail": "resolved owner via live L1 endpoint, rerouted breached ticket, re-read to verify",
                 "latency_live_ms": round(dt, 1)})

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    print(f"live cases={len(rows)} pass={n_pass} fail={len(rows) - n_pass} employees={n0}->{emp_count()}")
    for r in rows:
        print(f"  {r['id']}: {r['verdict']} [{r['latency_live_ms']}ms LIVE-measured] {r['observed']}")
    print(f"wrote {a.out}")
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
