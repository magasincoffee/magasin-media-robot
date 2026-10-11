# SAYDI — Kế hoạch tích hợp render + QC tự động theo phong cách G

**Ngày:** 2026-10-11
> **OWNER UPDATE 2026-10-11:** Main SOT was corrected and merged through [PR #103](https://github.com/magasincoffee/magasin-media-robot/pull/103). **VieNeu local on DESKTOP-H4A16IL is the ONLY active TTS path; SaydiVoice and historical `SAYDI002-003` are RETIRED / NON-EXECUTABLE.** New subtask NEXT: `SAYDI002-VN-001`. This newer instruction overrides any older SaydiVoice examples below. The chapter G audio remains REVIEW, not FINAL.
  
**Chủ trương Owner:** CHỐT phong cách nhạc tiêu đề G.  
**Trạng thái:** KẾ HOẠCH / CHƯA HOÀN THÀNH TÍCH HỢP / CHƯA PRODUCTION-ACCEPTED.  
**Host:** DESKTOP-H4A16IL, local-first.  
**Sole authority:** SOURCE_OF_TRUTH.md trên main.  
**References:** SAYDI_002_TEMP_SOURCE_OF_TRUTH.md; SAYDI_V6_NARRATION_QUALITY_EXECUTION_PLAN.md; SAYDI_PROSODY_PRONUNCIATION_QC_TEMP_SOURCE_OF_TRUTH.md; SAYDI_NARRATION_DIRECTOR_TEMP_SOURCE_OF_TRUTH.md; NARRATION_INTELLIGENCE_CAPABILITY_MATRIX.md.

> Đây là đặc tả triển khai phụ thuộc SOT, không tạo NEXT, task P3/P4 hay chuỗi TASK_ID mới. SAYDI-002 vẫn là NEXT. Theo **main SOT đã cập nhật ngày 2026-10-11**, toàn bộ SaydiVoice đã nghỉ, task cũ `SAYDI002-003` và mẫu SG - Chí Đạt không còn là điều kiện thực thi. **Nhiệm vụ con hiện tại là `SAYDI002-VN-001`**: kiểm kê read-only trên H4, giữ nguyên VieNeu/checkpoint. Owner chốt phong cách G **không đồng nghĩa** nghiệm thu toàn bộ Chương 4 hay thay đổi giọng VieNeu đã duyệt. Kế hoạch được viết trên Draft PR #101, chưa merge/main/cutover.

## 1. Đầu ra mục tiêu

Sau một lần Owner chọn sách có quyền sử dụng, chọn narrator/style đã được phê duyệt và thực hiện START hợp lệ trên MAGASIN Control Center, SAYDI tự chạy:

1. Ingest PDF/TXT/EPUB; phân loại nguồn/OCR, chương, số trang, footer, chú thích và tác giả/người dịch. Bảo toàn ba lớp original / normalized / spoken cùng SHA/offset.
2. Book → chapter → scene → paragraph → segment Director: phân tách đúng ngữ nghĩa, đặt nghỉ/hơi thở, xác định vai trò heading/body/dialogue; đề xuất cách đọc và từ khó, hiển thị low-confidence review.
3. VieNeu native-speed render theo reference/fingerprint Owner-approved; sử dụng queue, mutex, checkpoint và dedup để không tạo lại WAV đạt chuẩn.
4. QC tự động: đúng văn bản, phát âm/đúng thanh, đầu từ, prosody, semantic pause, acoustic, seam và coverage; phân biệt ASR false-positive với lỗi giọng thật.
5. Sửa lỗi retry-safe riêng từng chunk, tối đa 2 phương án; QC lại chunk và hàng xóm. Không rerender toàn chương hoặc vô hạn.
6. Ghép voice master sạch → áp dụng preset G theo ID tiêu đề → QC loudness/duck/cue/body boundary → xuất chapter MP3 REVIEW cùng receipts, 3–5 phút mẫu đại diện và ngoại lệ có timecode.
7. Chỉ xuất READY/FINAL/M4B khi các gate nguồn, fingerprint, QA, Owner và export đủ điều kiện. Nếu không: WAIT_OWNER hoặc REVIEW, không phát hành.

Owner không cần nhờ ChatGPT thủ công render/QC cho từng chương. Robot local tự kiểm tra và đưa **ngoại lệ có bằng chứng** thay vì để Owner tìm lỗi.

## 2. Baseline có thật và giới hạn

| Khối | Đã kiểm tra | Chưa được coi là hoàn thành |
|---|---|---|
| VieNeu, queue, checkpoint | H4 đã render Ch04 440/440, trạng thái REVIEW_READY, owner_approved=false, final=false | Chưa chứng minh tự orchestrate một chapter mới end-to-end |
| Editorial, source lineage, QC | Draft PR #101 có rule/audit/repair-inventory tools; Windows CI và H4 hồi quy GREEN | Nhiều tool đang OFF-by-default / REVIEW-only, không nằm trong production workflow |
| Lỗi mất âm đầu | Exact PCM Ch04 440/440: không có head trim; 255 đoạn có suy giảm năng lượng 12ms đầu | Fade nhỏ không chứng minh mất nửa từ; phải kiểm tra VieNeu gốc + ngữ cảnh đầu câu |
| Semantics và page furniture | Ch02–05 phát hiện số trang dạng isolated chunk 50 / 60 / 69,80 / 93; Ch04 E staging bỏ 69,80 | Không tự xóa số có nghĩa hoặc chú thích nguồn nếu chưa chắc |
| Heading G | Staging mixer original 2s melody + nhạc thấp dưới heading, 8 headings Ch04 | Chưa tích hợp versioned preset vào hệ thống render/QC production |
| MP3 G Ch04 | SHA a9c2c1bae4824fdf05e8587983c65ccea77187e731b6e6da04551e7c6ba8bb98, 2470.315s, decode PASS | Đó là bản phối từ WAV đã có, không phải chứng minh tự sinh lại voice hoặc QC toàn phần |
| Control/worker | Local read-only monitoring, legacy watchdog/guardian tồn tại | Owner START/STOP unified, OFF-after-reboot và rollback chưa field-qualified |

Dữ liệu audio, sách, credentials, Chrome profile và checkpoint chỉ lưu local. Không commit lên Git hoặc upload Actions artifact.

## 3. G_V1 — Preset Owner chốt, phải đóng gói thành contract

Tên preset: **SAYDI_HEADING_MUSIC_G_V1**.

- Trigger chỉ khi manifest role là CHAPTER_TITLE / SECTION_HEADING / SUBSECTION_HEADING, đã có xác minh lineage. Không có nhạc QC beep, spoken ID, âm dưới thân truyện hay đoạn thoại thông thường.
- Bản G mẫu: original 3-note music **2,000 ms** trước heading, nghỉ **160 ms**, nhạc nhỏ dưới **chính WAV tiêu đề**, giảm theo vùng có lời nói, fade-out hoàn toàn trước phần BODY. Không sao chép âm từ video tham chiếu.
- Biên độ đã đo ở staging: prelude peak 0.036102 (FS), RMS 0.010253; ducked-bed peak mẫu Ch04 0.005473. Đây là baseline để kiểm thử, không phải tự tuyên bố đã đạt EQ/true peak trên mọi thiết bị.
- Giọng tiêu đề có nhấn/nhịp riêng trong narration plan; nhạc là landmark, không thay thế việc TTS diễn cảm. Giữ natural articulation, không atempo, không pitch/time-stretch.
- Versioned fingerprint tối thiểu: canonical_source_sha, spoken_manifest_sha, heading_role IDs, narrator reference/fingerprint, G music preset version, cue PCM SHA, bed mix policy, voice/MP3 output SHA, source-to-audio timecodes, QC receipt.
- Tiêu chí: đúng toàn bộ heading, không cue ở body; music mix không che từ đầu câu; không clipping/loudness jump/click; Giữ WAV giọng gốc và stage E để so sánh/rollback. Thay G version/voice fingerprint → invalidation và approval gate thích hợp.

## 4. Các gói triển khai gắn với TASK chính thức (không tạo task queue mới)

| Task SOT / thứ tự | Source cần tích hợp | Definition of Done |
|---|---|---|
| **SAYDI-002** | Thực hiện `SAYDI002-VN-001..005` theo TEMP SOT mới: kiểm kê H4, xác minh VieNeu adapter, giọng `SAYDI Nam Mien Nam`, local sample/QC, G mixer, bàn giao đúng SOT | VieNeu/worker/checkpoint/voice fingerprint thật; không dùng SaydiVoice, không đụng checkpoint 640; QA/exact-main trước chuyển nhiệm vụ |
| **SAYDI-003** | PDF-first ingest, page/footer/annotation classifier, OCR confidence, three text layers with spans | Không đọc số trang rác; không bỏ nội dung gốc; số không rõ là trang hay nội dung → REVIEW |
| **SAYDI-004** | Semantic boundary reconstruction, Vietnamese leading word MUST_CHECK, title roles, chapter/scene/paragraph hierarchy | Không chẻ câu sai nghĩa; canonical token map giữ nguyên; heading tách body; test tiếng Việt |
| **SAYDI-005** | Director schema, book/scene contextual delivery, reference fingerprint, heading G preset and approval contract | No fake VieNeu controls, no automatic approval; deterministic valid plan; confidence+review |
| **SAYDI-006** | VieNeu queue, idempotent render, resource controller, source/voice/job hash, checkpoint and bounded retry | One worker only, no simultaneous VieNeu+Whisper heavy; RAM and owner START gate; resume unchanged chunks |
| **SAYDI-007** | Native-speed seam/paragraph pause assembler; E speech baseline; versioned post-speech-QC G mix | E/G exact same canonical voice WAV inputs; click/silence/edge/loudness/timecodes measured, including first-word preservation |
| **SAYDI-008** | Layered QC (source/coverage/diacritic/onset/prosody/join/G mix) + root-cause classifier + repair | Targeted safe <=2 candidates, ASR not final authority; neighbor QA, timecode; unknown/blocked → REVIEW |
| **SAYDI-009** | Chapter-MP3 REVIEW and versioned export receipts; qualified M4B packaging | Decoder PASS, all chapter metadata/ordering and QA, no unresolved material defects, Owner gates before FINAL |
| **SAYDI-010** | MAGASIN Control Center Owner START/STOP, progress, RAM/status, playback and exception dashboard | Durable STOP latch, authenticated session/CSRF/Origin, OFF after reboot post-approved cutover, honest heartbeat, reversible backup |
| **SAYDI-011** | Installer and end-to-end clean Windows acceptance | Legally usable new book completes from import → VieNeu → QC → G → REVIEW / authorized release without ChatGPT intervention; recovery and rollback field-tested |

### Extend existing paths, do not rebuild the robot

- Core: 02_SAYDI_CORE/src/saydi_audiobook/text_layers.py, editorial.py, contracts.py, director.py, narration.py, prosody.py, pronunciation.py, quality.py, repair.py, workflow.py, voice.py.
- Narration: tools/saydi_tts/narration/prepare_editorial_manifest.py and build_directed_audio.py; reconcile actual local C:\SAYDI\narration_director_v1\chapter_v5_job.py and render_owner_approved_v5.py with repo before production patch.
- QC: reuse tools/saydi_tts/qc/v5_source_lineage.py, v5_editorial_structure_gate.py, v5_first_word_onset_gate.py, v5_join_onset_audit.py, v5_staged_review_assembler.py, v5_title_music_staging.py and bounded repair/QC/release helpers. Staging code is **not** authorized as a production worker by being imported.
- Tests: 02_SAYDI_CORE/tests and tools/saydi_tts/qc/test_v5_*; synthetic fixtures only.
- Control belongs to existing unified Control Center and SAYDI/ Supervisor SOT control-plane gates; preserve independently recoverable SAYDI engine, no new competing watchdog.

## 5. Acceptance gates for one genuinely unattended chapter

| Gate | Concrete evidence | On failure |
|---|---|---|
| G0 — Authorization | Valid SOT task, exact Owner START, job ID/actor, checkpoint+mutex | No start, no side-effect |
| G1 — Manuscript | Original/normalized/spoken diff, page/notes approved policy, source SHA | REVIEW_EDITORIAL |
| G2 — Director/voice | Approved active reference, semantic segments, native onset and phrase delivery | REVIEW_VOICE / repair plan |
| G3 — Render | Stable chunk hashes/versions, no duplicate render, RAM/worker isolation | PAUSED_RESOURCE |
| G4 — QC | True spoken coverage, tone/word evidence, timing, prosody and seams | bounded isolated repair |
| G5 — Mix G | Cue at every valid heading and nowhere else; original first syllable intelligible; no clipping/duck failures | REVIEW_MIX, keep baseline E |
| G6 — Export REVIEW | Full decoder/FFprobe, chapter length/hash/markers, 3–5 minute preview and exact exception timecodes | REVIEW_READY, not FINAL |
| G7 — Owner | Material errors resolved or explicit signed exception/voice consent | WAIT_OWNER |
| G8 — Control lifecycle | STOP survives reboot, Owner START resumes checkpoint only, no double model, rollback safe | No cutover |

**Critical:** Green unit tests, MP3 decodable and Whisper similarity do **not** equal listening acceptance or FINAL.

## 6. Local orchestration contract and resources

Target stage machine:

QUEUED → PREFLIGHT → PREPARE_TEXT → DIRECTOR → SAMPLE_GATE → RENDER → QC_SEGMENTS → SAFE_REPAIR → ASSEMBLE_VOICE → QC_SEAMS → APPLY_G → QC_G_MIX → CHAPTER_REVIEW → READY_OR_WAIT_OWNER.

Each phase records immutable input/output SHA, source/ref/preset versions, worker/mutex ownership, task authorization, retry count, phase/heartbeat and redacted error class. Resume reuses already verified artifacts; no repeated paid Generate, no rerender of accepted chunk or accidental double-QC.

- Heavy VieNeu and local ASR/Whisper run **sequentially**, never in parallel on 8GB H4. RAM checked dynamically immediately before model load; preserve historical **2.3 GiB Chapter 2 V5 QC** gate pending individual requalification, not blindly lower it.
- Explicit Owner START applies to qualified Control Center after cutover. Durable STOP prevents watchdog/scheduler restart, and boot default is OFF after verified migration; before migration do not mutate legacy scheduled tasks or auto-start workers.
- Semantic ambiguity, source/explanation/translator notes, new voice or changed G preset need review when consequential; low-risk routine QC/repair must remain local and self-running. No cloud manuscript usage without opt-in.
- G is *editorial sound design*, while QC signals are invisible metadata only.

## 7. Incremental execution and verification sequence

1. **Read-only baseline + doc PR:** inventory main SOT and temp task states, local running jobs/guardians, RAM, manifest/audio/checkpoint SHA; freeze known good Ch02/Ch03/Ch04 files. This document on Draft PR #101, not main.
2. **SOT-authorized VieNeu SAYDI002 gates:** bắt đầu `SAYDI002-VN-001` kiểm kê read-only VieNeu trên H4, đối chiếu 640 checkpoint bảo vệ và voice/reference hiện có; sử dụng bằng chứng WAV VieNeu đã render, không login/Generate SaydiVoice; đóng 002 chỉ khi các cổng VieNeu và nghe duyệt thật đạt, không dùng phong cách nhạc G để duyệt thay.
3. **Offline implementation:** schema/director roles, page/annotation policy, G preset/mixer contract, orchestration stage interface and synthetic negative tests. Targeted/impacted tests GREEN before CI all.
4. **Local H4 dry-run:** reproduce E→G with hash checks; inject bad source/heading/page, duplicate chunk, failed fade/duck, rejected first-word and missing WAV. Show fail-closed and immutable output.
5. **First real limited TTS pilot only after authorization:** isolated new passage with source/ref/Owner approval, safe RAM, single worker, QC and at most 2 target repair candidates; neighboring WAV hashes unchanged.
6. **Full chapter field pilot:** owner-friendly complete MP3 + selected excerpts, timecoded QC and source proof; actual Owner listening verifies initial syllables, joins and G title feel. Rejection stays REVIEW.
7. **Control Center + export + recovery:** start/stop/reboot/rollback in isolated qualified conditions; main SOT/CI/exact-main after authorized merge; never treat a Draft PR as production install.

### Criteria to claim “robot tự render + tự QC thành G”

- One *new* chapter independently completes PREPARE_TEXT → VieNeu render → automatic QC → bounded isolated repair → G cue only at headings → mastered MP3 REVIEW **without live ChatGPT/Remote Desktop intervention between a valid Owner START and REVIEW**.
- Every produced/omitted spoken element reconciles with immutable source; no printed page numbers falsely spoken or meaningful numbers silently removed.
- All voice/heading fingerprints are stable; no paid duplicate TTS or destroyed approved checkpoints, 100% expected title cues and 0 cue/body leaks.
- Targeted QA detects controlled pronunciation/onset/join regressions and rejects unsafe repair; whole chapter decoder/acoustic gate + Owner listening verdict exist.
- STOP/START/reboot safety and exact-main qualification pass before production auto-operation.

## 8. Current authorized next action

**Now:** record this Owner G style lock and implementation plan on Draft PR #101; optionally link the existing V6 planning document. Keep PR draft and main SOT authoritative. **No production script deployment, model start, main merge, Windows task edit, Supabase queue write, media overwrite, or FINAL claim.**

**Next executable project action:** đọc main SOT mới (merged PR #103) và TEMP SOT VieNeu; thực hiện `SAYDI002-VN-001` **read-only inventory trên DESKTOP-H4A16IL** trước các cổng local tiếp theo. Không yêu cầu 4K7, không SaydiVoice profile/generate. Owner phê duyệt G là quyết định thiết kế nhạc, không phải `FINAL` hay duyệt thay fingerprint VieNeu.

**Status:** plan prepared, integration and end-to-end field verification still pending.
