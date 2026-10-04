# SAYDI Narration Intelligence Capability Matrix

Last updated: 2026-10-04

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
| Local VieNeu v3 Turbo production TTS | ✅ AVAILABLE | Field-used on Windows local worker | Remains default all-local TTS path |
| Approved Southern male narrator profile | ✅ AVAILABLE | `SAYDI Nam Mien Nam` active local voice | Narrator identity remains stable across a book unless Owner changes it |
| Automatic local worker / resume / checkpoints | ✅ AVAILABLE | Windows worker, durable queue/checkpoints and chapter assembly are field-used | Fully unattended normal operation |
| Book genre classification | ✅ AVAILABLE | Rule-based classifier + `AnalysisProvider` | Expand taxonomy without coupling to TTS |
| Local LLM analysis boundary | ✅ AVAILABLE | Ollama `AnalysisProvider` interface exists | Local semantic analysis remains default; cloud optional |
| Whole-book style/tone understanding | 🟡 PARTIAL | Current first slice can create `BOOK_PROFILE`; current Ollama implementation analyzes an excerpt rather than a hierarchical full-book pass | Hierarchical book -> chapter -> scene analysis over the complete canonical book |
| Narration profiles `BUSINESS_CLEAR / STORY_NARRATIVE / GENERAL_CLEAR` | ✅ AVAILABLE | Profile selection/fingerprint code exists | Expand into versioned genre/style presets |
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
| Provider-safe mapping of emotion/prosody | 🟡 PARTIAL | Provider-neutral design exists; unsupported controls must not be fabricated | Map only to verified TTS capabilities: segmentation, punctuation, pace, pause, supported reference/style controls |
| ASR text similarity QC | ✅ AVAILABLE | Local QC currently produces similarity/warning/error evidence | Keep as one QC signal, not final acceptance by itself |
| Word-level pronunciation clarity / “lơ lớ” detection | 🟡 BUILDING | Core policy implemented in PR #58; local worker extraction not yet integrated | Exact suspect token + confidence + timecode |
| Vietnamese pronunciation lexicon / spoken-form overrides | 🟡 PARTIAL | Lexicon is architectural requirement; production repair layer not complete | Versioned safe TTS-only overrides without modifying canonical source |
| Prosody QC: speaking rate | 🟡 BUILDING | Core policy in PR #58; local metric extraction pending | Compare against active narration profile envelope |
| Prosody QC: pause/silence pattern | 🟡 BUILDING | Core policy in PR #58; local metric extraction pending | Detect too little/too much/unnatural pause |
| Prosody QC: pitch/intonation variation | 🟡 BUILDING | Core policy in PR #58; local metric extraction pending | Detect flat/robotic delivery and profile mismatch |
| Prosody QC: energy/dynamics | 🟡 BUILDING | Contract/policy direction exists; worker extraction pending | Detect lifeless or overexpressive delivery |
| Acoustic QC / joins / clipping / silence | 🟡 PARTIAL | Existing QA architecture and some local checks; full unified gate still evolving | Default-on after synthesis and chapter assembly |
| Targeted automatic rerender | 🟡 PARTIAL | Repair policy exists; complete local worker loop not yet integrated | Repair only affected chunk/segment, never whole chapter unnecessarily |
| Bounded retry / no infinite rerender | 🔒 LOCKED | Owner-approved architecture; PR #58 policy defaults to bounded attempts | Retry-safe only; exhaustion -> REVIEW |
| Owner exception-only review | 🔒 LOCKED | SOT owner experience rule | Owner should not manually hunt defects |
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
