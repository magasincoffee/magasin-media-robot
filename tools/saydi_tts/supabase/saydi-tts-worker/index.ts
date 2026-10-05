
import { createClient } from "npm:@supabase/supabase-js@2";

const TOKEN_HASH = "f848bf5969598eb2372dc992cbe51d8e7ccf719e2487235520f96daacd4e8b7a";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

async function sha256Hex(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ error: "POST required" }, 405);

  const token = req.headers.get("x-saydi-worker-token") ?? "";
  if (!token || (await sha256Hex(token)) !== TOKEN_HASH) {
    return json({ error: "unauthorized" }, 401);
  }

  const body = await req.json().catch(() => ({}));
  const action = String(body.action ?? "");

  const secretKeys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
  const legacyServiceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const adminKey = secretKeys.default ?? legacyServiceRole;
  if (!adminKey) return json({ error: "server key unavailable" }, 500);

  const supabase = createClient(Deno.env.get("SUPABASE_URL")!, adminKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  if (action === "health") {
    return json({ ok: true, service: "saydi-tts-worker-api", version: 3 });
  }

  if (action === "claim") {
    const workerId = String(body.worker_id ?? "saydi-local-worker");
    if (workerId !== "DESKTOP-H4A16IL-SAYDI-TTS") return json({ error: "worker_not_allowed" }, 403);
    const workerNow = new Date().toISOString();
    await supabase.from("saydi_tts_workers").upsert({
      worker_id: workerId,
      hostname: workerId.replace("-SAYDI-TTS", ""),
      status: "online",
      current_job_id: null,
      last_seen_at: workerNow,
      last_error: null,
      updated_at: workerNow,
    }, { onConflict: "worker_id" });

    // Resume an interrupted job already owned by this machine.
    const { data: existing, error: existingError } = await supabase
      .from("saydi_tts_jobs")
      .select("id,title,status,voice_name,output_format,total_source_chars,total_chunks,completed_chunks")
      .eq("worker_id", workerId)
      .in("status", ["claimed", "rendering"])
      .order("created_at", { ascending: true })
      .limit(1);

    if (existingError) return json({ error: existingError.message }, 500);
    if (existing?.length) {
      const now = new Date().toISOString();
      await supabase.from("saydi_tts_workers").upsert({
        worker_id: workerId,
        hostname: workerId.replace("-SAYDI-TTS", ""),
        status: "busy",
        current_job_id: existing[0].id,
        last_seen_at: now,
        updated_at: now,
      }, { onConflict: "worker_id" });
      return json({ job: existing[0], resumed: true });
    }

    const { data: jobs, error: readError } = await supabase
      .from("saydi_tts_jobs")
      .select("id,title,status,voice_name,output_format,total_source_chars,total_chunks,completed_chunks")
      .eq("status", "queued")
      .order("created_at", { ascending: true })
      .limit(1);

    if (readError) return json({ error: readError.message }, 500);
    if (!jobs?.length) {
      const now = new Date().toISOString();
      await supabase.from("saydi_tts_workers").upsert({
        worker_id: workerId,
        hostname: workerId.replace("-SAYDI-TTS", ""),
        status: "online",
        current_job_id: null,
        last_seen_at: now,
        updated_at: now,
      }, { onConflict: "worker_id" });
      return json({ job: null });
    }

    const job = jobs[0];
    const now = new Date().toISOString();
    const { data: claimed, error: claimError } = await supabase
      .from("saydi_tts_jobs")
      .update({
        status: "claimed",
        worker_id: workerId,
        claimed_at: now,
        updated_at: now,
      })
      .eq("id", job.id)
      .eq("status", "queued")
      .select("id,title,status,voice_name,output_format,total_source_chars,total_chunks,completed_chunks")
      .maybeSingle();

    if (claimError) return json({ error: claimError.message }, 500);
    if (claimed) {
      const now2 = new Date().toISOString();
      await supabase.from("saydi_tts_workers").upsert({
        worker_id: workerId,
        hostname: workerId.replace("-SAYDI-TTS", ""),
        status: "busy",
        current_job_id: claimed.id,
        last_seen_at: now2,
        updated_at: now2,
      }, { onConflict: "worker_id" });
    }
    return json({ job: claimed ?? null, resumed: false });
  }

  if (action === "start") {
    const jobId = String(body.job_id ?? "");
    const now = new Date().toISOString();
    const { error } = await supabase
      .from("saydi_tts_jobs")
      .update({ status: "rendering", started_at: now, updated_at: now, error: null })
      .eq("id", jobId);
    return error ? json({ error: error.message }, 500) : json({ ok: true });
  }

  if (action === "chunks") {
    const jobId = String(body.job_id ?? "");
    const after = Number.isFinite(Number(body.after_index)) ? Number(body.after_index) : -1;
    const limit = Math.max(1, Math.min(20, Number(body.limit ?? 10)));
    const { data, error } = await supabase
      .from("saydi_tts_chunks")
      .select("chunk_index,text_content,spoken_text_override,spoken_text_override_meta,qc_repair_attempts,status")
      .eq("job_id", jobId)
      .gt("chunk_index", after)
      .order("chunk_index", { ascending: true })
      .limit(limit);
    if (error) return json({ error: error.message }, 500);
    const chunks = (data ?? []).map((row: any) => ({
      chunk_index: row.chunk_index,
      // Backward-compatible worker contract: existing workers read text_content.
      // A derived spoken override is exposed only to TTS; canonical text remains in canonical_text_content.
      text_content: row.spoken_text_override || row.text_content,
      canonical_text_content: row.text_content,
      spoken_override_applied: Boolean(row.spoken_text_override),
      spoken_text_override_meta: row.spoken_text_override_meta ?? {},
      qc_repair_attempts: Number(row.qc_repair_attempts ?? 0),
      status: row.status,
    }));
    return json({ chunks });
  }

  if (action === "chunk_status") {
    const jobId = String(body.job_id ?? "");
    const chunkIndex = Number(body.chunk_index);
    const status = String(body.status ?? "completed");
    const errorText = body.error ? String(body.error) : null;
    const now = new Date().toISOString();

    const { error: chunkError } = await supabase
      .from("saydi_tts_chunks")
      .update({ status, error: errorText, updated_at: now })
      .eq("job_id", jobId)
      .eq("chunk_index", chunkIndex);

    if (chunkError) return json({ error: chunkError.message }, 500);

    const { data: workerJob } = await supabase
      .from("saydi_tts_jobs")
      .select("worker_id")
      .eq("id", jobId)
      .maybeSingle();
    if (workerJob?.worker_id) {
      await supabase.from("saydi_tts_workers").upsert({
        worker_id: workerJob.worker_id,
        hostname: String(workerJob.worker_id).replace("-SAYDI-TTS", ""),
        status: "busy",
        current_job_id: jobId,
        last_seen_at: now,
        updated_at: now,
      }, { onConflict: "worker_id" });
    }

    const { count, error: countError } = await supabase
      .from("saydi_tts_chunks")
      .select("*", { count: "exact", head: true })
      .eq("job_id", jobId)
      .eq("status", "completed");

    if (countError) return json({ error: countError.message }, 500);

    const { error: jobError } = await supabase
      .from("saydi_tts_jobs")
      .update({ completed_chunks: count ?? 0, updated_at: now })
      .eq("id", jobId);

    return jobError ? json({ error: jobError.message }, 500) : json({ ok: true, completed_chunks: count ?? 0 });
  }

  if (action === "complete") {
    const jobId = String(body.job_id ?? "");
    const now = new Date().toISOString();
    const { error } = await supabase
      .from("saydi_tts_jobs")
      .update({
        status: "completed",
        output_file_name: String(body.output_file_name ?? ""),
        finished_at: now,
        updated_at: now,
        error: null,
      })
      .eq("id", jobId);
    return error ? json({ error: error.message }, 500) : json({ ok: true });
  }

  if (action === "fail") {
    const jobId = String(body.job_id ?? "");
    const now = new Date().toISOString();
    const { error } = await supabase
      .from("saydi_tts_jobs")
      .update({
        status: "failed",
        error: String(body.error ?? "unknown error").slice(0, 8000),
        finished_at: now,
        updated_at: now,
      })
      .eq("id", jobId);
    return error ? json({ error: error.message }, 500) : json({ ok: true });
  }


  if (action === "book_jobs") {
    const bookId = String(body.book_id ?? "");
    const limitChapter = Number(body.max_chapter ?? 9999);
    const { data, error } = await supabase
      .from("saydi_tts_jobs")
      .select("id,book_id,chapter_number,chapter_title,title,status,total_source_chars,total_chunks,completed_chunks,output_file_name,error,qc_status,qc_issue_count,qc_report,finished_at,updated_at")
      .eq("book_id", bookId)
      .lte("chapter_number", limitChapter)
      .order("chapter_number", { ascending: true });
    return error ? json({ error: error.message }, 500) : json({ jobs: data ?? [] });
  }

  if (action === "qc_report_batch") {
    const jobId = String(body.job_id ?? "");
    const qcStatus = String(body.qc_status ?? "review");
    const report = body.qc_report && typeof body.qc_report === "object" ? body.qc_report : {};
    const events = Array.isArray(body.events) ? body.events.slice(0, 500) : [];

    const { data: job, error: jobReadError } = await supabase
      .from("saydi_tts_jobs")
      .select("id,book_id")
      .eq("id", jobId)
      .maybeSingle();
    if (jobReadError) return json({ error: jobReadError.message }, 500);
    if (!job) return json({ error: "job_not_found" }, 404);

    const autoTypes = ["acoustic", "asr_mismatch", "join_discontinuity", "silence", "clipping", "duration", "decode", "missing_audio"];
    await supabase.from("saydi_tts_qc_events").delete().eq("job_id", jobId).in("event_type", autoTypes);

    if (events.length) {
      const rows = events.map((e: any) => ({
        book_id: job.book_id,
        job_id: jobId,
        chunk_index: Number.isFinite(Number(e.chunk_index)) ? Number(e.chunk_index) : null,
        event_type: String(e.event_type ?? "acoustic"),
        severity: ["info","warning","error"].includes(String(e.severity)) ? String(e.severity) : "warning",
        score: Number.isFinite(Number(e.score)) ? Number(e.score) : null,
        time_start_sec: Number.isFinite(Number(e.time_start_sec)) ? Number(e.time_start_sec) : null,
        time_end_sec: Number.isFinite(Number(e.time_end_sec)) ? Number(e.time_end_sec) : null,
        details: e.details && typeof e.details === "object" ? e.details : {},
        resolved: false,
      }));
      const { error: insertError } = await supabase.from("saydi_tts_qc_events").insert(rows);
      if (insertError) return json({ error: insertError.message }, 500);
    }

    const issueCount = events.filter((e: any) => String(e.severity) !== "info").length;
    const { error: jobUpdateError } = await supabase
      .from("saydi_tts_jobs")
      .update({
        qc_status: qcStatus,
        qc_issue_count: issueCount,
        qc_report: report,
        updated_at: new Date().toISOString(),
      })
      .eq("id", jobId);

    return jobUpdateError ? json({ error: jobUpdateError.message }, 500) : json({ ok: true, issue_count: issueCount });
  }

  if (action === "repair_eligibility") {
    const jobId = String(body.job_id ?? "");
    const indices = Array.isArray(body.chunk_indices)
      ? [...new Set(body.chunk_indices.map((x: any) => Number(x)).filter((x: number) => Number.isInteger(x) && x >= 0))].slice(0, 50)
      : [];
    if (!indices.length) return json({ error: "no_chunk_indices" }, 400);

    const maxAttempts = 2;
    const { data, error } = await supabase
      .from("saydi_tts_chunks")
      .select("chunk_index,qc_repair_attempts,last_repair_request_id,spoken_text_override")
      .eq("job_id", jobId)
      .in("chunk_index", indices)
      .order("chunk_index", { ascending: true });
    if (error) return json({ error: error.message }, 500);

    const rows = data ?? [];
    const eligible = rows
      .filter((row: any) => Number(row.qc_repair_attempts ?? 0) < maxAttempts)
      .map((row: any) => Number(row.chunk_index));
    const exhausted = rows
      .filter((row: any) => Number(row.qc_repair_attempts ?? 0) >= maxAttempts)
      .map((row: any) => Number(row.chunk_index));
    return json({ ok: true, max_attempts: maxAttempts, eligible_indices: eligible, exhausted_indices: exhausted });
  }

  if (action === "repair_chunks") {
    const jobId = String(body.job_id ?? "");
    const indices = Array.isArray(body.chunk_indices)
      ? [...new Set(body.chunk_indices.map((x: any) => Number(x)).filter((x: number) => Number.isInteger(x) && x >= 0))].slice(0, 50)
      : [];
    if (!indices.length) return json({ error: "no_chunk_indices" }, 400);

    const requestId = String(body.repair_request_id ?? "").trim() || ("legacy-" + crypto.randomUUID());
    const maxAttempts = 2;
    const overrideRows = Array.isArray(body.spoken_overrides) ? body.spoken_overrides : [];
    const overrides = new Map<number, any>();
    for (const item of overrideRows.slice(0, 50)) {
      const idx = Number(item?.chunk_index);
      const spokenText = typeof item?.spoken_text === "string" ? item.spoken_text.trim() : "";
      if (!Number.isInteger(idx) || idx < 0 || !spokenText) continue;
      overrides.set(idx, {
        spoken_text: spokenText,
        meta: item?.meta && typeof item.meta === "object" ? item.meta : {},
      });
    }

    const { data: rows, error: readError } = await supabase
      .from("saydi_tts_chunks")
      .select("chunk_index,text_content,spoken_text_override,spoken_text_override_meta,qc_repair_attempts,last_repair_request_id")
      .eq("job_id", jobId)
      .in("chunk_index", indices);
    if (readError) return json({ error: readError.message }, 500);

    const repaired: number[] = [];
    const exhausted: number[] = [];
    const idempotent: number[] = [];

    for (const row of rows ?? []) {
      const idx = Number(row.chunk_index);
      const attempts = Number(row.qc_repair_attempts ?? 0);
      if (String(row.last_repair_request_id ?? "") === requestId) {
        idempotent.push(idx);
        continue;
      }
      if (attempts >= maxAttempts) {
        exhausted.push(idx);
        continue;
      }

      const override = overrides.get(idx);
      const update: Record<string, unknown> = {
        status: "queued",
        error: null,
        qc_repair_attempts: attempts + 1,
        last_repair_request_id: requestId,
        updated_at: new Date().toISOString(),
      };
      if (override) {
        update.spoken_text_override = override.spoken_text;
        update.spoken_text_override_meta = {
          ...(row.spoken_text_override_meta ?? {}),
          ...override.meta,
          repair_request_id: requestId,
          canonical_text_preserved: true,
          applied_at: new Date().toISOString(),
        };
      }

      const { error: updateError } = await supabase
        .from("saydi_tts_chunks")
        .update(update)
        .eq("job_id", jobId)
        .eq("chunk_index", idx);
      if (updateError) return json({ error: updateError.message, chunk_index: idx }, 500);
      repaired.push(idx);
    }

    if (!repaired.length) {
      if (exhausted.length) {
        await supabase
          .from("saydi_tts_jobs")
          .update({ qc_status: "review", updated_at: new Date().toISOString() })
          .eq("id", jobId);
      }
      return json({
        ok: true,
        queued: false,
        repaired_indices: repaired,
        exhausted_indices: exhausted,
        idempotent_indices: idempotent,
        max_attempts: maxAttempts,
        review_required: exhausted.length > 0,
      });
    }

    const { count, error: countError } = await supabase
      .from("saydi_tts_chunks")
      .select("*", { count: "exact", head: true })
      .eq("job_id", jobId)
      .eq("status", "completed");
    if (countError) return json({ error: countError.message }, 500);

    const now = new Date().toISOString();
    const { error: jobResetError } = await supabase
      .from("saydi_tts_jobs")
      .update({
        status: "queued",
        completed_chunks: count ?? 0,
        worker_id: null,
        claimed_at: null,
        started_at: null,
        finished_at: null,
        output_file_name: null,
        error: null,
        qc_status: "pending",
        qc_issue_count: 0,
        qc_report: {},
        updated_at: now,
      })
      .eq("id", jobId);

    return jobResetError
      ? json({ error: jobResetError.message }, 500)
      : json({
          ok: true,
          queued: true,
          repair_request_id: requestId,
          repaired_indices: repaired,
          exhausted_indices: exhausted,
          idempotent_indices: idempotent,
          completed_chunks: count ?? 0,
          max_attempts: maxAttempts,
        });
  }

  return json({ error: "unknown action" }, 400);
});
