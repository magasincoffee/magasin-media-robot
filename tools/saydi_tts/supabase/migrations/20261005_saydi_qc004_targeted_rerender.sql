-- SAYDI-QC-004: targeted pronunciation/prosody repair metadata.
-- Canonical text_content remains immutable; only the derived spoken override changes.

alter table public.saydi_tts_chunks
  add column if not exists spoken_text_override text,
  add column if not exists spoken_text_override_meta jsonb not null default '{}'::jsonb,
  add column if not exists qc_repair_attempts integer not null default 0,
  add column if not exists last_repair_request_id text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'saydi_tts_chunks_qc_repair_attempts_nonnegative'
      and conrelid = 'public.saydi_tts_chunks'::regclass
  ) then
    alter table public.saydi_tts_chunks
      add constraint saydi_tts_chunks_qc_repair_attempts_nonnegative
      check (qc_repair_attempts >= 0);
  end if;
end
$$;

comment on column public.saydi_tts_chunks.spoken_text_override is
  'Derived TTS-only spoken form for targeted QC repair. Canonical text_content must not be overwritten.';
comment on column public.saydi_tts_chunks.spoken_text_override_meta is
  'QC repair provenance: reason, lexicon version, applied overrides, source audio hash, etc.';
comment on column public.saydi_tts_chunks.qc_repair_attempts is
  'Bounded automatic repair attempts. Edge API enforces the active maximum.';
comment on column public.saydi_tts_chunks.last_repair_request_id is
  'Idempotency key for the most recent targeted repair request.';
