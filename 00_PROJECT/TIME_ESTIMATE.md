# Remaining Time Estimate

Last recalculated: 2026-09-17 after D2 field acceptance/merge and D3 V0.4.0 implementation.

This is a planning estimate, not a fixed delivery promise. One engineering workbox is capped at **28 minutes** and stops earlier at an operator/provider gate.

## Current position

- D0 Discovery Runner: complete.
- D1 Surface Map: complete and merged.
- D2 Voice/Settings Catalog: complete, field-verified, merged.
- D3 Generation Lifecycle: code/CI/package complete; one real controlled generation + review remains.
- D4–D6: not yet complete.
- Production media pipeline modules: not yet built.

## Estimated remaining work

| Stage | Estimated workboxes | Active engineering time |
| --- | ---: | ---: |
| D3 field review/fix/merge | 1–2 | 28–56 min |
| D4 Audio download lifecycle | 2 | ~56 min |
| D5 Limits/error characterization | 2–3 | 56–84 min |
| D6 Freeze discovery contracts | 1 | ~28 min |
| Production Voice Engine | 3 | ~84 min |
| Media Analyzer | 4 | ~112 min |
| Scene Planner | 5 | ~140 min |
| Subtitle/Timing Engine | 3 | ~84 min |
| Video Composer + FFmpeg Render | 5 | ~140 min |
| Desktop Control Center | 4 | ~112 min |
| QA + resume + diagnostics | 4 | ~112 min |
| Installer + final regression | 3 | ~84 min |
| Contingency/provider/media changes | 5–10 | 140–280 min |

## Totals from current point

- **Finish SaydiVoice discovery D3–D6:** approximately **3–4 active engineering hours**, plus short operator field runs.
- **First end-to-end usable MVP (video + content → rendered video):** approximately **12–15 active engineering hours** from the current point.
- **Full V1 with desktop UX, diagnostics/resume, installer and regression hardening:** approximately **17–23 active engineering hours** from the current point.

At roughly 6 productive engineering hours/day with fast operator responses, the current planning range remains about **3–4 working days** for Full V1. Provider UI changes, generation quotas/login requirements, media edge cases, or FFmpeg/Windows packaging defects can extend it.

## Time-control rule

1. read `CURRENT_STATUS.md`, `NEXT_STEP.md`, bug/test/session logs;
2. start one <=28-minute workbox;
3. implement → self-test → log defects → fix → regression-test;
4. stop at 28 minutes or earlier at an operator gate;
5. update durable logs and next step before reporting.
