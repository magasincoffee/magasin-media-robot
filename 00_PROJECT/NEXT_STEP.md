# Next Step

## Immediate next step — Final D2 field gate with V0.3.2

Real V0.3.1 run `20260917_142133_bd48aed7` verified that pause restoration and visible setting-value capture now work, but two custom-provider surfaces are still under-captured in structured JSON:

- the language dropdown visibly shows language labels, while `language.options` is empty;
- the voice modal visibly shows one automatic voice card, while the catalog counts navigation tabs as voice options.

V0.3.2 adds a second privacy-safe visible-leaf delta pass specifically for custom SaydiVoice surfaces. It excludes input/contenteditable text, filters modal navigation/generic controls, captures visible language labels, and recognizes the current automatic voice card without changing a selection.

## Operator sequence

1. Use `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.2.zip` on the target Windows laptop.
2. Extract to a new folder.
3. Run `CAI_DAT_VA_CHAY.bat`.
4. Do not manually change voice, language, pause, sliders, output format, or script while discovery is running.
5. Do not click `Tạo giọng nói`.
6. Let the robot finish by itself.
7. Return the newest same-run artifacts, especially `voice_catalog.json`, `settings_catalog.json`, `d2_voice_surface.png`, `d2_language_surface.png`, and `d2_pause_surface.png`.
8. Never send `browser_profile`.

## D2 acceptance gate

Merge PR #7 when:

- voice catalog identifies `Tự động — Hệ thống tự chọn giọng` or equivalent semantic automatic-card evidence rather than modal navigation tabs;
- language catalog includes visible choices such as English/Tiếng Việt instead of an empty list;
- pause reports restored/closed after observation;
- display values remain `2.8`, `Ổn định`, `1.00×` for the current page state;
- MP3 remains selected and no provider setting changed;
- no Generate/download occurs;
- structured evidence contains no script/editor text.

## After D2 — D3 Generation Lifecycle

After D2 field acceptance and merge: use a minimal controlled text sample to characterize Generate start, processing, completion, error, quota behavior, result-player controls, and lifecycle timing. D3 may trigger one real generation only after the operator package explicitly marks that action as controlled. Audio download remains D4.
