# SAYDI VN-001 — Secure MCP Tunnel source-only deployment runbook
Date: 2026-10-12 (Asia/Ho_Chi_Minh)
Authority: **00_PROJECT/SOURCE_OF_TRUTH.md** on `main` — this file provides operational instructions ONLY, not a second SOT or executable task queue.
Current state: SOURCE/QA candidate. **H4 install, tunnel activation, ChatGPT plugin registration, and actual V5 field inventory are NOT DONE.**

## Selected transport

Use OpenAI **Secure MCP Tunnel** for an outbound-only private connection. Do not open H4 firewall/router inbound ports, use anonymous public Cloudflare quick tunnels, publish an unauthenticated raw shell MCP, or write secrets to GitHub. Reuse H4 and the SOT-gated `SAYDI002-VN-001` read-only inventory tool. No paid voice inference API replaces VieNeu. The tunnel itself requires a Platform tunnel ID and a **runtime API key** for transport authentication; this is not automatically cost-free and must not be confused with VieNeu narration usage.

Official current instructions:
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://platform.openai.com/ (Tunnels settings, account permissions)

### Stage A — prerequisites / no local writes

1. From an independently authenticated H4 channel, inspect whether existing local MCP already provides a compatible **stdio** or HTTP MCP endpoint; do not assume `C:\MAGASIN_MCP\dispatch_gateway.py` is a general-purpose/qualified tool endpoint.
2. Verify host is exactly `DESKTOP-H4A16IL`; record H4 Owner STOP/AUTOSTART_DISABLED and specialist flags with read-only evidence. **STOP stays ON and no Supervisor production task switch is allowed.**
3. Inspect SHA of installed scripts and local roots for voice/reference/checkpoint/audio. Only bind verified `C:\SAYDI\...` or `D:\SAYDI\...` directories; do not scan arbitrary user files, any old 4K7 machine, or send source manuscript/audio to GitHub.
4. Independently confirm the canonical SAYDI SOT has `SAYDI-002 = NEXT` and `SAYDI002-VN-001 = IN_PROGRESS`. The verifier module fetches live `main` twice and refuses a stale exact commit.

### Stage B — private tunnel, after separate Owner credentials/role and deployment approval

1. In **OpenAI Platform Tunnels settings**, Owner creates or selects a tunnel, associates it to the correct ChatGPT workspace, and provides `tunnel-client` runtime key through the platform credential channel **only**, never through ChatGPT messages, PRs, shell history, a tracked `.env`, or Control Center UI.
2. Download the current official `openai/tunnel-client` release on H4 and verify source/signature using the official distribution workflow. **Do not automatically download or execute from a GitHub commit**.
3. For one explicitly reviewed *manual test*, configure `tunnel-client` using the official CLI, with a private `--mcp-command` pointing at the reviewed Python stdio tool:
   `python -u <verified-absolute-path>\tools\saydi_tts\qc\vn001_private_mcp_stdio.py`
   This process is only an MCP JSON-RPC stdio endpoint, not VieNeu or Whisper. It exposes exactly `saydi_vn001_inventory_readonly`.
4. The stdio endpoint reads the **H4-admin-controlled** `SAYDI_VN001_ROOTS_JSON` process-environment variable. Example for an existing Owner-verified audio folder only (EXAMPLE, not a known real H4 location):
   `{"chapter2":{"scope":"audio","path":"C:\\SAYDI\\output\\<VERIFIED_CHAPTER2_FOLDER>"}}`
   It must be injected locally by the approved operator, not by the ChatGPT client. The bridge rejects any path outside `C:\SAYDI` and `D:\SAYDI` after canonical resolution.
5. Run `tunnel-client doctor --profile <owner-approved-profile> --explain` first. Run `tunnel-client run --profile <owner-approved-profile>` only for the manually approved bounded acceptance session. Client reaches OpenAI through outbound `api.openai.com:443`. Do **not** create autostart, a Windows service, a scheduler, or a persistent 24/7 business dispatcher at this gate.

### Stage C — ChatGPT connection, after transport PASS

1. From **ChatGPT on the web**, go to **Plugins → Add custom MCP server → Connection: Tunnel**, choose the previously approved `tunnel_id`, set appropriate authentication, review risk, create and install. Creation availability depends on account/workspace settings and tunnel permissions. The Owner must finish any account authorization in the official web UI; never relay a Platform API key to chat.
2. Discover exactly **one** tool: `saydi_vn001_inventory_readonly`. Refuse creation if any shell/write/START/STOP or generic gateway tools appear.
3. Start with a single `metadata` inventory call. Send the expected current GitHub main commit SHA, fixed TASK_ID, target and locally configured `root_key`. The server verifies the same commit still on `main` before reading. A changed main produces a safe BLOCKED reply; renew only from fresh authoritative SOT.
4. If metadata receipt is safe and Worker/STOP checks independently remain safe, perform bounded SHA batches (`hash_offset` + `expected_metadata_sha256`). Never treat a final hash page alone as evidence of total approved narrator/worker ownership.
5. Review authenticated mobile ChatGPT availability **on the exact account** separately; custom app authoring starts from web. A local-only plugin is not implicitly accessible from mobile, and the tunnel does not itself guarantee iOS support.
6. Upload only sanitized aggregate evidence/PR links to the canonical SAYDI SOT, not filename lists/manuscripts/audio/credentials.

### Deny, rollback, and owner gates

- No login/key/tunnel ID available? **STOP, not activated**.
- H4 Offline or local MCP transport unverified? **STOP, not activated**.
- Root outside C:/SAYDI or D:/SAYDI, unknown reparse point, stale/changed SOT, wrong TASK_ID? **BLOCKED**, no worker.
- Supervisor SC-013 P1/P2/P3 and specialist START/STOP gates remain separate. This read-only tool DOES NOT turn business dispatch on, clear STOP, or authorize rerender.
- Rollback of this source-only candidate is removal/disablement of the private plugin and tunnel test profile; no V5 data, checkpoint or production worker requires rollback because none are changed.
- Do not mark `SAYDI002-VN-001` or step 1.1 DONE until actual H4 root provenance, narrator/hash inventory and worker/STOP ownership are independently verified.

## Current verified evidence

At creation, Desktop Commander listed H4 **Offline** (last seen about four hours earlier), and no independent existing H4 MCP tool appeared in this ChatGPT tool list. New stdio module and tests are **source-only**. This runbook is not evidence of a live tunnel, authenticated plugin, or accepted 640 WAV checkpoints.
