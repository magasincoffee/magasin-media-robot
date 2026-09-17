# Next Step

## Immediate next step — D3 Generation Lifecycle V0.4.0 field run

D2 is complete and merged. D3 is now the active gate.

### What D3 V0.4.0 does

- requires explicit `--allow-generate` authorization;
- opens a disposable tab in the same SaydiVoice session;
- inserts one fixed short non-sensitive test sentence;
- clicks `Tạo giọng nói` exactly once;
- observes Generate busy/disabled state, quota text, audio/result controls, and new alert/toast messages;
- saves only structural lifecycle evidence plus fixed-sample length/SHA-256;
- does **not** click any download control;
- closes the disposable tab after observation.

### Operator sequence

1. Extract `MAGASIN_SAYDIVOICE_DISCOVERY_V0.4.0.zip` to a new folder.
2. Run `CAI_DAT_VA_CHAY_D3.bat`.
3. Read the warning that the test may consume one provider generation/quota unit.
4. Press `Y` to authorize one controlled generation.
5. Do not interact with the SaydiVoice window while the robot runs.
6. When it finishes, return five same-run artifacts:
   - `runs\<run-id>\generation_lifecycle.json`
   - `runs\<run-id>\d3_before_generate.png`
   - `runs\<run-id>\d3_after_generate.png`
   - `reports\discovery_report_<run-id>.json`
   - `logs\discovery_<run-id>.jsonl`
7. Never send `browser_profile`.

### D3 acceptance gate

Merge PR #8 when:
- exactly one controlled Generate action occurred;
- trace records processing or another concrete lifecycle transition;
- terminal evidence is classified as success signal, provider error, or explicit timeout/no-signal rather than guessed;
- a pre-existing provider toast is not treated as a new generation error;
- no audio download action occurred;
- no script/editor content is persisted in structured evidence;
- original D1/D2 evidence remains valid.

## After D3 — D4 Audio Download Lifecycle

After D3 merge, characterize the real result-player/download control, browser download event, file naming, output extension, completion/error behavior, and safe destination handling. D4 may download exactly one audio result only after its own explicit operator gate.
