# Next Step

## Immediate next step — D5 controlled limits/error characterization

Authenticated live discovery is now working on the Windows self-hosted runner and D1–D4 are field-verified. The next phase is not another authentication/browser bootstrap. It is a bounded characterization of Saydi provider limits and failure modes.

## Current validated baseline

- Runner: `MAGASIN-PC` (`self-hosted`, `Windows`, `X64`).
- Browser: installed Google Chrome controlled by Playwright.
- Persistent profile: `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`.
- Session: `TTS_READY` + `AUTHENTICATED_OR_HIDDEN`.
- D3: one authenticated Generate succeeds and yields a real download-ready result.
- D4: one authenticated Download succeeds; metadata can be captured and the temporary audio deleted before evidence upload.
- Normal live-session workflow remains non-destructive by default.

## D5 objectives

Characterize only limits/errors that materially affect a production Voice Engine. Do not stress-test the provider and do not bypass provider restrictions.

Priority checks:

1. **Text boundary behavior**
   - verify accepted lengths near practical/advertised limits using the minimum number of requests;
   - record validation messages/statuses without repeatedly probing the same boundary.
2. **Unsupported/invalid input behavior**
   - empty or whitespace-only input where the UI permits observation without generation;
   - clearly over-limit input only if it can be rejected before provider generation work.
3. **Session expiry/re-auth behavior**
   - observe naturally when encountered; do not intentionally invalidate credentials unless required for a bounded test.
4. **Quota/rate-limit behavior**
   - prefer passive observation from normal runs;
   - do not intentionally exhaust free/paid quota or generate rapid repeated requests.
5. **Format/settings failure behavior**
   - only test combinations exposed by the UI and avoid combinatorial sweeps.

## D5 acceptance gate

D5 is sufficient when the project has documented, reproducible handling for the production-relevant provider errors encountered or safely observable, including:

- user-facing error/validation signal;
- relevant HTTP status/endpoint metadata where privacy-safe;
- whether a request consumed generation quota;
- retryability classification (`retry`, `re-auth`, `fix input`, or `do not retry`);
- bounded timeout/cancellation behavior.

## After D5

1. Freeze D6 discovery contracts: selectors, session requirements, generation lifecycle, download lifecycle, errors/timeouts, privacy boundaries.
2. Build the production SaydiVoice provider adapter against those frozen contracts.
3. Keep browser profile/auth state local; never place it in GitHub artifacts or repository files.

No operator ZIP round-trip is required for ordinary D5 iterations while the self-hosted runner is online.
