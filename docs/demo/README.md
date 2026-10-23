# Narrated offline demo

[model_migration_eval_kit_demo_en.mp4](model_migration_eval_kit_demo_en.mp4) is a narrated recording of a real offline run (about 99 seconds). The narration is English. The voice is text-to-speech generated with xAI. Subtitles are [English](model_migration_eval_kit_demo_en.en.srt). The spoken script is [model_migration_eval_kit_demo_en_script.md](model_migration_eval_kit_demo_en_script.md). The video file was not edited.

The take was recorded on a fresh clone of `main` at `12c9659836ab`, package 0.2.2. It is fully offline. No live model call and no network call was made for this video. The badge on screen says OFFLINE. The model results are simulated by the fake providers. The cost figures use [EST] prices. The NO_GO is built into `fake-new` on purpose. It is not a difference between two real models.

Every number on screen or in the narration comes from that run and is mapped in [evidence_model_migration_eval_kit_demo/number_trace.md](evidence_model_migration_eval_kit_demo/number_trace.md). Spoken numbers are written in words. The README records its measurements on Python 3.12.3. This take ran on Python 3.12.15 with package 0.2.2. The report written by the run is kept at [evidence_model_migration_eval_kit_demo/sources/report.md](evidence_model_migration_eval_kit_demo/sources/report.md). On the day of the take it matched the then-committed example report. Simulated cost in that snapshot was measured on the original Spanish ticket text on 2026-10-17. The current [docs/example-report.md](../example-report.md) was re-measured on 2026-10-23, package 0.2.3, after the tickets were translated to English. Quality rows match the recording. Simulated cost follows character length, so the current report is the later measurement. The live 55/63 and 56/63 quoted in the narration were also measured on that Spanish text and were not re-run.

## Commands

The recorded terminal is [evidence_model_migration_eval_kit_demo/terminal_take/terminal_dump.txt](evidence_model_migration_eval_kit_demo/terminal_take/terminal_dump.txt). The prompt is `lab $`. The scene table in the number trace names the same commands. What each one printed is in that trace.

Scene A:

```text
python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17 --out out/demo 2>&- | sed -n 3p
```

Scene B:

```text
sed -n '/^## Quality by slice/,/^## Behaviour/p' out/demo/report.md | grep '^|'
```

Scene C:

```text
awk -F'|' '/^\| (slice|paired|no_new|cost)/{gsub(/ /,"",$2);gsub(/ /,"",$3);print $2,$3}' out/demo/report.md
grep -E '^- (Tickets where|Exact)' out/demo/report.md | cut -c1-124
grep -E '^\| (Cost per run|Savings|Harmful)' out/demo/report.md
```

Scene D:

```text
for p in fake-new-close fake-new-flat fake-new-degraded; do
echo -n "$p: "
python -m migration_eval compare --old fake-old --new $p --runs 10 --today 2026-10-17 --out out/$p 2>&- | grep -o 'Decision.*'
done
```

Scene E:

```text
python -m migration_eval eval-regression 2>&- | sed -n 1,6p; echo exit=${PIPESTATUS[0]}
```

Scene F reads README text. It is not a run:

```text
sed -n '17p' README.md | fold -s -w 126
sed -n '106p;108p' README.md | fold -s -w 126
```

## Live self-compare quoted in the video

The narration says fifty-five and fifty-six of sixty-three. That is pass 55/63 on the old side and 56/63 on the new side, the same model on both sides. It is quoted from the README in scene F. It was measured on the original Spanish ticket text on 2026-10-17 and was not re-run for this video. It is noise, not evidence, and it says nothing about a migration.

## Spend

[evidence_model_migration_eval_kit_demo/spend.md](evidence_model_migration_eval_kit_demo/spend.md) is text-to-speech only. The figures there are estimated. There were no live model calls.

## Evidence files

- [number_trace.md](evidence_model_migration_eval_kit_demo/number_trace.md) maps every number on screen or in the narration.
- [spend.md](evidence_model_migration_eval_kit_demo/spend.md) is the text-to-speech estimate for this video.
- [stt_transcript.txt](evidence_model_migration_eval_kit_demo/stt_transcript.txt) is the speech-to-text check.
- [terminal_take/](evidence_model_migration_eval_kit_demo/terminal_take/) holds `terminal_dump.txt`, `take.json`, and `take.log`.
- [sources/](evidence_model_migration_eval_kit_demo/sources/) holds the report from the run (`report.md`, `report.json`), `CLONE_HEAD.txt`, and the README from that clone.
- [code/narration.json](evidence_model_migration_eval_kit_demo/code/narration.json) and [code/timestamps.json](evidence_model_migration_eval_kit_demo/code/timestamps.json) are the narration and the take timing.
