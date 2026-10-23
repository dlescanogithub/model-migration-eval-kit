# Number trace: model_migration_eval_kit_demo_en.mp4

Every number on screen or in the narration, with its source. Asserted by script (`code/build_trace.py`) at build time against the take recording (`take.json`), the repo README (clone of main, HEAD 12c9659836ab, package 0.2.2, run on Python 3.12.15) and the report written by the run (`sources/report.md`). On the day of the take that report matched the then-committed `docs/example-report.md`. Spoken numbers are written in words. No live model call and no network call was made for this video; the badge says OFFLINE.

The cost figures below (0.069515, 0.014914, savings ratio 0.7855) and the live 55/63 and 56/63 were measured on the original Spanish ticket text on 2026-10-17. They were not re-run for the English tickets. The video file was not edited. Quality figures do not read ticket wording; a 2026-10-23 offline re-measure on the English tickets matched them. Simulated cost follows character length, so the current `docs/example-report.md` is that later measurement, not this snapshot.

## Scene commands (all real, offline, `lab $` prompt, no network)
| Scene | Command shown | What it prints |
|---|---|---|
| A | `python -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17 --out out/demo \| sed -n 3p` | `- Decision: **NO_GO**` |
| B | `sed ... out/demo/report.md \| grep '^|'` | slice table |
| C | `awk ...`, `grep ...` over `out/demo/report.md` | gates, paired test, cost rows |
| D | loop of the same `compare` over `fake-new-close`, `fake-new-flat`, `fake-new-degraded` | decisions |
| E | `python -m migration_eval eval-regression \| sed -n 1,6p; echo exit=${PIPESTATUS[0]}` | forced NO_GO, `exit=1` |
| F | `sed -n '17p'` and `sed -n '106p;108p'` on README.md | README text (not a run) |

## Numbers
| On screen / narration | Value | Source |
|---|---|---|
| "sixty-three synthetic tickets" | n=63 (ticket is the unit, 10 seed repeats collapsed) | `sources/report.md` "Tickets (unit of analysis, n): 63"; README intro |
| Decision NO_GO | NO_GO | compare output, `sources/report.md` line 3 |
| Edge slice "one point zero to point six six six seven", "thirty-three points, on twenty-one tickets", "cap is five" | 1.0000 -> 0.6667, drop 33.33, n=21, cap 5.00 | slice table in take; `sources/report.md` (Quality by slice, Gates `slice:edge`); README line 17 |
| "Happy and adversarial stay inside" (on screen in the slice table and gates, not narrated) | happy 3.57, adversarial 0.00 (cap 5) | slice table / gates |
| Overall (on screen only) | 0.8730, drop 12.70, bootstrap [-0.2222, -0.0476] | slice table |
| "Two gates fail: the edge slice, and the paired test" | `slice:edge no`, `paired_regression no`; others yes | gates (awk over `report.md`) |
| "Eight tickets fail only on the new provider, none only on the old" | 8 and 0 | `report.md` "Paired test" lines |
| p-value (on screen) | 0.00390625 (exact one-sided McNemar, n=63) | `report.md` |
| "Harmful tickets: zero" | 0 old, 0 new | `report.md` Cost and latency table |
| "Cost falls from about seven cents to one and a half, simulated, on [EST] prices" | 0.069515 -> 0.014914 USD per run (about 6.95 and 1.49 cents), [EST] prices, simulated | `report.md`; README Results table |
| "about seventy-nine percent" (closing slide) | savings ratio 0.7855 (78.55 percent) | `report.md`; README Business case |
| Other profiles: close GO, flat NEED_HUMAN, degraded NO_GO | GO / NEED_HUMAN / NO_GO | loop output in take; README table "Other profiles" |
| "Fourteen harmful tickets, the gate goes red, exit one" | harmful tickets old=0 new=14; `exit=1` | `eval-regression` output in take |
| "fifty-five and fifty-six of sixty-three" (live self-compare) | 55/63 old, 56/63 new, same model both sides | **README text only, not re-run** (README "Live compare", 2026-10-17, model grok-4.20-0309-non-reasoning); badge says README text, not re-run |

## Closing slide
| Item | Source |
|---|---|
| How to decide, steps 1 to 4 | README "How to decide in hours" |
| Not covered | README "Not covered yet" |
| Simulated bill per pass 0.069515 -> 0.014914, ratio 0.7855, prices [EST], latency simulated | `report.md`, README Business case |

## Caveats not in the video
- The video does not re-run the live compare. README live numbers (55/63, 56/63) are a same-model self-compare and say nothing about migrations.
- README records measurements on Python 3.12.3; this take ran on Python 3.12.15 with package 0.2.2. `sources/report.md` is the report from the take. It matched the committed example on that day. The current example report was re-measured on 2026-10-23 after the tickets were translated to English.
- Cost rows and the live 55/63 and 56/63 in this trace were measured on the original Spanish ticket text on 2026-10-17.
- Latency and prices are simulated / [EST]; the NO_GO is built into `fake-new` and is not a difference between two real models.
