# Next Step

## Immediate next step — D3 Generation Lifecycle V0.4.1 recovery field run

The first real V0.4.0 D3 run reached processing, then SaydiVoice returned `Không tải được giọng. Vui lòng tải lại trang.` with quota unchanged. D3 therefore needs one controlled reload-recovery run before merge.

### What V0.4.1 changes

- detects `Hủy/Cancel` or Generate disappearance as a processing signal;
- waits best-effort for network idle before each attempt;
- attempt 1 remains a fixed short non-sensitive test sentence;
- when and only when attempt 1 returns a provider error explicitly asking to reload, the robot reloads the disposable same-session page and makes exactly one second attempt;
- a second attempt never occurs for unrelated errors;
- saves per-attempt traces/screenshots plus the final lifecycle analysis;
- never clicks a download control;
- never persists editor content, only fixed-sample length/SHA-256.

### Operator sequence

1. Extract `MAGASIN_SAYDIVOICE_DISCOVERY_V0.4.1.zip` to a new folder.
2. Run `CAI_DAT_VA_CHAY_D3.bat`.
3. Read the warning: this run may use up to two generation attempts; attempt 2 occurs only after the reload-page error.
4. Press `Y` to authorize the controlled recovery test.
5. Do not interact with the SaydiVoice window while the robot runs.
6. Return the newest same-run artifacts:
   - `runs\<run-id>\generation_lifecycle.json`
   - all `runs\<run-id>\d3_attempt*_before.png`
   - all `runs\<run-id>\d3_attempt*_after.png`
   - `runs\<run-id>\d3_before_generate.png`
   - `runs\<run-id>\d3_after_generate.png`
   - `reports\discovery_report_<run-id>.json`
   - `logs\discovery_<run-id>.jsonl`
7. Never send `browser_profile`.

### D3 acceptance gate

Merge PR #8 when:
- processing is correctly recognized;
- retry occurs only after the explicit reload-page error;
- preferably attempt 2 reaches a concrete success signal (quota decrement, new result control, or new audio evidence);
- if the same provider error repeats after reload, the evidence is sufficient to classify generation as provider/login availability blocked rather than an automation-lifecycle ambiguity;
- no download occurs;
- no script/editor content is persisted;
- D1/D2 evidence remains valid.

## After D3 — D4 Audio Download Lifecycle

D4 starts only after a successful generated result exists. It will characterize the real result-player/download control, browser download event, filename/extension, completion/error behavior, and safe destination handling. D4 will require its own explicit operator authorization for one audio download.
