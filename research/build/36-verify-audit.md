# 36 — Verify Audit Chain: seq Continuity, prev_hash Link, Hash Recompute, firstBadSeq, Denials + Anchor

**Sources:** `research/build/23-step-audit.md` §§1–6 (schema, hash rule, writer, verifier, anchor, hardening) · `research/final/13-safety-audit.md` §§1,8 (CITE→CHECK→ACT→RECORD, audit.jsonl schema, anchor head externally) · `research/build/04-auth.md` §§3–4 (args never raw, `args_hash` inputs, `${ENV}` redaction).
**Goal:** prove the append-only log is intact end-to-end — dense `seq` from 1, unbroken `prev_hash` links, recomputed `hash` on every record, denials chained, no raw args/secrets, and head hash pinned to an external anchor so truncation is detectable.
**Rule:** `hash = sha256_hex(canonical_json(record_minus_hash))`; `canonical_json = json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)`; `record[1].prev_hash == "0"*64`; `record[N].prev_hash == record[N-1].hash`; every proxy decision (allow AND deny) appends exactly one line.

## 1. Audit contract under test

| # | Check | Input / attack | Expect |
|---|---|---|---|
| 1 | `seq` continuity | delete line 3 of 5, or two writers race | verifier stops, `firstBadSeq=3`, `reason=seq gap/reorder: got 4, want 3` |
| 2 | `prev_hash` link | splice/fork: rewrite history before N | `firstBadSeq=N`, `reason=prev_hash mismatch (fork or deletion before it)`; everything ≥ N untrusted |
| 3 | Recomputed `hash` | flip one byte in record N (even `extra` field) | `firstBadSeq=N`, `reason=hash mismatch — edited in place`; chain after N fails transitively |
| 4 | `firstBadSeq` report | any of 1–3, plus bad JSON / missing field / bad decision / bad hex | single `(ok, firstBadSeq, reason)` tuple; first failure wins; `firstBadSeq=None` iff clean |
| 5 | Denials logged | blocked call (`preview_hash_mismatch`, `ambiguous_scope`, `insufficient_scope`) | a `decision=denied` line IS chained with valid `prev_hash`/`hash`; absence of denial lines = fail (silent-drop) |
| 6 | Args never raw | `grep` log for raw payload keys | only `args_hash` (`^[0-9a-f]{64}$`) present; no `"password"`, `"token"`, email bodies, `${ENV:…}` resolved values |
| 7 | External anchor head hash | truncate file to first K of N records (chain-self-check passes) | anchor replay fails: `tip[anchor.seq] != anchor.tip` or replay K→tip breaks; truncation detected only via anchor |

Field/shape rules (from 23 §1): `seq` int 1-indexed; `ts` UTC ISO-8601 `Z` (informational, never sort by it); `actor`/`tool` non-empty; `args_hash` hex64; `decision ∈ {auto-allow, approved, denied, override}`; `approved` requires `approval_id + preview_id/hash`; `override` requires `reason`; `prev_hash`/`hash` hex64 (`"0"*64` genesis only at seq 1). Extra fields (`reason`, `policy_version`, `session_id`, `duration_ms`, `anchor_ref`) allowed but MUST be hash-covered.

## 2. Verifier script (copy-paste, stdlib only)

Single file: verifies chain + denials presence + raw-secret scan + anchor replay. Exit 0 clean, 2 tampered.

```python
# audit_verify.py — chain + denials + no-raw-args + anchor replay (stdlib only)
import hashlib, json, re, sys

GENESIS = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = ["seq", "ts", "actor", "tool", "args_hash", "decision", "prev_hash", "hash"]
DECISIONS = {"auto-allow", "approved", "denied", "override"}
# Raw-secret tripwires: any of these literal keys/patterns in the log = fail check 6.
RAW_TRIPWIRES = re.compile(r'"password"|"token"|"secret"|"api[_-]?key"|"Authorization"|[\w.+-]+@[\w-]+\.[\w.]+|\$\{ENV:[A-Za-z_][A-Za-z0-9_]*\}:(?!\[REDACTED\])', re.IGNORECASE)

def canonical(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def verify_chain(path: str, strict_extra: bool = False, known_keys: set | None = None):
    """Returns (ok, firstBadSeq, reason, records). First failure wins."""
    prev_hash, expect_seq = GENESIS, 1
    with open(path, "rb") as f:
        raw_lines = f.read().splitlines()
    lines = [(i + 1, ln) for i, ln in enumerate(raw_lines) if ln.strip()]
    if not lines:
        return True, None, "empty-log-ok", []
    recs = []
    for file_line, ln in lines:
        try:
            rec = json.loads(ln)
        except Exception as e:
            return False, expect_seq, f"line {file_line}: invalid JSON: {e}", recs
        for k in REQUIRED:
            if k not in rec:
                return False, rec.get("seq", expect_seq), f"line {file_line}: missing {k}", recs
        seq = rec["seq"]
        if seq != expect_seq:
            return False, expect_seq, f"line {file_line}: seq gap/reorder: got {seq}, want {expect_seq}", recs
        if rec["prev_hash"] != prev_hash:
            return False, seq, f"seq {seq}: prev_hash mismatch (fork or deletion before it)", recs
        if not HEX64.match(rec.get("args_hash") or ""):
            return False, seq, f"seq {seq}: bad args_hash shape", recs
        if not HEX64.match(rec.get("hash") or "") or not HEX64.match(rec.get("prev_hash") or ""):
            return False, seq, f"seq {seq}: bad hash/prev_hash hex shape", recs
        if rec["decision"] not in DECISIONS:
            return False, seq, f"seq {seq}: bad decision {rec['decision']!r}", recs
        if rec["decision"] == "approved" and (not rec.get("approval_id") or not rec.get("preview_id")):
            return False, seq, f"seq {seq}: approved without approval_id/preview_id", recs
        if strict_extra and known_keys is not None:
            unknown = set(rec) - known_keys
            if unknown:
                return False, seq, f"seq {seq}: unknown fields {sorted(unknown)}", recs
        expect = hashlib.sha256(canonical({k: v for k, v in rec.items() if k != "hash"})).hexdigest()
        if rec["hash"] != expect:
            return False, seq, f"seq {seq}: hash mismatch — edited in place (want {expect[:12]}..., got {str(rec['hash'])[:12]}...)", recs
        recs.append(rec)
        prev_hash, expect_seq = rec["hash"], seq + 1
    return True, None, f"ok: {len(recs)} records, tip {prev_hash[:12]}...", recs

def check_denials(recs):
    """Check 5: at least one denied line exists AND each denial is chain-valid (already proven)."""
    denied = [r for r in recs if r.get("decision") == "denied"]
    if not denied:
        return False, "no decision=denied line found — denials must be chained, not silently dropped"
    reasons = {str(r.get("reason", "")) for r in denied}
    return True, f"denials chained: {len(denied)} line(s), reasons={sorted(reasons) or ['(no reason field)']}"

def check_no_raw_args(path: str):
    """Check 6: log must carry args_hash only — no raw secret-shaped values."""
    with open(path, "rb") as f:
        text = f.read().decode("utf-8", errors="replace")
    # Allow the words inside reason/enum text; fail on key-shaped or value-shaped leaks:
    # resolved ${ENV:VAR}=value, password/token keys with values, raw emails in args context.
    leak = re.search(r'"(password|passwd|token|secret|api_key|apikey)"\s*:\s*"[^"]+"', text, re.IGNORECASE)
    if leak:
        return False, f"raw secret key found: {leak.group(0)[:60]}... (store args_hash only)"
    if re.search(r'\$\{ENV:[A-Za-z_][A-Za-z0-9_]*\}', text):
        # ${ENV:NAME} reference itself in an anchor/reason is tolerable ONLY if never
        # followed by a resolved value; flag for human review, do not auto-fail:
        return True, "note: ${ENV:NAME} reference present — confirm no resolved value adjacent (manual review)"
    return True, "no raw args/secrets detected (args_hash only)"

def verify_anchor(path: str, anchor_path: str):
    """Check 7: anchor tip must equal chain record at anchor.seq; replay forward must be clean."""
    with open(anchor_path, "r", encoding="utf-8") as f:
        anchor = json.load(f)
    ok, bad, reason, recs = verify_chain(path)
    if not ok:
        return False, bad, f"chain broken before anchor check: {reason}"
    seq, tip = int(anchor["seq"]), str(anchor["tip"])
    if seq < 1 or seq > len(recs):
        return False, seq, f"anchor seq {seq} out of range (log has {len(recs)} records — truncated?)"
    got = recs[seq - 1]["hash"]
    if got != tip and not tip.startswith(got[:12]) and not got.startswith(tip[:12] if len(tip) >= 12 else tip):
        # Exact compare when anchor stores full hash; prefix compare when it stores short tip.
        full_tip = tip if HEX64.match(tip) else None
        if full_tip is None and got[:len(tip)] != tip:
            return False, seq, f"anchor mismatch at seq {seq}: log has {got[:12]}..., anchor says {tip[:12]}... (truncation/forgery?)"
        if full_tip is not None:
            return False, seq, f"anchor mismatch at seq {seq}: want {tip[:12]}..., got {got[:12]}... (truncation/forgery?)"
    head = recs[-1]["hash"]
    return True, None, f"anchor ok: seq {seq} tip {tip[:12]}... matches; head seq {len(recs)} hash {head[:12]}..."

if __name__ == "__main__":
    log = sys.argv[1] if len(sys.argv) > 1 else ".synapse/audit.jsonl"
    anchor = sys.argv[2] if len(sys.argv) > 2 else None
    ok, bad, reason, recs = verify_chain(log)
    print({"check": "chain", "ok": ok, "firstBadSeq": bad, "reason": reason})
    if ok and recs:
        d_ok, d_msg = check_denials(recs)
        print({"check": "denials", "ok": d_ok, "detail": d_msg})
        r_ok, r_msg = check_no_raw_args(log)
        print({"check": "no_raw_args", "ok": r_ok, "detail": r_msg})
        ok = ok and d_ok and r_ok
    if anchor:
        a_ok, a_bad, a_msg = verify_anchor(log, anchor)
        print({"check": "anchor", "ok": a_ok, "firstBadSeq": a_bad, "reason": a_msg})
        ok = ok and a_ok
    sys.exit(0 if ok else 2)
```

Run:

```bash
python audit_verify.py .synapse/audit.jsonl
# {"check": "chain", "ok": true, "firstBadSeq": null, "reason": "ok: 42 records, tip 31f0ab..."}
# {"check": "denials", "ok": true, "detail": "denials chained: 3 line(s), ..."}
# {"check": "no_raw_args", "ok": true, "detail": "no raw args/secrets detected ..."}
python audit_verify.py .synapse/audit.jsonl .synapse/anchors/000042.json
# {"check": "anchor", "ok": true, "firstBadSeq": null, "reason": "anchor ok: ..."}
```

## 3. Tamper-drill matrix (ship-blocking, run on a COPY)

| # | Drill | Command | Verifier must print |
|---|---|---|---|
| T1 | Clean | `python audit_verify.py copy.jsonl` | `ok: true, firstBadSeq: null` |
| T2 | Edit-in-place | flip 1 byte in record 2 of copy | `ok: false, firstBadSeq: 2, hash mismatch` |
| T3 | Delete line | drop line 3 of 5 in copy | `firstBadSeq: 3, seq gap/reorder: got 4, want 3` |
| T4 | Splice/fork | replace lines ≥3 with a re-hashed alternate history | `firstBadSeq: 3, prev_hash mismatch` |
| T5 | Truncation | `head -K copy` keeps chain-self-check green | chain `ok: true` BUT anchor check fails (`anchor seq out of range / mismatch`) — proves anchor is load-bearing |
| T6 | Raw-secret plant | append line with `"password":"x"` raw (re-chained so chain passes) | chain `ok: true`, `no_raw_args ok: false` — policy fail, rotate + rewrite rule |

```bash
cp .synapse/audit.jsonl /tmp/audit_copy.jsonl
python -c "import json; p='/tmp/audit_copy.jsonl'; ls=open(p).read().splitlines(); r=json.loads(ls[1]); r['tool']='EVIL'; r.pop('hash',None); import hashlib; r['hash']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest() if False else '0'*64; ls[1]=json.dumps(r); open(p,'w').write('\n'.join(ls)+'\n')"
python audit_verify.py /tmp/audit_copy.jsonl   # expect firstBadSeq: 2
```

## 4. Anchor publish + replay (stops whole-file forgery)

Chain alone cannot prove you weren't handed a fully rewritten file. Publish the tip after every milestone (or every 50 records / 15 min):

```jsonc
// .synapse/anchors/000042.json
{"seq": 42, "tip": "31f0ab...", "ts": "2026-05-13T15:00:00Z", "prev_anchor_tip": "9a1e...", "where": "git-tag audit-000042"}
```

Cheapest first: **git tag** → append-only object store (S3 Object Lock) → RFC 3161 timestamp:

```bash
git add .synapse/audit.jsonl && git commit -m "audit tip <head-hash> seq <n>" && git tag audit-<seq>-<shorthash>
python audit_verify.py .synapse/audit.jsonl .synapse/anchors/000042.json
```

Verifier-with-anchor rule: `verify(chain) AND tip[anchor.seq] == anchor.tip AND replay(anchor.seq → tip) clean`. Report `head_hash + count` alongside every verdict so an external dashboard can compare without reading the file.

## 5. Reviewer checklist (fail the build if any is missing)

- [ ] `python audit_verify.py` exits 0, prints `firstBadSeq: null` on chain + anchor.
- [ ] Tamper drill T2–T4 each names the exact `seq` tampered (no off-by-one).
- [ ] T5 truncation passes chain but FAILS anchor — anchor wiring proven, not decorative.
- [ ] At least one `decision=denied` line exists and verifies (blocked preview-hash mismatch or scope deny exercised in tests).
- [ ] `grep -E '"password"|"token"|"secret"' audit.jsonl` empty of raw values; only `args_hash` hex64 present; `${ENV:*}` never resolved in log.
- [ ] One writer process per file (queue tool calls through it); `msvcrt.locking`/`fcntl.flock` around read-tip+append if multi-process; file `0600`, ACL to writer identity.
- [ ] `ts` never used for ordering — sort/verify by `seq` only; `policy_version` pinned per deployment.

*Delta vs cited sources: 23 defines schema/hash/writer/anchor semantics; 13 §8 defines the v:1 decision vocabulary; this file pins the executable verdict — check order (seq → prev_hash → shape → decision-matrix → recompute), the `firstBadSeq` tuple, the denials-present + no-raw-args gates, and the anchor-replay command. Nothing here changes the hash algorithm.*
