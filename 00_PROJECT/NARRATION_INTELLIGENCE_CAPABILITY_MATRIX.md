# SAYDI Narration Intelligence Capability Matrix

Last updated: 2026-10-05

Purpose: this file is the durable checklist for the audiobook intelligence/narration architecture. It shows what already exists, what is partial, and what is still missing. New capabilities can be appended here without losing sight of the target architecture.

> Authority note: task ordering remains controlled by `00_PROJECT/SOURCE_OF_TRUTH.md`. This matrix is a capability/status registry, not a replacement task queue.

## Status legend

- ✅ **AVAILABLE** — implemented and supported by concrete code/evidence.
- 🟡 **PARTIAL / BUILDING** — architecture, contract, prototype, PR, or limited implementation exists but the production path is not complete.
- ❌ **MISSING** — required target capability is not implemented yet.
- 🔒 **LOCKED** — architecture/behavior is an Owner-approved invariant and must be preserved.

## Owner experience target

The intended final interaction is:

```text
Owner supplies a legally usable book
  -> optionally says narrator/accent/style preference
  -> SAYDI understands the book
  -> SAYDI chooses and plans delivery
  -> SAYDI generates a representative preview
  -> Owner approves the overall narration fingerprint
  -> SAYDI performs full synthesis
  -> SAYDI listens/checks pronunciation + prosody + acoustic quality
  -> SAYDI repairs safe isolated defects automatically
  -> Owner sees only genuine semantic/quality exceptions
  -> validated audiobook export
```

## Capability checklist

| Capability | Current status | Current evidence / limitation | Target behavior |
|---|---|---|---|
| Historical V4↔V5 editorial drift triage (review-only) | 🟡 PARTIAL | PR #101 adds offline opt-in privacy-safe classified review queue (diacritics/words/boundaries), pagination and synthetic 16/16 sandbox smoke 2026-10-11; **not** original-source proofreading, host or CI acceptance | Run on actual H4 manifest after power returns, reconcile against original text and independent reviewer, then integrate only behind existing SOT gates |
| SHA-bound manuscript-to-segment lexical provenance (V5 pilot) | 🟡 PARTIAL | PR #101 opt-in source-lineage audit checks UTF-8 source hash, ordered words, accents and punctuation; synthetic tests added 2026-10-11, host + CI verification pending; default OFF | Verify on H4 against original local chapter text, resolve provenance and legacy paraphrase exceptions before pre-render gate may pass |
| Local VieNeu v3 Turbo production TTS | ✅ AVAILABLE | Field-used on Windows local worker | Remains default all-local TTS path |
| Approved Southern male narrator profile | ✅ AVAILABLE | `SAYDI Nam Mien Nam` active local voice | Narrator identity remains stable across a book unless Owner changes it |
| Automatic local worker / resume / checkpoints | ✅ AVAILABLE | Windows worker, durable queue/checkpoints and chapter assembly are field-used | Fully unattended normal operation |
| Book genre classification | ✅ AVAILABLE | Rule-based classifier + `AnalysisProvider` | Expand taxonomy without coupling to TTS |
| Local LLM analysis boundary | ✅ AVAILABLE | Ollama `AnalysisProvider` interface exists | Local semantic analysis remains default; cloud optional |
| Whole-book style/tone understanding | 🟡 PARTIAL | Current first slice can create `BOOK_PROFILE`; current Ollama implementation analyzes an excerpt rather than a hierarchical full-book pass | Hierarchical book -> chapter -> scene analysis over the complete canonical book |
| Narration profiles `BUSINESS_CLEAR / STORY_NARRATIVE / GENERAL_CLEAR` | ✅ AVAILABLE | QC-005 adds versioned `prosody-profile-v1` envelopes, Owner style mapping and fingerprints | Tune thresholds only with field evidence; fingerprint changes invalidate acceptance |
| Representative passages for preview | ✅ AVAILABLE | Current selector returns up to ~3 passages | Target 3–5 passages spanning normal prose, difficult terms, dialogue/emotion and edge cases |
| Text approval + audio sample approval | ✅ AVAILABLE | Workflow state supports both gates | Approval is tied to active narration fingerprint |
| Semantic block roles (heading/body/dialogue/quote/etc.) | 🟡 PARTIAL | Locked in SOT/architecture; production parser not complete | Every block gets a role + confidence |
| Scene segmentation | ❌ MISSING | No production scene model | Detect scenes/semantic regions across chapter context |
| Scene emotion classification | ❌ MISSING | No per-scene semantic emotion engine | `neutral/warm/joyful/sad/tense/urgent/reflective/mysterious/authoritative` + extensible vocabulary |
| Emotion intensity | ❌ MISSING | No production intensity score | Structured intensity, e.g. `sad=0.8`, with confidence |
| Contextual semantics / irony / mixed emotion | ❌ MISSING | Keyword rules are insufficient for cases such as “cười cay đắng” | Semantic context must override literal emotion keywords |
| Narrator vs dialogue vs speaker-role inference | ❌ MISSING | Domain requirement exists; no complete implementation | Infer speaker role when reliable; low-confidence cases go to review |
| Character continuity | ❌ MISSING | No persistent speaker/persona state | Preserve character/persona delivery across scenes without abrupt voice drift |
| Emotional arc across adjacent segments | ❌ MISSING | No smoothing/state transition model | Emotion should evolve smoothly across scene/paragraph boundaries |
| Segment delivery directives | 🟡 PARTIAL | Architecture defines pace/energy/pause/emphasis/emotion; no full production director | Every segment receives validated provider-neutral delivery metadata |
| Heading/title delivery policy | 🟡 PARTIAL | Architecture/SOT defines separate heading segments and pauses | Enforced in production narration manifest |
| Provider-safe mapping of emotion/prosody | ✅ AVAILABLE FOR PROFILE QC | QC-005 provider whitelist filters controls; VieNeu does not claim discrete emotion/mood/direct-speed controls without field evidence | Semantic intent remains provider-neutral; map only verified controls |
| ASR text similarity QC | ✅ AVAILABLE | Local QC currently produces similarity/warning/error evidence | Keep as one QC signal, not final acceptance by itself |
| Word-level pronunciation clarity / “lơ lớ” detection | 🟡 PARTIAL | Word-confidence + suspect-token measurement field-validated 24/24 chunks; automatic pronunciation repair is not built yet | Exact suspect token + confidence + timecode, then bounded repair |
| Vietnamese pronunciation lexicon / spoken-form overrides | ✅ AVAILABLE | QC-003 merged in PR #64 with versioned lexicon, conservative integer rules, explicit name/foreign-term entries, provenance and regression tests | Connect approved repair plans to targeted rerender in QC-004 |
| Prosody QC: speaking rate | ✅ PROFILE-AWARE | Field metric exists; QC-005 compares WPM against active versioned profile envelope | Profile-specific PASS/REVIEW |
| Prosody QC: pause/silence pattern | ✅ PROFILE-AWARE | Field metric exists; QC-005 compares pause ratio against active profile envelope | Detect insufficient/excessive pauses by profile |
| Prosody QC: pitch/intonation variation | ✅ PROFILE-AWARE | Field metric exists; QC-005 compares F0 variation against active profile envelope | Detect flat or excessive intonation by profile |
| Prosody QC: energy/dynamics | ✅ PROFILE-AWARE | Field metric exists; QC-005 compares dynamics against active profile envelope | Detect flat or excessive dynamics by profile |
| Acoustic QC / joins / clipping / silence | 🟡 PARTIAL | Existing QA architecture and some local checks; full unified gate still evolving | Default-on after synthesis and chapter assembly |
| Targeted automatic rerender | 🟡 CORRECT-HOST FIELD PENDING | QC-004 code merged and Supabase/Edge v7 deployed; automated runner reached DESKTOP-4K7IM13 and was safely blocked because authoritative TTS host is DESKTOP-H4A16IL | Run the one-command H4A16IL field gate; prove only the target chunk changes, then PASS/REVIEW |
| Bounded retry / no infinite rerender | 🔒 LOCKED | Owner-approved architecture; bounded policy merged in PR #60 | Retry-safe only; exhaustion -> REVIEW |
| Owner exception-only review | 🔒 LOCKED | SOT owner experience rule | Owner should not manually hunt defects |
| VieNeu end-to-end pronunciation/prosody field acceptance | 🟡 LOCAL + OWNER GATES PENDING | QC-006 synthetic fixtures/harness implemented; H4A16IL technical run and Owner BEFORE/AFTER listening remain | Prove localized defects, targeted rerender, bounded repair and final PASS/REVIEW on real local audio |
| Narration Director semantic beat planning | 🟡 FIELD PENDING | `narration-director-v1` implements semantic beats, provider-safe punctuation, scene-specific tempo/pause policy, canonical/spoken hashes and Golden Story V2 field path | Owner A/B acceptance required before production integration |
| Final “submit book and SAYDI handles narration” flow | ❌ NOT YET COMPLETE | Depends on scene intelligence, narration director and full QC/repair integration | Primary end-state for the product |

## Locked semantic narration architecture

```text
CANONICAL BOOK
    |
    v
BOOK INTELLIGENCE
genre / subgenre / audience / tone / narration identity
    |
    v
CHAPTER INTELLIGENCE
chapter purpose / local tone / continuity state
    |
    v
SCENE INTELLIGENCE
scene boundary / semantics / emotion / intensity / tension
    |
    v
SEGMENT INTELLIGENCE
speaker role / dialogue / emphasis / local meaning / confidence
    |
    v
EMOTIONAL ARC
smooth transition from preceding -> current -> following delivery state
    |
    v
DELIVERY DIRECTIVE
pace / energy / pauses / emphasis / expression / pronunciation hints
    |
    v
VOICE PROVIDER
VieNeu local default; provider adapter maps only supported controls
    |
    v
PRONUNCIATION QC
ASR + word clarity/alignment + suspect-token localization
    |
    v
PROSODY / STYLE QC
rate + pause + intonation + dynamics + active-profile envelope
    |
    v
ACOUSTIC / JOIN QC
    |
    +--> safe isolated repair -> rerender affected unit -> QC again
    |
    v
PASS / REVIEW
```

## Semantic rules that must not regress

1. **Context wins over keywords.** “Cười cay đắng” must not automatically become joyful because the word “cười” appears.
2. **Emotion is not binary.** Store emotion + intensity + confidence.
3. **Book identity is stable.** Do not change narrator/persona abruptly because one sentence is emotional.
4. **Scenes have continuity.** Adjacent segments receive a smoothed emotional arc, not independent random labels.
5. **Meaning is immutable.** Delivery optimization may alter derived `spoken_text`/punctuation hints, never silently rewrite canonical source meaning.
6. **Provider-neutral first.** Semantic intent is stored even if the active TTS cannot realize every control.
7. **Unsupported controls are never fabricated.**
8. **Uncertain semantics become REVIEW**, not silent guesses.
9. **QC is default-on** and attached to exact audio hashes.
10. **Repair is minimal and bounded.**

## How to extend this checklist

When a missing requirement or better idea is discovered:

1. add a new row to **Capability checklist**;
2. assign one status from the legend;
3. link it to code/PR/run evidence when implementation starts;
4. add or refine its acceptance gate in the appropriate authoritative SAYDI task;
5. never mark ✅ without concrete evidence;
6. if it changes an Owner-locked invariant, update `SOURCE_OF_TRUTH.md` explicitly.

This file is intentionally designed to grow over time.

## Owner-approved SAYDI V6 upgrade work packages (2026-10-08)

**Status: PLANNED / NOT YET IMPLEMENTED.** These are subordinate capability gaps under the authoritative `SAYDI-004..010` sequence and existing SAYDI-ND / SAYDI-QC execution tracks. Requirements + acceptance contract: [SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md](./SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md). Do not mark a work package AVAILABLE merely because the documentation exists.

| Work package | Capability gap to close | Status / gate |
|---|---|---|
| V6-P0-01 | Source-faithful Editorial QA with hierarchical semantic context, punctuation, must-check Vietnamese tones and derived-only fixes | 🔒 Owner requirement LOCKED; implementation/field gate PENDING |
| V6-P0-02 | Fingerprint-based approved WAV reference, consistent native VieNeu articulation across complete chapter, representative 3–5 passage A/B approval | 🔒 Owner requirement LOCKED; listening gate PENDING |
| V6-P0-03 | Distinguish source/editorial fault vs real TTS tone/slur fault vs ASR false alarm; dual evidence and timecoded cause | ❌ Not integrated into production closed loop |
| V6-P0-04 | Accept only improved SHA-matched localized repair; bounded retries, unchanged neighbors, recheck changed clips, do not rerender whole chapter | 🟡 Partial field prototype; production integrated acceptance PENDING |
| V6-P0-05 | Semantic pauses, crossfade/edge-click detection and verified continuous long-form output without atempo/time stretching | 🟡 Partial; long chapter Owner A/B acceptance PENDING |
| V6-P0-06 | 8-GB host memory/thread limits on TTS and ASR child processes, watchdog pause/resume without duplicate workers | 🟡 Local scripting exists; repo integration and controlled field tests PENDING |
| V6-P1-07 | Versioned Director→Robot job contract; default local/private production, batch cloud analysis only with Owner enablement | 🟡 Contracts exist; end-to-end orchestration PENDING |
| V6-P1-08 | Operator receives chapter audio + concise sampled review + precise timecoded exceptions + verifiable FINAL gate | 🟡 Local sample packages exist; production dashboard/release gate PENDING |

Latest local diagnostic, **not formal project completion**: chapter 1 V5 = 347 generated; R2 = 115 basic ASR REVIEW, 279 strict ASR REVIEW, Owner listening gate still pending. These numeric flags **are not audible defect counts** and must not be treated as direct proof of the quality percentage.

The active Source of Truth still selects **SAYDI-002** as NEXT until formally changed; no new competing NEXT task is created here.
