# SAYDI Audiobook Data Contracts

This document defines the minimum stable domain contracts. Exact JSON Schema files are implemented in later tasks, but implementations must preserve these semantics.

## 1. BookManifest.v1

Required conceptual fields:

```text
schema_version
book_id
source:
  source_type
  original_filename
  source_sha256
  imported_at
metadata:
  title
  author
  language
chapters[]:
  chapter_id
  ordinal
  title
  blocks[]:
    block_id
    block_type
    ordinal
    original_text
    source_locator
manifest_sha256
```

The manifest preserves original extracted text. Spoken normalization is not written over the source text.

## 2. SpokenSegment.v1

```text
schema_version
segment_id
book_id
chapter_id
block_id
ordinal
original_text
spoken_text
normalization_version
content_sha256
pronunciation_keys[]
narration_directive_id
```

`content_sha256` represents the exact spoken content plus normalization version needed for dependency invalidation.

## 3. NarrationProfile.v1

```text
schema_version
profile_id
provider_key
voice_key
style_key
speed
expression
pause_policy
output_format
pronunciation_lexicon_version
fingerprint
```

The fingerprint is stable for equivalent narration behavior and is part of cache/reuse decisions.

## 4. VoiceRequest.v1

```text
operation_id
segment_id
text
narration_fingerprint
voice_key
style_key
provider_controls
output_format
output_directory
```

Provider-specific controls may exist inside the provider adapter payload but must not become required fields in audiobook-domain objects.

## 5. VoiceResult.v1

```text
operation_id
segment_id
status
provider
provider_voice
local_audio_path
audio_sha256
byte_count
duration_ms
provider_reference
attempt
error_class
retryable
created_at
```

An accepted result is immutable. Regeneration creates a new attempt/result record and changes acceptance explicitly.

## 6. SegmentQA.v1

```text
segment_id
audio_sha256
attempt
structural_status
alignment_status
alignment_confidence
pronunciation_status
pronunciation_min_word_confidence
unclear_tokens[]
prosody_status
speaking_rate_wpm
pause_ratio
pitch_variation_semitones
energy_variation_db
material_mismatch
acoustic_status
duration_ms
silence_findings[]
clipping_finding
repair_actions[]
review_required
accepted
notes
```

QA results are attached to the exact audio hash they evaluated. Pronunciation/prosody repair metadata is evidence, not permission to rewrite canonical source text. Spoken-form overrides must remain a separate versioned layer.

## 7. ChapterManifest.v1

```text
chapter_id
ordered_segment_audio[]
pause_policy_version
processing_profile_version
chapter_audio_path
chapter_audio_sha256
duration_ms
qa_status
```

## 8. ExportManifest.v1

```text
book_id
book_manifest_sha256
narration_fingerprint
chapter_manifest_hashes[]
qa_report_sha256
export_profile
artifacts[]:
  type
  path
  sha256
  byte_count
  duration_ms
created_at
```

## 9. Job state

The state database must separate:

- desired work;
- current execution lease;
- provider operation attempt;
- artifact creation;
- artifact acceptance;
- QA status;
- human approval.

A file existing on disk is not sufficient evidence that a job is complete.

## 10. Invalidation rules

At minimum:

- source structural change invalidates dependent manifest/segments;
- spoken-text change invalidates that segment's synthesis, processing, chapter assembly, QA and export;
- narration-fingerprint change invalidates sample approval and all synthesis using the old fingerprint;
- audio-processing-profile change preserves raw voice audio but invalidates processed/chapter/export artifacts;
- export-profile change invalidates export only;
- QA algorithm-version change invalidates QA acceptance but does not automatically regenerate audio.

These rules are fundamental to fast, safe long-form iteration.
