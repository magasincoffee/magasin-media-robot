# SAYDI Audiobook

Local-first Windows automation for turning a legally usable manuscript into a professionally structured audiobook with resumable TTS generation, audio processing, QA and export.

> Repository name remains `magasin-media-robot` for continuity, but the active product track is **SAYDI Audiobook**.

## End-user target

```text
Import book
 -> review chapters
 -> choose narrator/style
 -> approve a sample
 -> create audiobook
 -> review/repair exceptions
 -> export M4B or chapter MP3
```

Normal operation should not require knowledge of Python, Playwright, FFmpeg, browser profiles, segment IDs or state databases.

## Architecture

```text
BOOK
 -> Ingest / Canonical Manifest
 -> Text Normalization / Segmentation
 -> Narration Director
 -> Segment Orchestrator
 -> Voice Engine (SaydiVoice first)
 -> Audio Engine
 -> Alignment + Acoustic QA
 -> Export Engine
 -> M4B / MP3
```

## Existing foundation

`01_DISCOVERY/saydivoice` already contains field-verified work for:

- authenticated Chrome/Playwright automation;
- voice and style controls;
- controlled generation;
- download behavior;
- privacy-safe evidence.

That foundation is reused. It is not being rebuilt from zero.

## Source of Truth

For any continuation, read:

**`00_PROJECT/SOURCE_OF_TRUTH.md`**

It is the single authoritative project state and task queue.

Supporting documents:

- `00_PROJECT/ARCHITECTURE.md`
- `00_PROJECT/AUDIOBOOK_DATA_CONTRACTS.md`
- `00_PROJECT/DECISIONS.md`
- `00_PROJECT/QA_STRATEGY.md`
- `00_PROJECT/DEVELOPMENT_RULES.md`

Historical notes remain useful evidence but do not override the Source of Truth.

## Current task

**NEXT: SAYDI-002 — Production SaydiVoice provider adapter.**

## Security / privacy

Never commit source books, generated private audio, browser profiles, cookies, credentials, local production databases or private diagnostic content.

## Rights

Use SAYDI only for works you own, are licensed to reproduce, or that are otherwise legally usable for the intended audiobook production.
