# Architecture

## High-level pipeline

```text
SOURCE MEDIA + CONTENT
        |
        v
Desktop Control Center
        |
        +--> Project Manager / State Store
        |
        +--> Media Analyzer
        |
        +--> Script & Scene Planner
        |
        +--> SaydiVoice Browser Adapter (Playwright)
        |
        +--> Audio Processor
        |
        +--> Subtitle Timing Engine
        |
        +--> Video Composer
        |
        +--> FFmpeg / FFprobe Render Engine
        |
        +--> Quality Validator
        |
        v
PREVIEW + FINAL MP4 + LOGS
```

## Major modules

### 01_DISCOVERY
Temporary and repeatable discovery tooling for external browser integrations. First target: SaydiVoice. Discovery outputs stable selectors, settings schema, behavior notes, screenshots, and error-state evidence.

### 02_VOICE_ENGINE
Provider-neutral voice interface. Initial adapter automates `https://voice.saydi.ai/vi/studio/tts/` through Playwright using a local persistent browser profile.

### 03_MEDIA_ANALYZER
Uses FFprobe/OpenCV/PySceneDetect where needed to inspect duration, resolution, FPS, orientation, audio streams, scene boundaries, and source suitability.

### 04_SCENE_PLANNER
Turns user content and source-media inventory into an explicit edit decision list/timeline. V1 is template/rule-based. Later versions may add visual semantic selection.

### 05_SUBTITLE_ENGINE
Creates timed captions from the known script and generated voice. V1 can use sentence-level timing; later versions can optionally use local speech alignment.

### 06_VIDEO_COMPOSER
Builds a render specification: clips, trims, crop, scale, overlays, logo, captions, transitions, voice, music, ducking, and CTA.

### 07_RENDER_ENGINE
Executes the render specification with FFmpeg/FFprobe and validates the output artifact.

### 08_DESKTOP_APP
Windows operator UI. It should expose business actions, not technical implementation details.

### 09_BROWSER_AUTOMATION
Shared Playwright infrastructure: persistent profile, resilient locators, downloads, retry policy, screenshots, DOM snapshots, and integration diagnostics.

### 10_QA
Unit, integration, fixture, browser smoke, render validation, regression tests, and project-state guardrails.

### 11_INSTALLER
One-time Windows setup for bundled runtime/dependencies, directories, browser runtime, model assets if required, and Desktop shortcut.

## Runtime data separation

Repository code and documentation are separated from local runtime state.

```text
repo/                         # source-controlled
%LOCALAPPDATA%/MAGASIN/MediaRobot/
  browser_profile/            # never commit
  projects/
  downloads/
  cache/
  logs/
  diagnostics/
  config.local.json           # never commit
```

## Failure model

Every pipeline stage should end in one of: `SUCCESS`, `RETRYABLE_FAILURE`, `ACTION_REQUIRED`, `FATAL_FAILURE`. Recoverable checkpoints are persisted so the next run can resume rather than restart.

## Integration rule

External websites are treated as unstable dependencies. Core edit/render logic must remain usable even if SaydiVoice selectors change. Browser-specific details live behind adapters and are refreshed by discovery tooling.
