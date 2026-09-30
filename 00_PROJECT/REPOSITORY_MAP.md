# Repository Map

The repository currently contains the mature SaydiVoice discovery foundation and project documentation. New audiobook implementation directories should be materialized only when their task begins. `02_SAYDI_CORE` is now materialized as the cross-cutting executable vertical slice for SAYDI-002.

## Target SAYDI Audiobook structure

```text
magasin-media-robot/
├── .github/
│   └── workflows/
│       └── saydi-live.yml                 # trusted provider checks
├── 00_PROJECT/
│   ├── SOURCE_OF_TRUTH.md                 # single authoritative state
│   ├── PROJECT_VISION.md
│   ├── ARCHITECTURE.md
│   ├── AUDIOBOOK_DATA_CONTRACTS.md
│   ├── ROADMAP.md
│   ├── DEVELOPMENT_RULES.md
│   ├── QA_STRATEGY.md
│   ├── REPOSITORY_MAP.md
│   ├── CURRENT_STATUS.md
│   ├── NEXT_STEP.md
│   ├── DECISIONS.md
│   ├── BUG_LOG.md
│   ├── TEST_LOG.md
│   └── CHANGELOG.md
├── 01_DISCOVERY/
│   └── saydivoice/                        # existing provider discovery/evidence
├── 02_SAYDI_CORE/                         # SAYDI-002 executable vertical slice/contracts
├── 02_BOOK_INGEST/                        # SAYDI-003
├── 03_TEXT_ENGINE/                        # SAYDI-004
├── 04_NARRATION_ENGINE/                   # SAYDI-005
├── 05_VOICE_ENGINE/                       # SAYDI-002 production provider layer
├── 06_AUDIO_ENGINE/                       # SAYDI-007
├── 07_ALIGNMENT_QA/                       # SAYDI-008
├── 08_EXPORT_ENGINE/                      # SAYDI-009
├── 09_ORCHESTRATOR/                       # SAYDI-006
├── 10_DESKTOP_APP/                        # SAYDI-010
├── 11_QA/                                 # cross-cutting automated tests
├── 12_INSTALLER/                          # SAYDI-011
├── schemas/                               # versioned JSON schemas
├── fixtures/                              # synthetic/public test fixtures only
├── templates/                             # narration/export profiles
├── .gitignore
└── README.md
```

## Runtime is not repository content

Production data belongs under a local runtime root such as:

```text
%LOCALAPPDATA%/SAYDI/Audiobook/
  config/
  browser_profile/
  library/<book_id>/
    source/
    manifests/
    segments/
    audio/raw/
    audio/processed/
    chapters/
    exports/
    qa/
    logs/
  cache/
  diagnostics/
```

Never commit source manuscripts, generated production audio, local SQLite databases, browser profiles or credentials.

## Migration rule

Do not delete `01_DISCOVERY/saydivoice`. It contains field evidence and reusable provider knowledge.

Old video-oriented top-level module names were documentation-only placeholders and had no implementation on `main`; the audiobook target map supersedes those placeholders.
