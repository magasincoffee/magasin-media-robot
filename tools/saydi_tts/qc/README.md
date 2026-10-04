# SAYDI Local QC

Runs after chapter rendering. Acoustic checks, ASR verification, timecode reporting, and bounded technical repair are local-first and listener-invisible.

## PyAV compatibility

As of 2026-10, faster-whisper 1.2.x passes `metadata_errors` to `av.open()`, while PyAV 19 removed that parameter. The local QC environment must therefore pin `av>=11,<19` until faster-whisper is updated/validated against PyAV 19+.
