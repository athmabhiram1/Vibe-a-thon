# Step 21 — Approval Gate: Preview → Approve → Execute

> Goal: no mutating tool executes blind. Every write requires an explicit preview with integrity hash, an out-of-band `APPROVE <id>` (or `confirm=True`), optimistic-concurrency check, and a 10-minute expiry. Deny messages are verbatim contracts — copy them exactly.

## 1. Rules (non-negotiable)

1. **Preview first.** A mutating call without a prior `preview` is rejected.
2. **`confirm=True` required.** Default is dry-run. `confirm=False`/`None`/omitted → deny.
3. **`preview_hash` = sha256 of canonical JSON** of the exact args that will execute.
4. **`base_hash` optimistic concurrency.** Caller passes the state hash it previewed against; mismatch → deny (re-preview).
5. **10-min TTL.** `preview.created_at + 600s < now` → expired, re-preview.
6. **Single-use.** An approval is consumed on first execute (success or fail). Replays → deny.
7. **Deny messages verbatim.** Clients key on these strings; do not reword.

## 2. Canonical JSON + preview_hash (spec)

```python
import json, hashlib

def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")

def preview_hash(args: dict) -> str:
    return hashlib.sha256(canonical(args)).hexdigest()
```

- Canonical form: `sort_keys=True`, `separators=(",", ":")`, UTF-8, no whitespace, `ensure_ascii=False`.
- Hash covers **tool name + args only** (not timestamps, not request ids).
- Server recomputes on `execute` and compares with `==` (constant-time compare preferred: `hmac.compare_digest`).

## 3. State machine

```
(no preview) --preview--> PENDING(id, tool, args, preview_hash, base_hash, created_at)
PENDING --execute[confirm=True, hash match, base match, fresh, unused]--> EXECUTED (consumed)
PENDING --execute[any check fails]--> DENIED (stays PENDING until consumed or expired)*
PENDING --600s elapsed--> EXPIRED (re-preview required)
```

\* Failed executes do **not** consume the approval — caller may fix and retry within TTL — except on success, which always consumes. Alternative strict policy: consume-on-any-execute; pick one and document it. Default here: consume-on-success.

## 4. Copy-paste server (`guarded_call`)

```python
import hashlib, hmac, json, time, secrets
from dataclasses import dataclass, field

TTL_S = 600  # 10 minutes

def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False).encode()

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

@dataclass
class Preview:
    id: str
    tool: str
    args: dict
    preview_hash: str
    base_hash: str | None
    created_at: float = field(default_factory=time.time)
    used: bool = False

STORE: dict[str, Preview] = {}
# current_state_hash(): hash of the resource/version the write depends on
# (e.g., file mtime+size, DB row version, git HEAD). Return None if unversioned.

def preview(tool: str, args: dict, base_hash: str | None) -> dict:
    pid = "apv_" + secrets.token_hex(4)
    ph = sha256_hex(canonical({"tool": tool, "args": args}))
    STORE[pid] = Preview(id=pid, tool=tool, args=args,
                         preview_hash=ph, base_hash=base_hash)
    return {"approval_id": pid, "preview_hash": ph,
            "base_hash": base_hash, "ttl_s": TTL_S,
            "human": render_preview(pid, tool, args)}

def guarded_call(approval_id: str, tool: str, args: dict,
                 confirm: bool, preview_hash_: str,
                 base_hash: str | None,
                 current_state_hash: str | None,
                 do_execute) -> dict:
    p = STORE.get(approval_id)
    if p is None or p.tool != tool:
        return deny("DENY: unknown approval_id. Re-run preview.")
    if p.used:
        return deny("DENY: approval already used. Re-run preview for a new approval_id.")
    if time.time() - p.created_at > TTL_S:
        return deny("DENY: approval expired (>10 min). Re-run preview.")
    if confirm is not True:
        return deny("DENY: confirm=True required. Re-send execute with confirm=True.")
    expect = sha256_hex(canonical({"tool": tool, "args": args}))
    if not hmac.compare_digest(expect, preview_hash_) or \
       not hmac.compare_digest(expect, p.preview_hash):
        return deny("DENY: preview_hash mismatch. Args changed since preview. Re-run preview.")
    if p.base_hash is not None and base_hash != p.base_hash:
        return deny("DENY: base_hash mismatch. Re-run preview with current base_hash.")
    if p.base_hash is not None and current_state_hash != p.base_hash:
        return deny("DENY: stale base. State changed since preview. Re-run preview.")
    p.used = True  # consume before execute to block double-submit races
    try:
        result = do_execute(tool, args)
    except Exception:
        p.used = False  # allow retry within TTL on executor crash (strict alt: keep True)
        raise
    return {"ok": True, "approval_id": approval_id, "result": result}

def deny(msg: str) -> dict:
    return {"ok": False, "error": msg}

def render_preview(pid: str, tool: str, args: dict) -> str:
    lines = [f"Approval {pid} — `{tool}` will run with:"]
    lines += [f"  {k} = {v!r}" for k, v in args.items()]
    lines += [f"Reply APPROVE {pid} to execute (expires in 10 min)."]
    return "\n".join(lines)
```

**Wire-in checklist:** `confirm` defaults to `False` in the schema (never default `True`); `preview_hash`/`base_hash` are required string fields on execute; server is the sole computer of `current_state_hash`.

## 5. UX strings (verbatim — APPROVE <id> flow)

Preview response (chat-visible):

```
Proposing `<tool>` (approval `apv_9f2c1a4b`):
  path = "notes/demo.md"
  edit = "append 'hello'"
  preview_hash = `e3b0…c912`
  base_hash = `mt_7f3a`
This is a PREVIEW — nothing was changed.
Reply APPROVE apv_9f2c1a4b to execute (expires in 10 min), or REJECT apv_9f2c1a4b to discard.
```

Confirm prompt (if user tries to skip):

```
To run this I need explicit approval. Reply APPROVE apv_9f2c1a4b (or re-send with confirm=True + matching preview_hash and base_hash).
```

Executed:

```
OK: executed `<tool>` under approval `apv_9f2c1a4b`. Approval consumed — a repeat needs a fresh preview.
```

Rejected / discarded:

```
OK: approval `apv_9f2c1a4b` discarded. Nothing was changed.
```

## 6. Deny messages (verbatim — do not reword)

| Condition | Exact `error` string |
|---|---|
| No/unknown id | `DENY: unknown approval_id. Re-run preview.` |
| Reused id | `DENY: approval already used. Re-run preview for a new approval_id.` |
| Expired (>600 s) | `DENY: approval expired (>10 min). Re-run preview.` |
| `confirm` not `True` | `DENY: confirm=True required. Re-send execute with confirm=True.` |
| Args drift | `DENY: preview_hash mismatch. Args changed since preview. Re-run preview.` |
| Caller base mismatch | `DENY: base_hash mismatch. Re-run preview with current base_hash.` |
| State moved on | `DENY: stale base. State changed since preview. Re-run preview.` |

## 7. Client call sequence (copy-paste)

```python
# 1. Preview (dry-run, no confirm)
pv = preview("write_file", {"path": "notes/demo.md", "text": "hello\n"}, base_hash="mt_7f3a")
print(pv["human"])  # show user; wait for "APPROVE apv_..."

# 2. On APPROVE apv_XXX — execute with identical args + hashes
out = guarded_call(
    approval_id=pv["approval_id"],
    tool="write_file",
    args={"path": "notes/demo.md", "text": "hello\n"},  # byte-identical to preview
    confirm=True,
    preview_hash_=pv["preview_hash"],
    base_hash=pv["base_hash"],
    current_state_hash=state_hash("notes/demo.md"),
    do_execute=real_write_file,
)
```

**Double-submit guard:** disable the Approve button after first click; server-side `used` flag is the backstop.

## 8. Test matrix (all must pass)

- [ ] Execute without preview → `unknown approval_id`.
- [ ] Execute with `confirm=False`/omitted → `confirm=True required`.
- [ ] Flip one arg char after preview → `preview_hash mismatch`.
- [ ] Touch underlying state (change `current_state_hash`) → `stale base`.
- [ ] Sleep/fast-forward 601 s → `expired`.
- [ ] Execute twice on same id → second is `already used`.
- [ ] `APPROVE <wrong-id>` → `unknown approval_id`; nothing executes.
