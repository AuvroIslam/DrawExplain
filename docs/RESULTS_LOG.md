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

Pending: filled in from `eval_lessons.py` (lesson pass rates per version) and `eval_grounding.py --gpu`.
