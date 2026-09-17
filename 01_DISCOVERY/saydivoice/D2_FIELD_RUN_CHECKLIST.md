# D2 V0.3 field run checklist

1. Extract `MAGASIN_SAYDIVOICE_DISCOVERY_V0.3.zip` to a new folder.
2. Run `CAI_DAT_VA_CHAY.bat`.
3. Do not manually change voice, language, pause, sliders, output format, or script while discovery is running.
4. Do not click Generate.
5. Let the robot finish and open the local runtime folder.
6. Return eight artifacts from one run ID:
   - report JSON;
   - DOM inventory;
   - surface map;
   - selectors;
   - voice catalog;
   - settings catalog;
   - screenshot;
   - JSONL log.
7. Never send `browser_profile`.

Acceptance: D2 outputs reflect the real provider UI without changing provider state and without exposing script/editor values.
