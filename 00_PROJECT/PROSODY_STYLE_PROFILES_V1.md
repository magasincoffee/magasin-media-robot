# SAYDI Prosody / Style Profiles v1

Status: IMPLEMENTED
Version: `prosody-profile-v1`

Purpose: define deterministic, provider-neutral QC envelopes for long-form audiobook delivery. These values are QC acceptance ranges, not claims about universal human narration.

## Profiles

| Profile | Intended use | WPM | Pause ratio | Pitch variation (semitones) | Energy variation (dB) |
|---|---|---:|---:|---:|---:|
| `BUSINESS_CLEAR` | business, management, practical non-fiction | 120–180 | 0.06–0.28 | 0.65–4.8 | 1.5–12.0 |
| `STORY_NARRATIVE` | fiction / story / expressive narration | 95–165 | 0.08–0.36 | 1.00–6.5 | 2.0–15.0 |
| `GENERAL_CLEAR` | neutral/general narration | 110–175 | 0.06–0.32 | 0.75–5.5 | 1.5–13.0 |

These are versioned starting envelopes. Field evidence may tune them later, but any threshold change produces a new profile fingerprint and invalidates prior QC acceptance for that profile.

## Owner-facing style mapping

Simple Owner requests are mapped deterministically:

- business / kinh doanh / quản trị / chuyên nghiệp / rõ ràng -> `BUSINESS_CLEAR`
- story / fiction / truyện / kể chuyện / cảm xúc -> `STORY_NARRATIVE`
- general / tổng quát / trung tính / neutral -> `GENERAL_CLEAR`

If the Owner request is unknown, SAYDI falls back to the analyzed `BookProfile`; if no usable book profile exists, it uses `GENERAL_CLEAR`.

CLI example:

```powershell
saydi-audiobook profile-resolve --style "sách kinh doanh rõ ràng"
```

The output includes the selected profile, envelope version and immutable profile fingerprint.

## Provider-safe rule

Semantic intent and QC profile are provider-neutral. Provider controls are filtered through a verified whitelist.

Current verified control surfaces:

### VieNeu local

Allowed:

- segmentation
- punctuation
- pause insertion
- voice reference

Not claimed:

- discrete emotion selector
- mood selector
- arbitrary prosody parameter
- direct speed control unless separately field-verified

### SaydiVoice

Allowed by current adapter contract:

- voice
- stability/expression axis
- speed
- pause enabled
- output format

Unsupported semantic controls such as `emotion`, `mood` and arbitrary `prosody` are rejected rather than fabricated.

## QC behavior

Each chunk stores:

- active prosody profile key;
- profile version;
- profile fingerprint;
- speaking rate;
- pause ratio;
- pitch variation;
- energy variation;
- exact reasons when outside the profile envelope.

Possible reasons include:

- `pace_too_fast`
- `pace_too_slow`
- `insufficient_pauses`
- `excessive_pauses`
- `flat_intonation`
- `excessive_pitch_variation`
- `flat_dynamics`
- `excessive_dynamics`

A QC acceptance is valid only for the exact profile fingerprint that produced it.
