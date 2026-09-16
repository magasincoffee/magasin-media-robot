# SaydiVoice Discovery

This workstream exists to learn the real behavior of SaydiVoice Studio before production browser automation is frozen.

Target: `https://voice.saydi.ai/vi/studio/tts/`

## Discovery goals

- identify logged-in / logged-out / blocked / unexpected states;
- map TTS controls and accessible labels;
- enumerate available voices and relevant metadata exposed by the UI;
- identify language, speed, pitch, style/emotion, format, or other settings if present;
- observe generation lifecycle states;
- observe preview and download behavior;
- determine download file naming/format behavior;
- characterize popups/modals/cookie banners;
- characterize session expiry and recoverable failures;
- test text-length behavior safely;
- generate robust locator candidates rather than hard-coded brittle selectors.

## Intended local discovery outputs

```text
%LOCALAPPDATA%/MAGASIN/MediaRobot/discovery/saydivoice/
  runs/<run-id>/
    discovery.log
    discovery_report.json
    page_state.json
    controls.json
    voice_catalog.json
    screenshots/
    snapshots/
    downloads/
```

These runtime artifacts are local and are not committed automatically. Sanitized examples/schemas may be committed only after review.

## Safety rules

The discovery runner must not record passwords, raw cookies, tokens, authorization headers, or browser profile contents. Early discovery should be non-destructive: inspect state first; do not generate/download audio until the step explicitly calls for it.
