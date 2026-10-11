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
 -> Voice Engine (VieNeu local ONLY; legacy SaydiVoice retired)
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

This is retired historical evidence only. SAYDI production does **not** use SaydiVoice Chrome, paid quota, cloud provider or any SaydiVoice generation task.

## Source of Truth

For any continuation, read:

**`00_PROJECT/SOURCE_OF_TRUTH.md`**

It is the **only** authoritative Owner-policy, V6 24-step roadmap and task queue. The former three temporary Sources of Truth, separate implementation/status trackers, README and historic branch/PR notes are **not task authority**; never select a NEXT task from them.

Supporting documents:

- `00_PROJECT/ARCHITECTURE.md`
- `00_PROJECT/AUDIOBOOK_DATA_CONTRACTS.md`
- `00_PROJECT/DECISIONS.md`
- `00_PROJECT/QA_STRATEGY.md`
- `00_PROJECT/DEVELOPMENT_RULES.md`

Historical notes remain useful evidence but do not override the Source of Truth.

## Current task

**NEXT: SAYDI-002 — Executable vertical slice + provider/AI contracts. Active authorized subtask: SAYDI002-VN-001 IN_PROGRESS.** Only the canonical SOT on `main` can change this.

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

VieNeu ONNX is the sole active local TTS. Retired SaydiVoice is **not selectable or runnable**. Cloud LLMs are disabled by default and require explicit Owner authorization.

## Development method

SAYDI is built as runnable vertical slices. The first implementation must reach a real audible sample and approval state through a CLI/operator runner before the project scales to full-book generation.
