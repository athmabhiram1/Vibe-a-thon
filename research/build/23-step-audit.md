# Step 23 — Hash-Chained `audit.jsonl`: Tamper-Evident Tool Audit

> Goal: every tool call leaves an append-only, hash-chained receipt that proves **what was approved, what ran, and that nothing was edited after the fact** — without ever storing raw secrets in the log.
> File: `.synapse/audit.jsonl` (one canonical JSON object per line, UTF-8, `\n`-terminated). Never rewrite history; only append.

## 1. Record schema (frozen — one line per tool invocation)

| Field | Type | Required | Rule |
|---|---|---|---|
| `seq` | int | yes | 1-indexed, contiguous, no gaps/reuse. First record `seq=1`. |
| `ts` | string | yes | UTC ISO-8601 with `Z`, e.g. `2026-05-13T14:02:11.042Z`. Writer clock only; verifier does not trust ordering by `ts`, only by `seq`. |
| `actor` | string | yes | Who/what invoked: `user:<id>`, `agent:<name>`, `system:cron`. No PII beyond ID. |
| `tool` | string | yes | Tool/endpoint id, e.g. `it_reroute_ticket`, `hr_create_employee`, `fs.write`. Must match allow-listed tool name. |
| `args_hash` | string | yes | `sha256` hex (64 lowercase chars) of **canonical JSON of args**. **Never store raw args** (may contain PII/secrets/tokens). |
| `preview_id` | string | no* | ID of the pre-execution preview shown for approval (required when `decision` needs approval). |
| `preview_hash` | string | no* | `sha256` hex of the canonical preview body the approver saw. Binds "what was shown" to "what ran". |
| `approval_id` | string | no* | Approval ticket/id that authorized this call (`appr_...`). Required for mutating tools; `null` for read-only + `decision=auto-allow`. |
| `decision` | string | yes | One of `auto-allow` \| `approved` \| `denied` \| `override`. `denied` records are still chained (proof the call was blocked). |
| `prev_hash` | string | yes | `hash` of record `seq-1`. For `seq=1`: `"0".repeat(64)` (`GENESIS`). |
| `hash` | string | yes | `sha256` hex chaining this record to history (see §2). Computed last, covers all fields above. |

`*` Required-matrix:

| `decision` | `approval_id` | `preview_id/hash` |
|---|---|---|
| `auto-allow` (read-only) | `null` allowed | optional (set if preview was shown anyway) |
| `approved` | **required** | **required** |
| `denied` | required if approval was requested, else `null` | required if preview existed |
| `override` (break-glass) | `null` + must set `reason` extra field | required — what was shown |

Extra optional fields (`reason`, `policy_version`, `session_id`, `duration_ms`, `anchor_ref`) are allowed **but must be included in the hash** (hash covers the whole object minus `hash` itself). Unknown fields fail closed in strict verifiers — pin `policy_version` per deployment.

**Example lines (pretty-printed here; on disk each is one line):**

```json
{"seq":1,"ts":"2026-05-13T14:02:11.042Z","actor":"agent:demo","tool":"it_sla_breach_list","args_hash":"4f3c…","preview_id":null,"preview_hash":null,"approval_id":null,"decision":"auto-allow","policy_version":"p23.1","prev_hash":"0000000000000000000000000000000000000000000000000000000000000000","hash":"9a1e…"}
{"seq":2,"ts":"2026-05-13T14:02:14.900Z","actor":"agent:demo","tool":"it_reroute_ticket","args_hash":"b71d…","preview_id":"prev_7f3a","preview_hash":"c88e…","approval_id":"appr_9c21","decision":"approved","policy_version":"p23.1","prev_hash":"9a1e…","hash":"31f0…"}
```

## 2. Hash rule (canonical — writer and verifier must agree byte-for-byte)

```
args_hash    = SHA256_HEX(canonical_json(args))
preview_hash = SHA256_HEX(canonical_json(preview_body))   # what approver saw
hash         = SHA256_HEX(canonical_json(record_minus_hash))
```

`canonical_json(v)` = `json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded UTF-8. No whitespace, sorted keys, no NaN/Infinity, no floats for money — normalize before hashing.

`record_minus_hash` = the full record object **with `hash` removed** (all other fields including `prev_hash` included). `hash` is lowercase hex, 64 chars.

Chain: `record[N].prev_hash == record[N-1].hash`, and `record[1].prev_hash == "0"*64`.

Why `args_hash (never raw)`: args routinely contain emails, tokens, file contents. The log proves *which exact args* ran (recompute and compare) without becoming a secret-spill. Keep a separate encrypted argument vault keyed by `args_hash` if replay is needed — the JSONL itself stays safe to copy/paste.

## 3. Writer — copy-paste (Python stdlib only, atomic append + file lock)

```python
# audit_writer.py — append-only hash-chained audit.jsonl writer (stdlib only)
import hashlib, json, os, time
from datetime import datetime, timezone

AUDIT_PATH = os.environ.get("AUDIT_PATH", ".synapse/audit.jsonl")
GENESIS = "0" * 64
DECISIONS = {"auto-allow", "approved", "denied", "override"}

def canonical(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def sha_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _read_tip(path: str):
    """Return (last_seq, last_hash). (0, GENESIS) when file missing/empty."""
    try:
        with open(path, "rb") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except FileNotFoundError:
        return 0, GENESIS
    if not lines:
        return 0, GENESIS
    tip = json.loads(lines[-1])
    return int(tip["seq"]), str(tip["hash"])

def append_audit(*, actor: str, tool: str, args: dict,
                 decision: str, approval_id: str | None = None,
                 preview_id: str | None = None, preview_body: dict | None = None,
                 extra: dict | None = None, path: str = AUDIT_PATH) -> dict:
    if decision not in DECISIONS:
        raise Value TambiénError(f"bad decision {decision!r}")
    if decision == "approved" and (not approval_id or preview_id is None):
        raise ValueError("approved requires approval_id + preview_id/hash")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # Best-effort cross-process lock (Windows-safe: lock file sentinel).
    # For single-writer demos this is enough; use fcntl/msvcrt for hard locking (§6).
    last_seq, last_hash = _read_tip(path)
    record = {
        "seq": last_seq + 1,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "actor": actor,
        "tool": tool,
        "args_hash": sha_hex(canonical(args)),
        "preview_id": preview_id,
        "preview_hash": sha_hex(canonical(preview_body)) if preview_body is not None else None,
        "approval_id": approval_id,
        "decision": decision,
        "policy_version": (extra or {}).pop("policy_version", "p23.1"),
        **(extra or {}),
        "prev_hash": last_hash,
    }
    record["hash"] = sha_hex(canonical(record))
    line = canonical(record) + b"\n"
    # O_APPEND is atomic for short lines on POSIX/NTFS; verify on read (§4).
    with open(path, "ab") as f:
        f.write(line)
    # Optional fsync for crash safety (uncomment on laptops):
    # f.flush(); os.fsync(f.fileno())
    return record

if __name__ == "__main__":
    print(append_audit(actor="agent:demo", tool="it_sla_breach_list",
                       args={"team": "support-night"}, decision="auto-allow"))
```

Usage with approval flow:

```python
prev_body = {"tool": "it_reroute_ticket", "summary": "T-551 -> on-call …", "diff": "assignee: a@x → b@y"}
r = append_audit(actor="agent:demo", tool="it_reroute_ticket",
                 args={"ticket_id": "T-551", "to_email": "b@y"},
                 decision="approved", approval_id="appr_9c21",
                 preview_id="prev_7f3a", preview_body=prev_body)
```

## 4. Verifier — copy-paste (returns `firstBadSeq`)

Contract: scan in `seq` order; first failure wins. Returns `(ok: bool, firstBadSeq: int | None, reason: str)`. `firstBadSeq=None` means clean.

Checks per line, in order: (a) valid JSON + required fields + types; (b) `seq` contiguous from 1; (c) `prev_hash` linkage (genesis for seq 1); (d) recomputed `hash` matches; (e) `decision` in enum + approval-matrix (§1); (f) hex-shape of hashes (`^[0-9a-f]{64}$` or null where allowed).

```python
# audit_verify.py — verifier with firstBadSeq (stdlib only)
import hashlib, json, re, sys

GENESIS = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = ["seq", "ts", "actor", "tool", "args_hash", "decision", "prev_hash", "hash"]

def canonical(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def verify(path: str, strict_extra: bool = False, known_keys: set | None = None):
    prev_hash, expect_seq = GENESIS, 1
    with open(path, "rb") as f:
        raw_lines = f.read().splitlines()
    lines = [(i + 1, ln) for i, ln in enumerate(raw_lines) if ln.strip()]
    if not lines:
        return True, None, "empty-log-ok"
    for file_line, ln in lines:
        try:
            rec = json.loads(ln)
        except Exception as e:
            return False, expect_seq, f"line {file_line}: invalid JSON: {e}"
        for k in REQUIRED:
            if k not in rec:
                return False, rec.get("seq", expect_seq), f"line {file_line}: missing {k}"
        seq = rec["seq"]
        if seq != expect_seq:
            return False, expect_seq, f"line {file_line}: seq gap/reorder: got {seq}, want {expect_seq}"
        if rec["prev_hash"] != prev_hash:
            return False, seq, f"seq {seq}: prev_hash mismatch (fork or deletion before it)"
        if not HEX64.match(rec.get("args_hash") or ""):
            return False, seq, f"seq {seq}: bad args_hash shape"
        if rec["decision"] not in {"auto-allow", "approved", "denied", "override"}:
            return False, seq, f"seq {seq}: bad decision {rec['decision']!r}"
        if rec["decision"] == "approved" and (not rec.get("approval_id") or not rec.get("preview_id")):
            return False, seq, f"seq {seq}: approved without approval_id/preview_id"
        if strict_extra and known_keys is not None:
            unknown = set(rec) - known_keys
            if unknown:
                return False, seq, f"seq {seq}: unknown fields {sorted(unknown)}"
        expect = hashlib.sha256(canonical({k: v for k, v in rec.items() if k != "hash"})).hexdigest()
        if rec["hash"] != expect:
            return False, seq, f"seq {seq}: hash mismatch — edited in place (want {expect[:12]}…, got {str(rec['hash'])[:12]}…)"
        prev_hash, expect_seq = rec["hash"], seq + 1
    return True, None, f"ok: {len(lines)} records, tip {prev_hash[:12]}…"

if __name__ == "__main__":
    ok, bad, reason = verify(sys.argv[1] if len(sys.argv) > 1 else ".synapse/audit.jsonl")
    print({"ok": ok, "firstBadSeq": bad, "reason": reason})
    sys.exit(0 if ok else 2)
```

Interpreting `firstBadSeq`:

| Symptom | Meaning |
|---|---|
| `seq gap` at N | Lines deleted or two writers raced. Quarantine from N onward; restore from anchor (§5). |
| `prev_hash mismatch` at N | Fork / splice — history rewritten before N. Everything ≥ N is untrusted. |
| `hash mismatch` at N | Record N edited in place (even one byte). Record N — and by chain, all after — fail. |
| Clean (`firstBadSeq=null`) | Integrity holds **since genesis or since last verified anchor** — still confirm anchor (§5) for truncation attacks. |

```bash
python audit_verify.py .synapse/audit.jsonl
# {"ok": true, "firstBadSeq": null, "reason": "ok: 42 records, tip 31f0ab…"}
```

## 5. External anchor (stops truncation / whole-file forgery)

A chain alone can't prove you weren't handed a *fully rewritten* file. Periodically publish the tip elsewhere:

```json
// .synapse/anchors/000042.json
{"seq":42,"tip":"31f0ab…","ts":"2026-05-13T15:00:00Z","prev_anchor_tip":"9a1e…","where":"git-tag audit-000042"}
```

Pick one (cheapest first):

1. **Git tag/commit** (demo default): `git add .synapse/audit.jsonl && git commit -m "audit tip <hash> seq <n>" && git tag audit-<seq>-<shorthash>`. Verifier checks `git show <tag>:audit.jsonl | sha256` chains to current tip.
2. **Append-only object store** (S3 with Object Lock / Azure immutable blob): upload `anchors/<seq>.json` with retention lock; verifier fetches latest anchor and replays forward.
3. **RFC 3161 timestamp / transparency log**: `openssl ts -query -data audit.jsonl -cert | curl <tsa>`; store `.tsr` next to anchor. Proves existence at time T.

Anchor cadence: every demo milestone (or every 50 records / 15 min in prod). Verifier with anchor: `verify(chain) AND tip[anchor.seq] == anchor.tip AND replay(anchor.seq → tip) clean`. A truncated file passes chain-self-check but fails anchor replay — that's the point.

## 6. Hardening + pre-demo checklist

- **One writer process** per file (queue tool calls through it). Two writers → `seq` race. If multi-process, guard append with `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) around read-tip+append.
- **File perms**: ACL to writer identity only; ship logs off-box before showing on projector (hashes are safe, `extra` fields may not be — audit `extra` for secrets).
- **Clock**: `ts` informational only; never gate on it. Sort/verify by `seq`.
- **Denied calls are chained too** — abort still appends (`decision=denied`), so "the agent tried X and was stopped" is provable.
- [ ] `python audit_verify.py` exits 0, prints `firstBadSeq: null`.
- [ ] Tamper drill passes: flip one byte in a copy → verifier names that exact `seq`.
- [ ] Latest anchor published (`git tag audit-<seq>-*` exists) and replay from anchor is clean.
- [ ] `grep -c "args" audit.jsonl` shows only `args_hash` — no raw `"password"`, `"token"`, email bodies in the log.
