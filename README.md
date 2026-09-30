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
 -> Rule Engine + Local LLM Intelligence
 -> Narration Director / Voice Casting
 -> Text Preview + Audio Sample Approval
 -> Segment Orchestrator
 -> Voice Engine (Local TTS + optional SaydiVoice)
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

**NEXT: SAYDI-002 — Executable vertical slice + provider/AI contracts.**

## Security / privacy

Never commit source books, generated private audio, browser profiles, cookies, credentials, local production databases or private diagnostic content.

## Rights

Use SAYDI only for works you own, are licensed to reproduce, or that are otherwise legally usable for the intended audiobook production.


## Local-first intelligence and cost model

The architecture does not require ChatGPT or another paid API.

Default target:

```text
Rules + Local LLM + Local TTS + FFmpeg + SQLite
```

SaydiVoice and cloud LLMs remain optional adapters.

## Development method

SAYDI is built as runnable vertical slices. The first implementation must reach a real audible sample and approval state through a CLI/operator runner before the project scales to full-book generation.
