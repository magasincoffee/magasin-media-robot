# Remaining Time Estimate

Last recalculated: 2026-09-17 after V0.3.1 real-provider review and V0.3.2 corrective build.

This is a planning estimate, not a fixed delivery promise. One engineering workbox is capped at **28 minutes**. A workbox stops earlier when the next step requires an operator/provider interaction.

## Current position

- D0 Discovery Runner: complete.
- D1 Surface Map: complete and merged.
- D2 Voice/Settings Catalog: code/CI complete through V0.3.2; one final real-provider verification remains.
- D3–D6: not yet complete.
- Production media pipeline modules: not yet built.

## Estimated remaining work

| Stage | Estimated workboxes | Active engineering time |
| --- | ---: | ---: |
| D2 final field review + merge | 1 | <= 28 min |
| D3 Generate lifecycle | 2–3 | 56–84 min |
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
| Contingency/provider changes | 5–10 | 140–280 min |

## Totals from current point

- **Discovery complete (D2–D6):** about **4–5 active engineering hours**, plus several short operator field runs.
- **First end-to-end usable MVP (video + content → rendered video):** about **13–16 active engineering hours** from the current point.
- **Full V1 with desktop UX, diagnostics/resume, installer and regression hardening:** about **18–24 active engineering hours** from the current point.

If operator gates are answered promptly and work continues for roughly 6 productive engineering hours per day, the full V1 planning range is approximately **3–4 working days**. Provider UI changes, generation quotas/login requirements, media edge cases, or FFmpeg/Windows packaging defects can extend that range.

## Time-control rule

For every requested continuation:

1. read `CURRENT_STATUS.md`, `NEXT_STEP.md`, bug/test/session logs;
2. start one <=28-minute workbox;
3. implement → self-test → log defects → fix → regression-test;
4. stop at 28 minutes or earlier at an operator gate;
5. update durable logs and next step before reporting.
