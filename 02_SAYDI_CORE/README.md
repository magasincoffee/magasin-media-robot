# SAYDI Audiobook Core — SAYDI-002 vertical slice

This package is the first runnable workflow slice. It intentionally uses a UTF-8 text fixture; PDF ingestion belongs to SAYDI-003.

## What the slice proves

```text
input
 -> ORIGINAL / NORMALIZED / SPOKEN text
 -> book profile
 -> narration profile + fingerprint
 -> representative passages
 -> text approval
 -> local audible sample
 -> audio approval
```

## Run without installing the package

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\02_SAYDI_CORE\src"
$run = "$env:LOCALAPPDATA\SAYDI\Audiobook\demo\run-001"

py -3 -m saydi_audiobook prepare --input 02_SAYDI_CORE\fixtures\business_sample_vi.txt --run-dir $run --analysis rules
py -3 -m saydi_audiobook decide-text --run-dir $run --decision approve
py -3 -m saydi_audiobook synthesize-sample --run-dir $run --provider windows-sapi
```

The Windows SAPI provider is a **zero-API-cost prototype** for validating the audible approval workflow. It is not the final narrator-quality local TTS decision.

After listening:

```powershell
py -3 -m saydi_audiobook decide-audio --run-dir $run --decision approve
```

## Optional local LLM via Ollama

```powershell
py -3 -m saydi_audiobook prepare --input 02_SAYDI_CORE\fixtures\business_sample_vi.txt --run-dir "$env:LOCALAPPDATA\SAYDI\Audiobook\demo\run-ollama" --analysis ollama --ollama-model qwen3:8b
```

The model name is only an example runtime value, not a locked architecture decision. Model selection must be benchmarked for Vietnamese quality, licensing and the target machine.

Cloud AI is not required.

## Tests

```powershell
$env:PYTHONPATH = "$PWD\02_SAYDI_CORE\src"
py -3 -m compileall -q 02_SAYDI_CORE\src 02_SAYDI_CORE\tests
py -3 -m unittest discover -s 02_SAYDI_CORE\tests -v
```
