# MAGASIN Voice Engine

Production provider-neutral voice interface for MAGASIN Media Robot.

## Current provider

`SaydiVoiceProvider` orchestrates a `SaydiPlaywrightBackend` using the field-verified authenticated SaydiVoice Studio path.

The browser profile remains local at:

```text
%LOCALAPPDATA%\MAGASIN\MediaRobot\saydivoice\browser_profile
```

It is never serialized into requests, logs, Git commits, or CI artifacts.

## Contract

A `VoiceRequest` contains:

- `text`;
- `preset_key`;
- optional `voice_override`;
- optional `format_override`;
- `output_directory`;
- explicit `allow_generate`;
- explicit `allow_download`;
- bounded generation/download timeouts.

A `VoiceResult` returns:

- pipeline status (`SUCCESS`, `RETRYABLE_FAILURE`, `ACTION_REQUIRED`, `FATAL_FAILURE`);
- provider, voice, preset and audio format;
- generation attempt count;
- whether provider history was created;
- local audio path, byte count and SHA-256 when Download was authorized;
- normalized error class (`fix_input`, `re_auth`, `retry`, `do_not_retry`).

## Side-effect policy

Normal preflight is read-only. Generate is blocked unless `allow_generate=True`. Download is blocked unless both `allow_generate=True` and `allow_download=True`.

`SaydiVoiceProvider` never automatically retries Generate. A failed generation returns a retryability classification to the caller; a second provider request must be a separate caller decision.

## Voice/style presets

The current production policy includes:

- `tiktok_energetic`;
- `review_natural`;
- `story_warm`;
- `news_stable`;
- `slow_emotional`.

These are application-level combinations of the controls actually observed on Saydi: voice, the Biểu cảm ↔ Ổn định axis, speed, pause enable state, and output format. They are not a claim that Saydi exposes a discrete emotion API.

## Example

```python
from pathlib import Path

from magasin_voice_engine import SaydiVoiceProvider, VoiceRequest
from magasin_voice_engine.saydi_playwright import SaydiPlaywrightBackend

provider = SaydiVoiceProvider(SaydiPlaywrightBackend())
result = provider.run(
    VoiceRequest(
        text="MAGASIN xin chào.",
        preset_key="tiktok_energetic",
        output_directory=Path.home() / "Music" / "MAGASIN",
        allow_generate=True,
        allow_download=True,
    )
)
print(result.to_dict())
```

The example is a live side-effecting operation. Unit/CI tests use fake backends and never call Saydi.

## Development

```powershell
cd 02_VOICE_ENGINE
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Do not add live Generate/Download calls to ordinary CI.


## Supervisor status + heartbeat

Every production `SaydiVoiceProvider` run now publishes privacy-safe local state to:

```text
%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\supervisor_state.json
```

and renders a self-refreshing local dashboard at:

```text
%LOCALAPPDATA%\MAGASIN\MediaRobot\saydi\saydi_status.html
```

The status model is `IDLE`, `RUNNING`, `WAIT_USER`, `RETRYING`, `FAILED`, or `DONE`. Active jobs refresh a heartbeat every 30 seconds. The dashboard marks a `RUNNING`/`RETRYING` heartbeat stale after 90 seconds.

The monitor stores job/step metadata only. It never stores request text, browser cookies, auth tokens, provider response bodies, or generated audio.

To inspect/open the dashboard from an installed Voice Engine environment:

```powershell
magasin-saydi-status --show
magasin-saydi-status --open
```

The provider's no-automatic-Generate-retry policy remains unchanged. A retryable provider failure becomes `WAIT_USER` until an explicit caller decision starts a new attempt; `RETRYING` is reserved for an outer supervisor that has explicitly begun such a retry.
