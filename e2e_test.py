"""End-to-end verification for CleanSlate AI — both dev-ui and chat."""

import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
APP  = "cleanslate_ai_my_pc_assistant"
USER = "user"

# ── helpers ────────────────────────────────────────────────────────────────

def new_session():
    req = urllib.request.Request(
        f"{BASE}/apps/{APP}/users/{USER}/sessions",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )
    data = json.loads(urllib.request.urlopen(req).read())
    return data.get("id") or data.get("session_id")


def send(sid, text, resume=None, timeout=50):
    body = {
        "app_name": APP,
        "user_id":  USER,
        "session_id": sid,
        "new_message": {"role": "user", "parts": [{"text": text}]},
    }
    if resume:
        body["resume_inputs"] = resume
    req = urllib.request.Request(
        f"{BASE}/run_sse",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode(),
    )
    best, iid, imsg = "", None, ""
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                ev  = json.loads(payload)
                out = ev.get("output") or {}
                fc  = ((ev.get("content") or {}).get("parts") or [{}])[0].get("functionCall") or {}
                if fc.get("id"):
                    iid  = fc["id"]
                    imsg = fc.get("args", {}).get("message", "")
                t = (
                    out.get("human_readable_report")
                    or out.get("message")
                    or out.get("conversational_response")
                    or ""
                )
                if t:
                    best = t
            except Exception:
                pass
    return best, iid, imsg


passed = 0
total  = 0

def check(label, condition, detail=""):
    global passed, total
    total += 1
    sym = "✅" if condition else "❌"
    suffix = f": {str(detail)[:130]}" if detail else ""
    print(f"  {sym} {label}{suffix}")
    if condition:
        passed += 1
    return condition


print()
print("══════════════════════════════════════════════════════")
print("  END-TO-END TEST — CleanSlate AI My PC Assistant")
print("══════════════════════════════════════════════════════")

# ── 1. dev-ui ──────────────────────────────────────────────────────────────
print()
print("[ 1 ] DEV-UI  →  http://127.0.0.1:8000/dev-ui/")
try:
    r = urllib.request.urlopen(f"{BASE}/dev-ui/")
    body_text = r.read().decode("utf-8", errors="replace")
    check("dev-ui returns 200", r.status == 200)
    check("dev-ui HTML contains agent/ADK content",
          "adk" in body_text.lower() or "agent" in body_text.lower())
except Exception as e:
    check("dev-ui reachable", False, str(e))
    check("dev-ui HTML content", False)

# ── 2. custom chat ──────────────────────────────────────────────────────────
print()
print("[ 2 ] CUSTOM CHAT  →  http://127.0.0.1:8000/chat")
try:
    r = urllib.request.urlopen(f"{BASE}/chat")
    body_text = r.read().decode("utf-8", errors="replace")
    check("chat returns 200", r.status == 200)
    check("chat contains CleanSlate branding", "CleanSlate" in body_text)
    check("chat has My PC Assistant text",     "My PC Assistant" in body_text)
    check("chat has send button / input",
          "sendBtn" in body_text or "userInput" in body_text or "id=\"input\"" in body_text)
except Exception as e:
    check("chat reachable", False, str(e))
    for _ in range(3):
        check("(skipped)", False)

# ── 3. greeting ────────────────────────────────────────────────────────────
print()
print('[ 3 ] GREETING  →  "hi"')
sid_hi = new_session()
print(f"     session_id: {sid_hi}")
reply_hi, iid_hi, _ = send(sid_hi, "hi")
check("Got non-empty reply",                bool(reply_hi))
check("Reply length sane (< 1000 chars)",   len(reply_hi) < 1000,   f"len={len(reply_hi)}")
check("Contains CleanSlate / PC Assistant", "CleanSlate" in reply_hi or "PC Assistant" in reply_hi)
check("No HITL interrupt for greeting",     iid_hi is None)
print(f"     preview: {repr(reply_hi[:100])}")

# ── 4. organize intent ─────────────────────────────────────────────────────
print()
print('[ 4 ] ORGANIZE FLOW  →  "organize my computer"')
sid_org = new_session()
print(f"     session_id: {sid_org}")
reply_org, iid_org, imsg_org = send(sid_org, "organize my computer")
check("Correct interrupt_id = parent_folder",      iid_org == "parent_folder",
      f"got={iid_org!r}")
check("Prompt mentions folder/path/organize",
      any(kw in (imsg_org or "").lower() for kw in ["folder", "path", "organize"]))
check("Prompt length sane (< 2000 chars)",         len(imsg_org) < 2000,  f"len={len(imsg_org)}")
print(f"     interrupt_id  : {iid_org!r}")
print(f"     prompt preview: {repr(imsg_org[:130])}")

# ── 5. step 2 of organize — user provides parent folder ───────────────────
print()
print("[ 5 ] ORGANIZE STEP 2  →  user provides parent folder path")
import os as _os
_test_folder = _os.getcwd().replace('\\', '/')
if iid_org == "parent_folder":
    r5, iid5, imsg5 = send(
        sid_org,
        _test_folder,
        resume={"parent_folder": _test_folder},
    )
    # Agent lists subfolders → sends __CHECKBOX_SELECT__ OR advances if no subs
    _got_checkbox = (imsg5 or "").startswith("__CHECKBOX_SELECT__")
    _got_subfolder = iid5 == "subfolder_selections"
    _got_next_step = iid5 in ("subfolder_selections", "user_pin")
    check("Step-2 advances the flow", _got_next_step, f"got iid={iid5!r}")
    check("Step-2 prompt non-empty",  bool(imsg5))
    if _got_subfolder and _got_checkbox:
        print("     → checkbox widget sent (subfolders found)")
    elif iid5 == "user_pin":
        print("     → no subfolders in test dir, skipped to PIN step")
    print(f"     interrupt_id  : {iid5!r}")
    print(f"     prompt preview: {repr((imsg5 or '')[:100])}")
else:
    check("Step-2 (skipped, step-4 failed)", False, "no interrupt from step 4")
    check("Step-2 prompt non-empty", False)

# ── 6. sessions API ────────────────────────────────────────────────────────
print()
print("[ 6 ] SESSIONS API")
try:
    r = urllib.request.urlopen(
        urllib.request.Request(
            f"{BASE}/apps/{APP}/users/{USER}/sessions",
            headers={"Content-Type": "application/json"},
        )
    )
    sessions = json.loads(r.read())
    check("Sessions endpoint returns list",  isinstance(sessions, list))
    check("At least 2 sessions exist",       len(sessions) >= 2, f"count={len(sessions)}")
except Exception as e:
    check("Sessions API reachable", False, str(e))
    check("Sessions list returned", False)

# ── summary ────────────────────────────────────────────────────────────────
print()
print("══════════════════════════════════════════════════════")
pct = int(100 * passed / total) if total else 0
result_sym = "🟢 PASS" if passed == total else ("🟡 PARTIAL" if passed > total // 2 else "🔴 FAIL")
print(f"  {result_sym}   {passed}/{total} checks passed  ({pct}%)")
print("══════════════════════════════════════════════════════")
sys.exit(0 if passed == total else 1)
