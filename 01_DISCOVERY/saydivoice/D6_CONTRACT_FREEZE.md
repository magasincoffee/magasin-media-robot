# D6 — SaydiVoice Discovery Contract Freeze

Frozen: 2026-09-17  
Contract: `contracts/saydivoice_contract_v1.json`

## Status

D1–D5 have enough authenticated field evidence to freeze the browser/provider contract used by the next production Voice Engine adapter. D6 introduces no new provider calls: it consolidates the behavior already observed on `MAGASIN-PC` and protects the safety/privacy invariants with unit tests.

## 1. Session contract

Production automation requires:

- page state `TTS_READY`;
- auth state `AUTHENTICATED_OR_HIDDEN`;
- installed Google Chrome controlled by Playwright;
- the persistent Saydi browser profile under `%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile`;
- the profile must remain local and must never be staged as a GitHub artifact.

Anonymous mode is retained only as historical failure characterization. It is not the production path: `/api/session/start` previously returned HTTP 403 and `/api/samples` HTTP 401 in the anonymous flow.

## 2. Locator contract

Locator preference is semantic first: test id → role + accessible name → aria label/placeholder → stable CSS → exact visible text fallback.

Frozen high-value locators:

- editor: `[contenteditable="true"]`;
- Generate: role `button`, exact name `Tạo giọng nói`;
- processing cancellation signal: `Hủy` / `Huỷ` / `Cancel`;
- result/download signal: visible `Tải về` / `Download`;
- voice selector: open from the exact current voice label, search via visible input, resolve the exact voice card, use `Dùng` / `Sử dụng` / `Use`;
- Saydi custom sliders: `.slider`; index 0 is the shared Biểu cảm ↔ Ổn định axis, index 1 is Tốc độ đọc;
- formats: `.fmt-tab`, observed WAV / MP3 / FLAC / OGG.

Selectors must never be derived from user editor text.

## 3. Voice/settings contract

Authenticated discovery observed 60 Vietnamese voices. The verified baseline voice is `Adam — Giọng hot tiktok`; reversible selection was verified against `THEANH28 - Nữ` and restored to Adam.

The UI exposes one shared stability/expression axis rather than two independent sliders. Baseline display is stability `2.8`, expression `Ổn định`. Speed baseline is `1.00×`. No independent mood/emotion selector was observed.

Pause defaults observed read-only:

- automatic pause: off;
- dot: 0.45 s;
- comma: 0.25 s;
- semicolon: 0.3 s;
- newline: 0.6 s.

## 4. Input boundary contract

D5C verified the advertised maximum as 20,000 characters without issuing any `/api/tts` request:

- 0 characters: Generate disabled in the UI;
- 1 character: accepted;
- 20,000 characters: accepted;
- target 20,001: editor clamps to 20,000; Generate remains valid for the retained 20,000 characters.

A production adapter must enforce 1–20,000 characters before provider generation and should not treat the clamp as permission to silently truncate user text. Truncation/splitting policy belongs above the provider adapter.

## 5. Generation lifecycle contract

Generate is destructive/quota-affecting and must remain explicitly gated.

Default production/discovery behavior:

1. require an explicit Generate authorization;
2. use a disposable same-session tab where the discovery runner does so;
3. default to one Generate attempt;
4. observe processing via Generate disappearing/being disabled, `Hủy` appearing, or busy state;
5. wait for a bounded terminal signal (current discovery timeout: 60 s);
6. classify success only from observable evidence, not from the click itself;
7. do not click Download during D3.

Authenticated field verification established a real success path: `POST /api/tts` returned HTTP 200 `audio/mpeg`, `Tải về` appeared, history write returned HTTP 201, and the lifecycle ended as `SUCCESS_SIGNAL`.

Blind retries are forbidden. A reload retry is allowed only if it is separately authorized and the newly observed provider error explicitly asks for reload.

## 6. Download lifecycle contract

Download requires its own explicit authorization and a prior generation success signal. A controlled run may create at most one new download.

The implementation must verify extension and non-zero bytes, hash/measure the file locally when evidence is required, and delete raw generated audio before GitHub artifact staging. Raw audio must never be uploaded to the public repository artifacts.

The field-verified D4 example was an MP3 of 11,853 bytes with SHA-256 `f0dd8145d6d55a70ebb46ab032d7805741f81d64e1ac06b4b9a08008f1928be4`.

## 7. Error/retry contract

- anonymous 403/401 session bootstrap → re-auth/use the authenticated profile; do not blind retry;
- empty input → fix input locally; no provider request;
- above-limit input → reject/split before provider call even though the UI itself clamps;
- generic provider error → no blind retry; capture only privacy-safe transport/HTTP metadata and surface a retryable/non-retryable decision to the caller;
- naturally encountered session expiry → re-authentication path; do not intentionally invalidate credentials merely to test it;
- quota/rate limits → observe passively; never exhaust quota or burst requests for characterization.

## 8. Privacy contract

Never persist or upload:

- editor text;
- credentials, cookies, authorization headers;
- localStorage/sessionStorage;
- browser profile;
- request bodies or successful response bodies;
- raw HTML;
- raw generated audio in GitHub artifacts.

Network evidence is limited to privacy-safe metadata for XHR/fetch/media. Query strings and URL fragments are stripped. The discovery recorder caps events at 180.

## 9. Frozen invariants

Any production adapter built after D6 must preserve these invariants:

1. normal discovery is read-only by default;
2. Generate and Download are independent explicit gates;
3. no authentication/quota/CAPTCHA/provider-restriction bypass;
4. controlled UI mutations are reversible and restored before PASS;
5. success is based on verified state transitions and provider/result evidence;
6. the authenticated browser profile remains local to the runner;
7. private user/editor content is not part of structured discovery evidence.

If Saydi materially changes its DOM, lifecycle, authentication, limits, or provider endpoints, increment the contract version and re-run only the minimum bounded discovery needed to validate the changed section.
