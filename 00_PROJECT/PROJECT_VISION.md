# Project Vision

## Product goal

Build a reliable Windows desktop robot that reduces video production to two primary user inputs:

1. source videos/images;
2. content/script.

The system should return a finished MP4 suitable for social publishing, with voice-over, subtitles, music, branding, scene timing, and quality checks handled automatically.

## Primary UX

The user should not need to understand Python, Playwright, FFmpeg, codecs, subtitle timing, browser profiles, or project directories. Daily operation should happen through one desktop application.

## Core design principles

- **Local-first media processing:** rendering and media transformation run locally where practical.
- **Browser automation only where necessary:** SaydiVoice TTS is browser-driven; rendering must not depend on GUI macro clicking in a video editor.
- **Deterministic before intelligent:** stable templates and explicit rules come before AI scene selection.
- **Observable:** every significant step produces status and logs.
- **Resumable:** recoverable failures should continue from the last safe checkpoint.
- **Testable:** modules expose verifiable inputs/outputs and regression tests.
- **Secure by default:** credentials, sessions, cookies, tokens, and private media are never committed to GitHub.
- **Replaceable integrations:** SaydiVoice, subtitle timing, and other external providers are adapters, not hard-wired into the project core.

## Definition of project completion

A production-ready version is complete when a clean Windows machine can install the product through the supported installer, complete the one-time SaydiVoice login/setup, select source media, enter content, create a final MP4, recover from common failures, and produce diagnostic evidence when it cannot recover automatically.
