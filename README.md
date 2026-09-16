# MAGASIN Media Robot

Desktop-first automation project for turning **source video + content** into a finished social video with minimal manual work.

## End-user target

The daily workflow should become:

`Select source videos -> enter content -> click CREATE VIDEO -> receive final MP4`

The system will coordinate SaydiVoice in a browser for TTS, local media analysis, scene planning, subtitle timing, FFmpeg rendering, QA, diagnostics, resume, and a simple Windows desktop control center.

## Project phases

1. **SaydiVoice Discovery** — map the real browser UI, settings, login/session behavior, voice selection, generation states, download behavior, errors, and robust selectors.
2. **Voice Engine** — reliable SaydiVoice automation with session persistence, retries, validation, and downloaded audio handoff.
3. **Media Analyzer** — inspect video metadata and source material.
4. **Scene Planner** — convert content + available footage into a deterministic edit plan.
5. **Subtitle Engine** — timed subtitles aligned to generated voice.
6. **Video Composer / Render Engine** — FFmpeg-based editing, audio mixing, overlays, branding, transitions, and export.
7. **Desktop Control Center** — simple Windows UI.
8. **QA / Diagnostics / Resume** — self-test, bug detection, logs, recovery, and regression testing.
9. **Installer** — one-time Windows setup and Desktop shortcut.

## Source of truth for continuation

Every work session must begin by reading:

- `00_PROJECT/CURRENT_STATUS.md`
- `00_PROJECT/NEXT_STEP.md`
- `00_PROJECT/DECISIONS.md`
- `00_PROJECT/BUG_LOG.md`
- `00_PROJECT/TEST_LOG.md`
- `00_PROJECT/CHANGELOG.md`

Every work session must end by updating the same records.

The intended continuation request is:

> **Tiếp tục dự án magasin-media-robot**

That request means: read the repository state first, continue from the recorded next step, test the work, record failures/fixes/tests, and update the next step before stopping.

## Security

Never commit passwords, browser cookies, auth tokens, local browser profiles, downloaded private media, production secrets, or user-specific configuration. Runtime secrets and sessions stay local on the user's machine.

## Current focus

**Phase 0 — SaydiVoice Discovery architecture and discovery runner.**
