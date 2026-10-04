# SAYDI Local QC

Runs after chapter rendering. Acoustic checks, ASR verification, timecode reporting, and bounded technical repair are local-first and listener-invisible.

## PyAV compatibility

As of 2026-10, faster-whisper 1.2.x passes `metadata_errors` to `av.open()`, while PyAV 19 removed that parameter. The local QC environment must therefore pin `av>=11,<19` until faster-whisper is updated/validated against PyAV 19+.

## QC v2 measurements

Each rendered chunk now records a structured observation keyed to the exact audio SHA-256:

- ASR similarity;
- minimum and mean word confidence from faster-whisper word timestamps;
- suspect/unclear word tokens;
- speaking rate (words/minute);
- pause/silence ratio;
- coarse pitch/F0 variation in semitones;
- energy/dynamics variation;
- clipping ratio;
- duration and attempt number.

These observations are persisted through the existing local QC report path. They are not uploaded as GitHub artifacts.

Important: word confidence and pitch variation are QC signals, not ground truth. Pronunciation repair remains bounded and must not silently change canonical book meaning.
