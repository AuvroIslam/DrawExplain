# DrawExplain results log

Every measurement taken while building the project, in the order it happened, so versions can be
compared. Grounding numbers come from `backend/scripts/eval_grounding.py` (ground-truth boxes, IoU);
lesson-quality numbers from `backend/scripts/eval_lessons.py` (fixed questions, automatic fact checks,
several runs per version). Single-run observations are marked as such: LLM output varies between runs.

## 1. Can the model place drawings by itself? (raw coordinate probe, 2026-10-09)

One clean synthetic network slide (1280x720), four boxes, the model asked for raw boxes, no CV.

| model | mean IoU | latency |
|---|---|---|
| gpt-4.1 | 0.48 | 4.1 s |
| gpt-4.1-mini | 0.34 | 2.2 s |
| gpt-5-mini | 0.35 | 4.8 s |
| gpt-5.4-mini | 0.95 | 2.2 s |
| gpt-5.4 | 0.97 | 3.8 s |
| gpt-5.5 | 0.99 | 4.1 s |

Takeaway: on a clean, sparse slide the newest models already localize well; the gap opens on dense
diagrams, photos and small text (section 3).

## 2. Perception (OCR + OpenCV, no LLM): recall of ground-truth elements

Recall@0.5 = share of ground-truth elements covered by some region with IoU >= 0.5.

**Version A** (OCR lines + stroke-hole shapes): on `network_basic`, shape boxes only 0.78-0.89 IoU
(connectors stretched them), 15 "shapes" for 4 boxes (words detected as blobs, all boxes merged into
one row). Fixed by B.

**Version B** (colour-edge rings, connector-proof thickness, opening for fills):

| image | clean | phone photo |
|---|---|---|
| network topology | 17/17 (0.956) | 15/17 (0.861) |
| dense architecture | 23/24 (0.925) | 20/24 (0.759) |
| flowchart with loop | 14/15 (0.868) | 14/15 (0.845) |
| formulas (kinematics) | 14/14 (0.953) | 13/14 (0.846) |
| free-body diagram | 15/18 (0.769) | 13/18 (0.636) |
| cell organelles | 13/16 (0.786) | 12/16 (0.711) |
| bar chart | 12/18 (0.737) | 14/18 (0.677) |

Hard fixtures: network_basic 6/6 (0.886), bullets + formula 11/12 (0.901), dark slide 16/16 (0.977),
dense diagram 40/40 (0.955), textbook page 14/14 (0.975), network photo 6/6 (0.886).

**Version C** (+ label rescue, + pocket rejection): flowchart 14/15 -> **15/15 (0.868 -> 0.952)**,
free-body 15/18 -> **16/18 (0.769 -> 0.818)**, no regressions on the other fixtures. On the real
Dijkstra lecture slide: edge weights read **5/14 -> 14/14**, shapes **14 (with pockets) -> 9 (exactly the
nodes)**; rescue costs ~0.2 s.

## 3. Grounding: do drawings land tightly on their target?

407 ground-truth targets in 24 images (synthetic clean / photo / dark / small sets + hard fixtures),
same model calls for every method. hit@t = share of targets with IoU >= t.

| version | model | method | mean IoU | hit@0.5 | hit@0.75 | hit@0.9 |
|---|---|---|---|---|---|---|
| baseline | gpt-5.4-mini | raw GPT coordinates | 0.592 | 65% | 34% | 15% |
| baseline | gpt-5.4-mini | model estimate with region marks | 0.552 | 62% | 31% | 11% |
| baseline | gpt-5.4-mini | chosen region ids only | 0.772 | 82% | 77% | 65% |
| fusion v1 (threshold ladder) | gpt-5.4-mini | fused | 0.816 | 87% | 81% | 69% |
| **fusion v2 (+ self-consistency gating)** | gpt-5.4-mini | fused | **0.829** | **89%** | **83%** | **69%** |
| baseline | gpt-4.1-mini | raw GPT coordinates | 0.111 | 5% | 0% | 0% |
| baseline | gpt-4.1-mini | chosen region ids only | 0.793 | 84% | 79% | 66% |
| fusion v1 (threshold ladder) | gpt-4.1-mini | fused | 0.645 | 67% | 63% | 53% |
| **fusion v2 (+ self-consistency gating)** | gpt-4.1-mini | fused | **0.812** | **86%** | **81%** | **68%** |

Notes:
- Fusion v1 lost to plain region ids with gpt-4.1-mini because it trusted that model's noisy box
  estimates; in its 120 fallback cases the region was right (IoU ~0.7) and the estimate wrong (~0.1).
  Gating on the response's own self-consistency fixed it (63% -> 81%) and helped gpt-5.4-mini too.
- Label promotion ("the Router" = the box, not the word): on the quick slide fused IoU 0.31 -> 0.89.
- Photo flattening run (`samples/eval/results_flatten.md`): not comparable, because photo ground truth
  is the bounding box of each warped shape, which penalises tight boxes after flattening.
- Full tables: `samples/eval/results.md`.

## 4. Lesson quality: does the tutor teach the procedure correctly?

Test case used throughout: the Dijkstra lecture slide (page 3 of the CS106B deck), question
"how to get the shortest path from A to E". The correct run: A=0; relax A: B=5, I=1, G=9, H=18; pick I:
C=7, **G 9->4**, E=3; pick E (3) = final; path A-I-E.

| version | what changed | observed (single runs) |
|---|---|---|
| L0 | "teach by doing" rule only | **compared nearby routes** and declared A-I-E; no initialization, no relaxation order (user's screenshot) |
| L1 | + "simulate algorithms faithfully" (Dijkstra used as the example) | run 1: init + relax A + pick I + settle E, but relaxed only I->E; run 2 (rule: relax every edge): complete, incl. C=7, G 9->4 |
| L2 | rule made general (no Dijkstra-specific text) | local run: complete (init, A, I incl. G 9->4, E final, path from predecessors); live run: correct order and answer but skipped B=5, H=18, G 9->4 |
| L3 | solver-backed simulation (graph read off the page, checked against OCR'd weights, Dijkstra run in code) | pending, see section 7 |

Same rule on other procedures (L2, single runs): flowchart "invalid twice" traced correctly
(read -> Valid? No -> error -> loop back, twice); TCP congestion window described the rules and wrote
"1->2->4->8" but did not invent a concrete threshold/timeout timeline.

Model choice for teaching (Dijkstra page 3, no question): gpt-5.4-mini started from B with wrong sums;
**gpt-5.5 traced A=0, I=1, G 1+3=4, E=3, F=7, D=23 correctly** at similar latency (17 s vs 15 s), so
gpt-5.5 became the lesson model.

## 5. Latency

| stage | local (16-core PC) | Render (1 CPU) |
|---|---|---|
| perception per page (OCR dominates) | 2-5 s | ~8 s |
| lesson, gpt-5.5, full | 15-20 s | similar |
| streamed: first token / first grounded step | 3.3 s / 5.7 s (vs 16.6 s full lesson) | first drawing ~23 s after Explain incl. scan |

## 6. Features verified end to end

- PDF reader mode: browsing pages 2->3->4->3 + arrow keys: **0 scans**, only page images fetched;
  Explain scans exactly 1 page; Replay of an explained page: **0 requests**.
- Lessons build on earlier pages: page 4 lesson showed "Builds on pages 1-3" and continued the trace.
- Real lecture robustness (8 TCP pages): 8/8 complete lessons, **128/130 drawings grounded by consensus**,
  self-consistency 0.91-1.00, 5/8 with a margin sketch of the procedure.
- Test suite: 58 backend tests passing (no network).

## 7. Upgrade results (solver-backed simulation, GPU perception)

### 7.1 Lesson quality on the three core cases (L3 = solver-backed simulation)

L3 (`12e5b41`): on a page that shows an algorithm or protocol, the problem is read off the page as JSON
(graph, array, protocol parameters), cross-checked against the pixels (edge weights against the OCR'd
labels next to each drawn line; pixels win) and run by deterministic code (Dijkstra, BFS, DFS, Prim,
Kruskal, sorts, binary search, TCP congestion window). The trace goes into the prompt as a VERIFIED
SIMULATION block; the model teaches it and draws it. Same 3 cases x 3 runs, same checks as section 4.

| case | L0 | L2 | **L3** |
|---|---|---|---|
| dijkstra_AtoE | 0.47 (0/3 all) | 0.93 (2/3 all) | **1.00 (3/3 all)** |
| tcp_cwnd | 0.73 (0/3 all) | 0.73 (0/3 all) | **1.00 (3/3 all)** |
| flowchart_invalid_twice | 1.00 (3/3 all) | 1.00 (3/3 all) | **1.00 (3/3 all)** |
| **all** | 0.73 (3/9) | 0.89 (5/9) | **1.00 (9/9)** |

- Dijkstra: every L3 run read 9/9 nodes and 14/14 edges off the slide, all 14 weights confirmed by
  the OCR'd labels. The extraction call takes 5-6 s before the lesson call, so it delays the first step
  by that much.
- TCP: the slide states the rules but no threshold; the solver assumes one (flagged as an example on the
  board) and the lesson walks a concrete timeline (1, 2, 4, 8, then +1 per RTT, timeout: threshold
  halved, window back to 1). L0 and L2 never produced a concrete threshold in 6 runs.
- One checker fix during this round: the TCP "timeout" check missed "resets CongWin to 1 MSS" and the
  board label `cwnd 12→1` (a false negative found by reading the lesson). The regex was widened and all
  versions were re-scored from their saved lessons: that was the only verdict that changed (L0/L2: none).
- In these runs the GPU service was not used (each run is a fresh process, which treats the GPU as cold
  and skips it); the L3 gain here is the solver alone.
- Two L3 runs first failed in perception (section 7.5) and were re-run after the fix (`0b90f8e`).

### 7.2 Broad benchmark: 17 new real pages, L2 vs L3

17 bench cases on real, openly licensed images (Wikimedia Commons; sources, licenses and edits in
`samples/bench/SOURCES.md`), each with a student question, a reference answer worked out by hand and
5 regex fact checks written before any lesson was run (`samples/bench/cases/*.json`). 2 runs per case
and version, L2 and L3 at the same time; per-case tables and every lesson in
`samples/eval/lessons_summary.md` and `samples/eval/lessons/<version>/transcripts.md`.

| topic | cases | L2 | L3 |
|---|---|---|---|
| graph algorithms (BFS/DFS, Prim, Dijkstra) | 3 | 0.93 (4/6 all) | 0.93 (4/6 all) |
| data structures (BST insert) | 1 | 1.00 (2/2 all) | 1.00 (2/2 all) |
| networking (TCP handshake, Go-Back-N vs Selective Repeat) | 2 | 0.90 (2/4 all) | 0.85 (1/4 all) |
| operating systems (SJF Gantt chart, LRU cache, deadlock graph) | 3 | 0.60 (2/6 all) | 0.57 (2/6 all) |
| math (quadratic, unit circle, Pythagoras, tangent line) | 4 | 0.80 (5/8 all) | 0.85 (4/8 all) |
| physics (two circuits, kinematics) | 3 | 0.97 (5/6 all) | 0.93 (4/6 all) |
| biology (Calvin cycle) | 1 | 1.00 (2/2 all) | 0.90 (1/2 all) |
| **all bench** | 17 | **0.85 (22/34 all)** | **0.84 (18/34 all)** |
| all 20 cases (core + bench) | 20 | 0.86 (27/43 all) | 0.87 (27/43 all) |

What it says:
- Outside the hard core pages, L3 is neither better nor worse. The solver ran on the three graph pages
  (Prim: 11/11 edges verified; BFS: 7/7 vertices; Dijkstra: 6 of 7 weights confirmed), but these small,
  clean graphs were already traced correctly by L2's simulate rule (BFS/DFS, Dijkstra 1.00 in both).
  Elsewhere no solver applies, and the versions differ by 1-3 checks in 34 runs: run-to-run noise.
- The failures are mostly reading errors, the same in both versions: misread Gantt bars (SJF: P7 read
  as waiting 6 instead of 5, average 2.21 instead of 2.36), a missed assignment arrow in the deadlock
  graph (3 of 4 runs concluded "no deadlock"), grid squares not counted (Pythagoras). Then facts the
  lessons leave out: Selective Repeat's cumulative Ack 5 after recovery (0 of 4 runs), why Prim skips
  the other edges (0 of 4), the general kinematics formula next to its substitution.
- Checker audit: every failed verdict of both versions was read against the lesson. One more false
  negative was found and fixed (Pythagoras: "4 by 4 ... 3 by 3" was not accepted); re-scoring both
  versions changed exactly that verdict. The table shows the final numbers, after the second audit
  round in 7.6 (L2 networking 0.85 -> 0.90, L3 operating systems 0.53 -> 0.57).
- Next target: the SJF chart prints every process as "P7(7, 3)" (arrival, burst), so code can compute
  the waiting times instead of the model reading them off the bars (section 7.6).

### 7.3 SAM 2.1 on the GPU: paired ablation (`samples/eval/results_gpu.md`)

Same run, same perception, same cached model responses; the only difference is SAM on or off. SAM is
called only for targets the CPU pipeline is unsure about (no consensus, figures); confident targets are
never touched.

| targets | n | mean IoU | hit@0.75 | hit@0.9 |
|---|---|---|---|---|
| low-confidence targets SAM refined | 19 | 0.483 -> **0.628** | 26% -> **47%** | 11% -> **32%** |
| all fused targets | 481 | 0.800 -> 0.806 | 77% -> 78% | 60% -> 61% |

SAM was asked about 30 targets and its mask was accepted for 19: 14 improved (up to +0.81 IoU, e.g. a
free-body weight arrow 0.11 -> 0.92, a nucleolus 0.64 -> 0.96), 3 lost at most 0.024, 2 stayed at 0
(the model had chosen the wrong region; SAM cannot fix a wrong choice). This run flattened the photo set,
so its absolute photo numbers are not comparable with section 3 (see its notes); the paired difference
is unaffected.

### 7.4 Formula OCR on the GPU (`samples/eval/latex_ocr.md`)

Lines that look like formulas are re-read by Qwen2-VL-2B on the GPU (pix2tex misread 2 of 4 kinematics
formulas in the first test) while the CPU stages continue; the LaTeX is appended to the region text
only when it adds something and agrees with the OCR text. 12 images, 27 formula lines: **14 LaTeX kept,
all improvements** (`S = ut + 12at2` -> `s=ut+\frac{1}{2}at^2`, `11π` -> `\frac{11\pi}{6}`,
`F=mxa` -> `F=m\times a`; one kept line has an I/l slip), 10 dropped as identical to the OCR, 3 dropped
as misreads (a box-coordinate hallucination, an empty array, an invented `=7π/12`). GPU time 0.4-2 s
per image when warm (hidden behind the CPU stages); a cold container needs ~25 s, so the API skips the
GPU until it is warm.

### 7.5 Robustness: a native OpenCV failure under load

- Symptom: 2 of 9 L3 lessons failed in perception with `cv2.error: Unknown C++ exception from OpenCV
  code` on the first colour conversion, again on the next call. Only seen while 3 lesson processes and
  the GPU grounding evaluation ran at once (one perception process peaks at ~1 GB commit; this PC had
  ~9 GB commit free). An earlier server process had shown the same and failed until restarted.
- Not reproducible in isolation: 50 fresh processes racing 6 threads on the first conversion, 12 building
  the OCR engine alongside OpenCV work, 30 fresh app processes scanning PDF pages 3 at a time (15 of them
  under an 8-thread perception load): 0 failures.
- Fix (`0b90f8e`), without a reproduction, so it removes every candidate: OpenCV runs sequentially
  (`cv2.setNumThreads(1)`; its native thread pool saved < 0.1 s per page, measured page times
  2.07 -> 2.10 s and 3.14 -> 3.00 s), a native OpenCV failure is retried once on a fresh thread
  (unit-tested), and the server finishes its warm-up before it accepts requests. The two failed lessons
  then ran 5/5 each; no failure since.

### 7.6 L4: CPU scheduling and page replacement solvers

L4 (`3e13ede`) adds two solver kinds, written because of the 7.2 failures: CPU scheduling (FCFS, SJF,
SRTF, round robin, priority) and page replacement (FIFO, LRU, OPT). The model reads the process table
or reference string; a process counts as confirmed only when its name, arrival and burst are printed
on one row of the page (an OCR line like "P7(7, 3)" or a table row), so axis numbers cannot confirm
anything. Unit tests reproduce the textbook answers (Silberschatz's FCFS 17, SJF 7, SRTF 6.5, RR 5.67
average waits; FIFO / LRU / OPT 15 / 12 / 9 faults) and both benchmark charts. Same 20 cases, same
checks, core 3 runs and bench 2 runs, GPU warm.

| | L0 | L2 | L3 | **L4** |
|---|---|---|---|---|
| 3 core cases | 0.73 (3/9 all) | 0.89 (5/9 all) | **1.00 (9/9 all)** | 0.98 (8/9 all) |
| 17 bench cases | - | 0.85 (22/34 all) | 0.84 (18/34 all) | **0.91 (23/34 all)** |
| all 20 | - | 0.86 (27/43 all) | 0.87 (27/43 all) | **0.93 (31/43 all)** |
| cs_sjf_gantt (scheduling solver) | - | 0.30 (0/2 all) | 0.40 (0/2 all) | **1.00 (2/2 all)** |
| cs_lru_cache (page replacement solver) | - | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |

How to read it:
- The effect of the new solvers is the SJF chart: every L2 and L3 lesson misread some bars (P7 waiting 6,
  average 2.21); both L4 lessons give all 14 waiting times, the total 33 and the average 2.36 exactly,
  with the simulation verified against the 14 printed rows. LRU was already right; now it is computed.
- Most of the other movement is run-to-run noise. On the math pages no solver runs, so L3 and L4 run
  identical code there, yet math went 0.85 -> 1.00 (Pythagoras 0.60 -> 1.00). With 2 runs per case a
  topic can move by ~0.15 by chance; only differences that are repeated in every run and explained by a
  code change (Dijkstra and TCP in 7.1, SJF here) should be read as effects.
- L4 core 0.98 vs L3 1.00: one TCP lesson shows "cwnd 1→2→4→8" on the board but never says the window
  starts at 1 MSS; the check asks for that sentence, every earlier run passed it, and it was not
  loosened after the fact.
- Still unsolved in every version: the deadlock graph (4 of the 6 L2-L4 lessons misread an arrow and
  concluded "no deadlock"), Selective Repeat's cumulative Ack 5 (0 of 6), why Prim skips the remaining
  edges (0 of 6).
- One L4 lesson (unit circle, run 2) hit the harness's time limit without producing a result; its rerun
  scored 5/5. Six earlier L2/L3 lessons failed on a 35-second network outage (OpenAI connection errors)
  and were rerun the same way.

Production check (live API on Render, same SJF chart, question "Why does P12 wait so long, and what is
the average waiting time?"): no simulation ran, and two lessons gave averages of 32/14 and 34/14 (the
exact value is 33/14 = 2.36). Cause: the benchmark question names the algorithm ("non-preemptive
Shortest Job First"); this one does not, the chart does not either, so the extraction returned no
variant and the solver was skipped. Fix (`420c645`): the extraction also reads the run order drawn on
the chart, and code runs every scheduler the data allows and keeps the one that reproduces that order.
On the real chart the model read the order exactly (P1..P6, P9, P8, P7, P10, P11, P13, P14, P12), only
SJF reproduces it, and the simulation is verified by the 14 printed rows and by the drawn order. A named
algorithm that the drawing contradicts is no longer marked verified.

The live server still ran no simulation. Reproduced with the server's own perception (fetched from the
API: its OCR differs slightly, so the marked image and region list do too): the model read the last three
bars in the wrong order (P12, P13, P14), so no algorithm reproduced the drawing exactly. Reading the
order of bars is the same weakness the solver exists to avoid, so exact matching was too strict. Fix:
when nobody names the algorithm, the one whose run order shares the longest common subsequence with the
drawing wins if it is clearly closest (here SJF 13/14 vs FCFS 12/14); its numbers are used but the
simulation is marked unverified. A drawing that resembles no algorithm still gives no simulation. A
named algorithm always runs as named, and the drawing only verifies it, because with 3-4 processes a
misread drawing can match the wrong algorithm by chance. Live after `cb94a25` (the API's
`/api/health` now reports the deployed commit): the same question gets "Simulation computed by code:
CPU scheduling, shortest job first", and the board reads P9 wait 2, P7 wait 5, P12 wait 8,
avg wait = 33/14 = 2.36, all exact (before the fixes: 32/14, 34/14, and P12 = 9).

Checker audit, second round (every failed verdict of L4, and the L2/L3 failures re-read with the same
rule: widen a check only when the lesson states the checked fact in other words, never when the fact is
missing, wrong or ambiguous). Widened: Go-Back-N "refuses frames 3 through 8", DFS "dives",
Pythagoras sides named in separate steps, "velocity rises from 0 to 10", deadlock "R3 gives / feeds an
instance to P1", Ohm "the drops add back to the battery". Re-scoring all versions changed 7 verdicts,
each read by hand: L2 +1, L3 +1, L4 +5. Kept as misses: "4.5 V across r" (lower-casing loses the r/R
distinction), cycles described in prose rather than as a path (the check asks for the path, L2 and L4
alike).
