# SAYDI Narration Preprocess V3

## Purpose

Convert extracted book text into a listener-oriented narration manifest before TTS.

## Input layers

- immutable source/extracted text;
- chapter/page provenance;
- book profile;
- approved narrator fingerprint.

## Output layers

For every semantic block:

```json
{
  "block_id": "...",
  "chapter_number": 1,
  "block_type": "SECTION_HEADING",
  "original_text": "...",
  "normalized_text": "...",
  "spoken_text": "...",
  "narration": {
    "emotion": "authoritative",
    "pace": "slow",
    "energy": "medium_high",
    "pause_before_ms": 700,
    "pause_after_ms": 1100,
    "emphasis": true,
    "confidence": 0.98,
    "review_required": false
  }
}
```

## Cleanup rules

Safe deterministic cleanup may remove:

- standalone page numbers;
- repeated page headers/footers;
- extraction control characters;
- duplicated whitespace;
- line-wrap artifacts;
- duplicated heading fragments caused by PDF layout.

Do not silently remove meaningful annotations, footnotes, citations, quotations, list content, captions with semantic meaning, or author/editor notes.

## Structure reconstruction

Detect at minimum:

- CHAPTER_TITLE
- SECTION_HEADING
- SUBSECTION_HEADING
- NARRATOR_BODY
- DIALOGUE
- QUOTE
- LIST_ITEM
- TRANSITION
- REFLECTIVE
- EXPLANATORY
- EMPHATIC
- ANNOTATION

## Heading policy

Heading audio is a navigation landmark.

Defaults:

| Type | Pause before | Pause after | Delivery |
|---|---:|---:|---|
| Chapter title | 800-1200 ms | 1200-1800 ms | independent segment, slower, prominent |
| Section heading | 500-900 ms | 800-1400 ms | independent segment, prominent |
| Subsection heading | 400-700 ms | 600-1000 ms | independent segment |
| Paragraph | 250-500 ms | provider-natural | normal narration |

Never combine heading and first body paragraph in one TTS segment.

## Segmentation

Segmentation priority:

1. semantic block boundary;
2. paragraph boundary;
3. complete sentence boundary;
4. punctuation-aware fallback only if a segment exceeds provider/model constraints.

Character count is a safety limit, not the primary segmentation rule.

## Expression/prosody

Narration metadata is provider-neutral.

When a provider exposes a verified control, map it directly.
When it does not, approximate only with validated mechanisms:

- separate segment rendering;
- punctuation;
- pause insertion;
- supported speed/profile controls;
- approved voice/reference settings.

Never invent unsupported emotion/style parameters.

## Preview gate

Before a full-book production rerender:

1. preprocess Chapter 1;
2. show/record cleaned spoken-text structure;
3. render representative audio including at least one chapter title and one section heading;
4. owner listens;
5. only after approval may the full book be regenerated with the same narration policy.

## Acceptance

A production chapter is FINAL only when:

- preprocessing manifest exists;
- no unresolved low-confidence cleanup/structure issue exists;
- heading treatment is present;
- approved narration fingerprint is used;
- TTS generation completes;
- acoustic/coverage/ASR QC gates pass or reviewed exceptions are accepted.
