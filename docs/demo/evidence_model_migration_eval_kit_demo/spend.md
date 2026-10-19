# xAI spend (this video: model_migration_eval_kit_demo_en)
- TTS (voice leo, speed 1.08): 1678 characters (first draft, discarded as too long) + 1294 characters (second draft) + 663 characters (3 scenes re-generated for pronunciation) = 3635 characters x US$15 / 1M = about US$0.055. Estimated from character counts at the listed rate; the API response did not include a cost field.
- STT check (grok-voice-transcribe-2.0, US$0.10/h): 2 transcriptions of about 99 s = about US$0.006 (estimated from duration).
- Live model calls (LLM): none. No `compare-live`, no `LIVE_MODE`, `MAX_LIVE_SPEND_USD` not needed. The run is fully offline; the badge on screen says so. XAI_API_KEY was removed from the terminal environment of the take and was not written to any file.
- Total for this video: about US$0.06 (estimated).
