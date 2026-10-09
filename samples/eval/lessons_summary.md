# Lesson-quality benchmark

Does the tutor teach the procedure on the page correctly? 20 fixed pages with a focus question each (the 3 core cases with hand-written checks, plus 17 bench cases from `samples/bench/cases/` with declarative regex checks); every run is a real lesson from `POST /api/lessons`, scored by automatic fact checks (`backend/scripts/eval_lessons.py`). Model gpt-5.5 (reasoning effort low); LLM cache off and a fresh data dir per run, so the runs are independent; run on 2026-10-09. Lessons were made 1, 2, 3 at a time per version.

| version | backend commit | what it adds | lessons | verdicts checked by hand |
|---|---|---|---|---|
| L0 | `3da1980` Add PDF reader mode with page context | teach-by-doing rule only (no simulation rule) | 9 ok / 9 | yes, all 45 (2026-10-09) |
| L2 | `6dbe976` Simulate procedures faithfully, deepen board colours | + general simulate-don't-shortcut rule | 43 ok / 43 | core: all 45 verdicts; bench: every failed verdict (2026-10-09) |
| L3 | `6085db5` Add results log of all measurements (+ uncommitted changes) (7 runs); `0b90f8e` Harden perception against native OpenCV failures (+ uncommitted changes) (36 runs) | solver-backed simulation + GPU perception | 43 ok / 43 | every failed verdict, core and bench (2026-10-09) |
| L4 | `3e13ede` Add CPU scheduling and page replacement solvers | + CPU scheduling and page replacement solvers | 43 ok / 43 | every failed verdict, core and bench (2026-10-10) |

## Overview: mean score (share of checks passed) and runs passing every check

| case | L0 | L2 | L3 | L4 |
|---|---|---|---|---|
| dijkstra_AtoE | 0.47 (0/3 all) | 0.93 (2/3 all) | 1.00 (3/3 all) | 1.00 (3/3 all) |
| tcp_cwnd | 0.73 (0/3 all) | 0.73 (0/3 all) | 1.00 (3/3 all) | 0.93 (2/3 all) |
| flowchart_invalid_twice | 1.00 (3/3 all) | 1.00 (3/3 all) | 1.00 (3/3 all) | 1.00 (3/3 all) |
| math_calvin_cycle | n/a | 1.00 (2/2 all) | 0.90 (1/2 all) | 1.00 (2/2 all) |
| cs_bst_insert | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 0.90 (1/2 all) |
| cs_bfs_dfs | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 0.90 (1/2 all) |
| cs_dijkstra_a_to_e | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |
| cs_prim_mst | n/a | 0.80 (0/2 all) | 0.80 (0/2 all) | 0.80 (0/2 all) |
| math_derivative_tangent | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |
| math_pythagoras | n/a | 0.30 (0/2 all) | 0.60 (0/2 all) | 1.00 (2/2 all) |
| math_quadratic | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |
| math_unit_circle | n/a | 0.90 (1/2 all) | 0.80 (0/2 all) | 1.00 (2/2 all) |
| cs_gbn_vs_sr | n/a | 0.80 (0/2 all) | 0.80 (0/2 all) | 0.70 (0/2 all) |
| cs_tcp_handshake | n/a | 1.00 (2/2 all) | 0.90 (1/2 all) | 1.00 (2/2 all) |
| cs_deadlock_rag | n/a | 0.50 (0/2 all) | 0.30 (0/2 all) | 0.50 (0/2 all) |
| cs_lru_cache | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |
| cs_sjf_gantt | n/a | 0.30 (0/2 all) | 0.40 (0/2 all) | 1.00 (2/2 all) |
| math_kinematics | n/a | 0.90 (1/2 all) | 0.80 (0/2 all) | 0.80 (0/2 all) |
| math_ohm_internal_resistance | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 0.90 (1/2 all) |
| math_parallel_meters | n/a | 1.00 (2/2 all) | 1.00 (2/2 all) | 1.00 (2/2 all) |
| **all cases** | **0.73 (3/9 all)** | **0.86 (27/43 all)** | **0.87 (27/43 all)** | **0.93 (31/43 all)** |

## Per topic: mean score and runs passing every check

Every run counts once (mean over the runs of the topic's cases); "k/n all" = runs passing every check. Core = the three original cases.

| topic | cases | L0 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| core | 3 | 0.73 (3/9 all, 33%) | 0.89 (5/9 all, 56%) | 1.00 (9/9 all, 100%) | 0.98 (8/9 all, 89%) |
| biology | 1 | n/a | 1.00 (2/2 all, 100%) | 0.90 (1/2 all, 50%) | 1.00 (2/2 all, 100%) |
| data structures | 1 | n/a | 1.00 (2/2 all, 100%) | 1.00 (2/2 all, 100%) | 0.90 (1/2 all, 50%) |
| graph algorithms | 3 | n/a | 0.93 (4/6 all, 67%) | 0.93 (4/6 all, 67%) | 0.90 (3/6 all, 50%) |
| math | 4 | n/a | 0.80 (5/8 all, 62%) | 0.85 (4/8 all, 50%) | 1.00 (8/8 all, 100%) |
| networking | 2 | n/a | 0.90 (2/4 all, 50%) | 0.85 (1/4 all, 25%) | 0.85 (2/4 all, 50%) |
| operating systems | 3 | n/a | 0.60 (2/6 all, 33%) | 0.57 (2/6 all, 33%) | 0.83 (4/6 all, 67%) |
| physics | 3 | n/a | 0.97 (5/6 all, 83%) | 0.93 (4/6 all, 67%) | 0.90 (3/6 all, 50%) |
| *all bench* | 17 | n/a | 0.85 (22/34 all, 65%) | 0.84 (18/34 all, 53%) | 0.91 (23/34 all, 68%) |
| **all** | 20 | **0.73 (3/9 all, 33%)** | **0.86 (27/43 all, 63%)** | **0.87 (27/43 all, 63%)** | **0.93 (31/43 all, 72%)** |

## What changed from L0 to L2

- **dijkstra_AtoE**: mean score 0.47 -> 0.93, all checks 0/3 -> 2/3; checks that moved: `init` 0/3 -> 3/3, `relax_A` 2/3 -> 3/3, `relax_I_all` 0/3 -> 2/3, `order` 2/3 -> 3/3.
- **tcp_cwnd**: mean score 0.73 -> 0.73, all checks 0/3 -> 0/3; no check moved.
- **flowchart_invalid_twice**: mean score 1.00 -> 1.00, all checks 3/3 -> 3/3; no check moved.

## What changed from L2 to L3

- **dijkstra_AtoE**: mean score 0.93 -> 1.00, all checks 2/3 -> 3/3; checks that moved: `relax_I_all` 2/3 -> 3/3.
- **tcp_cwnd**: mean score 0.73 -> 1.00, all checks 0/3 -> 3/3; checks that moved: `doubling` 2/3 -> 3/3, `concrete_threshold` 0/3 -> 3/3.
- **flowchart_invalid_twice**: mean score 1.00 -> 1.00, all checks 3/3 -> 3/3; no check moved.
- **math_calvin_cycle**: mean score 1.00 -> 0.90, all checks 2/2 -> 1/2; checks that moved: `fixation` 2/2 -> 1/2.
- **cs_bst_insert**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_bfs_dfs**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_dijkstra_a_to_e**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_prim_mst**: mean score 0.80 -> 0.80, all checks 0/2 -> 0/2; no check moved.
- **math_derivative_tangent**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **math_pythagoras**: mean score 0.30 -> 0.60, all checks 0/2 -> 0/2; checks that moved: `areas` 0/2 -> 1/2, `sides_3_4_5` 0/2 -> 1/2, `sum_9_16_25` 0/2 -> 1/2.
- **math_quadratic**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **math_unit_circle**: mean score 0.90 -> 0.80, all checks 1/2 -> 0/2; checks that moved: `point_150` 1/2 -> 0/2.
- **cs_gbn_vs_sr**: mean score 0.80 -> 0.80, all checks 0/2 -> 0/2; no check moved.
- **cs_tcp_handshake**: mean score 1.00 -> 0.90, all checks 2/2 -> 1/2; checks that moved: `third_seq_1024_established` 2/2 -> 1/2.
- **cs_deadlock_rag**: mean score 0.50 -> 0.30, all checks 0/2 -> 0/2; checks that moved: `p2_holds_r1_waits_r2` 1/2 -> 0/2, `deadlock_because_no_free_instance` 1/2 -> 0/2.
- **cs_lru_cache**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_sjf_gantt**: mean score 0.30 -> 0.40, all checks 0/2 -> 0/2; checks that moved: `waits_p7_p8_p9` 0/2 -> 1/2.
- **math_kinematics**: mean score 0.90 -> 0.80, all checks 1/2 -> 0/2; checks that moved: `formula` 1/2 -> 0/2.
- **math_ohm_internal_resistance**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **math_parallel_meters**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.

## What changed from L3 to L4

- **dijkstra_AtoE**: mean score 1.00 -> 1.00, all checks 3/3 -> 3/3; no check moved.
- **tcp_cwnd**: mean score 1.00 -> 0.93, all checks 3/3 -> 2/3; checks that moved: `starts_at_1` 3/3 -> 2/3.
- **flowchart_invalid_twice**: mean score 1.00 -> 1.00, all checks 3/3 -> 3/3; no check moved.
- **math_calvin_cycle**: mean score 0.90 -> 1.00, all checks 1/2 -> 2/2; checks that moved: `fixation` 1/2 -> 2/2.
- **cs_bst_insert**: mean score 1.00 -> 0.90, all checks 2/2 -> 1/2; checks that moved: `right_child_of_4` 2/2 -> 1/2.
- **cs_bfs_dfs**: mean score 1.00 -> 0.90, all checks 2/2 -> 1/2; checks that moved: `dfs_order` 2/2 -> 1/2.
- **cs_dijkstra_a_to_e**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_prim_mst**: mean score 0.80 -> 0.80, all checks 0/2 -> 0/2; no check moved.
- **math_derivative_tangent**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **math_pythagoras**: mean score 0.60 -> 1.00, all checks 0/2 -> 2/2; checks that moved: `areas` 1/2 -> 2/2, `sides_3_4_5` 1/2 -> 2/2, `sum_9_16_25` 1/2 -> 2/2, `rearrangement` 1/2 -> 2/2.
- **math_quadratic**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **math_unit_circle**: mean score 0.80 -> 1.00, all checks 0/2 -> 2/2; checks that moved: `point_150` 0/2 -> 2/2.
- **cs_gbn_vs_sr**: mean score 0.80 -> 0.70, all checks 0/2 -> 0/2; checks that moved: `gbn_discards_3_to_8` 2/2 -> 1/2.
- **cs_tcp_handshake**: mean score 0.90 -> 1.00, all checks 1/2 -> 2/2; checks that moved: `third_seq_1024_established` 1/2 -> 2/2.
- **cs_deadlock_rag**: mean score 0.30 -> 0.50, all checks 0/2 -> 0/2; checks that moved: `p1_holds_r3_waits_r1` 2/2 -> 1/2, `p2_holds_r1_waits_r2` 0/2 -> 2/2, `deadlock_because_no_free_instance` 0/2 -> 1/2.
- **cs_lru_cache**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.
- **cs_sjf_gantt**: mean score 0.40 -> 1.00, all checks 0/2 -> 2/2; checks that moved: `waits_p7_p8_p9` 1/2 -> 2/2, `p12_waits_8` 1/2 -> 2/2, `total_33` 0/2 -> 2/2, `average_2_36` 0/2 -> 2/2.
- **math_kinematics**: mean score 0.80 -> 0.80, all checks 0/2 -> 0/2; no check moved.
- **math_ohm_internal_resistance**: mean score 1.00 -> 0.90, all checks 2/2 -> 1/2; checks that moved: `internal_drop` 2/2 -> 1/2.
- **math_parallel_meters**: mean score 1.00 -> 1.00, all checks 2/2 -> 2/2; no check moved.

## dijkstra_AtoE

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3).

| version | runs | mean score | scores per run | all checks pass | init | relax_A | relax_I_all | order | answer | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 3 | 0.47 | 2/5, 2/5, 3/5 | 0/3 (0%) | 0/3 | 2/3 | 0/3 | 2/3 | 3/3 | 5.0 | 17.9 s |
| L2 | 3 | 0.93 | 5/5, 4/5, 5/5 | 2/3 (67%) | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | 5.3 | 19.3 s |
| L3 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 6.0 | 23.1 s |
| L4 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 6.0 | 23.2 s |

Verbatim excerpts (a typical run of each version: the step where it first works out E's distance; board texts after the narration):

- **L0**, run 1 (score 2/5), step 3 of 5: "Now we lock in I with total distance 1. From I to E costs 2 more, so A to I to E gives 1 + 2 = 3, which is already very strong." Board: `? -> e: +2` · `e: dist = 3`
- **L2**, run 1 (score 5/5), step 3 of 5: "Next we choose I, the smallest unfinished distance, 1. From I, E becomes 1 plus 2 equals 3, and G improves from 9 to 4; C would be 7, not our best route to E yet." Board: `1 ✓` · `? -> e: +2` · `e: ∞→3`
- **L3**, run 1 (score 5/5), step 4 of 6: "Now I has the smallest tentative distance, 1, so I becomes final. Relaxing I updates C to 7, E to 3, and improves G from 9 down to 4." Board: `1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
- **L4**, run 1 (score 5/5), step 4 of 6: "Now the smallest unvisited value is I at 1, so we finalize I. Relaxing from I improves C to 7, E to 3, and G from 9 down to 4." Board: `I 1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`

## tcp_cwnd

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31).

| version | runs | mean score | scores per run | all checks pass | starts_at_1 | doubling | concrete_threshold | additive | timeout | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 3 | 0.73 | 4/5, 4/5, 3/5 | 0/3 (0%) | 3/3 | 2/3 | 0/3 | 3/3 | 3/3 | 6.7 | 18.1 s |
| L2 | 3 | 0.73 | 4/5, 4/5, 3/5 | 0/3 (0%) | 3/3 | 2/3 | 0/3 | 3/3 | 3/3 | 6.0 | 17.0 s |
| L3 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 6.0 | 22.3 s |
| L4 | 3 | 0.93 | 4/5, 5/5, 5/5 | 2/3 (67%) | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 6.3 | 24.2 s |

## flowchart_invalid_twice

Question: "What happens if the input is invalid twice?" (samples/synthetic/clean/flowchart_loop.png).

| version | runs | mean score | scores per run | all checks pass | path | no_branch | loop_back | twice | exit | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 5.0 | 16.7 s |
| L2 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 5.7 | 18.9 s |
| L3 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 5.7 | 18.9 s |
| L4 | 3 | 1.00 | 5/5, 5/5, 5/5 | 3/3 (100%) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 5.3 | 16.3 s |

## math_calvin_cycle (biology)

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (samples/bench/images/math_calvin_cycle.png).

| version | runs | mean score | scores per run | all checks pass | fixation | reduction_cost | regeneration_cost | totals | gap_split | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.6 s |
| L3 | 2 | 0.90 | 4/5, 5/5 | 1/2 (50%) | 1/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 19.3 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 20.9 s |

## cs_bst_insert (data structures)

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (samples/bench/images/cs_bst_insert.png).

| version | runs | mean score | scores per run | all checks pass | left_at_8 | right_at_3_left_at_6 | right_child_of_4 | search_path | inorder_after | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 17.6 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.5 | 26.8 s |
| L4 | 2 | 0.90 | 4/5, 5/5 | 1/2 (50%) | 2/2 | 2/2 | 1/2 | 2/2 | 2/2 | 5.5 | 22.7 s |

## cs_bfs_dfs (graph algorithms)

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (samples/bench/images/cs_bfs_dfs.png).

| version | runs | mean score | scores per run | all checks pass | bfs_order | bfs_queue | bfs_levels | dfs_order | dfs_mechanism | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 21.2 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.5 | 30.0 s |
| L4 | 2 | 0.90 | 4/5, 5/5 | 1/2 (50%) | 2/2 | 2/2 | 2/2 | 1/2 | 2/2 | 6.0 | 24.7 s |

## cs_dijkstra_a_to_e (graph algorithms)

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (samples/bench/images/cs_dijkstra_a_to_e.png).

| version | runs | mean score | scores per run | all checks pass | b_stays_4 | d_is_5 | e_is_10 | path_a_c_e | via_d_is_12 | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.5 | 18.5 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 23.3 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 21.1 s |

## cs_prim_mst (graph algorithms)

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (samples/bench/images/cs_prim_mst.png).

| version | runs | mean score | scores per run | all checks pass | edges_ad_df_ab | edges_be_ce_eg | prim_order | total_39 | skips_cycle_edges | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 7.0 | 20.2 s |
| L3 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 7.0 | 27.8 s |
| L4 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 7.0 | 26.1 s |

## math_derivative_tangent (math)

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (samples/bench/images/math_derivative_tangent.png).

| version | runs | mean score | scores per run | all checks pass | point | derivative | slope | intercept | equation | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 16.3 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 18.3 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 15.9 s |

## math_pythagoras (math)

Question: "How does this picture prove the Pythagorean theorem?" (samples/bench/images/math_pythagoras_squares.jpg).

| version | runs | mean score | scores per run | all checks pass | areas | sides_3_4_5 | sum_9_16_25 | theorem | rearrangement | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.30 | 2/5, 1/5 | 0/2 (0%) | 0/2 | 0/2 | 0/2 | 2/2 | 1/2 | 5.0 | 15.3 s |
| L3 | 2 | 0.60 | 4/5, 2/5 | 0/2 (0%) | 1/2 | 1/2 | 1/2 | 2/2 | 1/2 | 6.0 | 21.2 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.5 | 21.0 s |

## math_quadratic (math)

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (samples/bench/images/math_quadratic_roots.png).

| version | runs | mean score | scores per run | all checks pass | set_zero | method | root_2 | root_minus_1 | graph_link | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 16.0 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 17.1 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 21.7 s |

## math_unit_circle (math)

Question: "What is sin(150°) and why?" (samples/bench/images/math_unit_circle.png).

| version | runs | mean score | scores per run | all checks pass | value_half | y_coordinate | point_150 | reference_30 | quadrant_sign | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.90 | 5/5, 4/5 | 1/2 (50%) | 2/2 | 2/2 | 1/2 | 2/2 | 2/2 | 5.0 | 13.5 s |
| L3 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 | 5.5 | 17.4 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.5 | 17.4 s |

## cs_gbn_vs_sr (networking)

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (samples/bench/images/cs_gbn_vs_sr.png).

| version | runs | mean score | scores per run | all checks pass | gbn_discards_3_to_8 | gbn_timeout_resends_from_2 | sr_buffers_3_to_5 | sr_nak_only_2 | sr_ack_5 | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 6.0 | 19.3 s |
| L3 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 6.0 | 22.3 s |
| L4 | 2 | 0.70 | 4/5, 3/5 | 0/2 (0%) | 1/2 | 2/2 | 2/2 | 2/2 | 0/2 | 6.5 | 21.4 s |

## cs_tcp_handshake (networking)

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (samples/bench/images/cs_tcp_handshake.png).

| version | runs | mean score | scores per run | all checks pass | client_syn_1023 | server_isn_2131691 | ack_1024_is_1023_plus_1 | final_ack_2131692 | third_seq_1024_established | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.7 s |
| L3 | 2 | 0.90 | 4/5, 5/5 | 1/2 (50%) | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 6.0 | 19.8 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.9 s |

## cs_deadlock_rag (operating systems)

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (samples/bench/images/cs_deadlock_rag.png).

| version | runs | mean score | scores per run | all checks pass | p1_holds_r3_waits_r1 | p2_holds_r1_waits_r2 | p3_holds_r2_waits_r3 | cycle | deadlock_because_no_free_instance | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.50 | 4/5, 1/5 | 0/2 (0%) | 2/2 | 1/2 | 1/2 | 0/2 | 1/2 | 6.0 | 18.5 s |
| L3 | 2 | 0.30 | 1/5, 2/5 | 0/2 (0%) | 2/2 | 0/2 | 1/2 | 0/2 | 0/2 | 6.0 | 20.0 s |
| L4 | 2 | 0.50 | 1/5, 4/5 | 0/2 (0%) | 1/2 | 2/2 | 1/2 | 0/2 | 1/2 | 5.0 | 16.5 s |

## cs_lru_cache (operating systems)

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (samples/bench/images/cs_lru_cache.png).

| version | runs | mean score | scores per run | all checks pass | e_evicts_a | d_hit_updated | f_evicts_b | six_misses | one_hit | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.2 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 17.9 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 20.4 s |

## cs_sjf_gantt (operating systems)

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (samples/bench/images/cs_sjf_gantt.png).

| version | runs | mean score | scores per run | all checks pass | order_p9_p8_p7 | waits_p7_p8_p9 | p12_waits_8 | total_33 | average_2_36 | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.30 | 2/5, 1/5 | 0/2 (0%) | 2/2 | 0/2 | 1/2 | 0/2 | 0/2 | 6.0 | 19.3 s |
| L3 | 2 | 0.40 | 2/5, 2/5 | 0/2 (0%) | 2/2 | 1/2 | 1/2 | 0/2 | 0/2 | 6.0 | 25.5 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 8.0 | 32.8 s |

## math_kinematics (physics)

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (samples/bench/images/math_kinematics_slide.png).

| version | runs | mean score | scores per run | all checks pass | formula | substitution | final_velocity | distance_25 | graph_area | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 0.90 | 4/5, 5/5 | 1/2 (50%) | 1/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.5 | 14.0 s |
| L3 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 18.6 s |
| L4 | 2 | 0.80 | 4/5, 4/5 | 0/2 (0%) | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 5.0 | 15.9 s |

## math_ohm_internal_resistance (physics)

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (samples/bench/images/math_ohm_internal_resistance.jpg).

| version | runs | mean score | scores per run | all checks pass | total_resistance | current | internal_drop | terminal_voltage | kirchhoff | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 17.7 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 17.8 s |
| L4 | 2 | 0.90 | 5/5, 4/5 | 1/2 (50%) | 2/2 | 2/2 | 1/2 | 2/2 | 2/2 | 6.0 | 19.0 s |

## math_parallel_meters (physics)

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (samples/bench/images/math_parallel_meters.png).

| version | runs | mean score | scores per run | all checks pass | topology | a2_r1_branch | a3_r2r3_branch | a1_total | v3_v4_split | mean steps | mean lesson latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 0 (0 failed) | n/a | | | | | | | | | |
| L2 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.5 s |
| L3 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 18.8 s |
| L4 | 2 | 1.00 | 5/5, 5/5 | 2/2 (100%) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 6.0 | 17.9 s |

## How the checks work

Each check is a small regex function in `backend/scripts/eval_lessons.py`, run on the step narrations, the text written on the board (labels and arrow captions; a note attached to a lettered graph node is read with the letter first, e.g. `b: ∞ -> 5`, and `?` marks an arrow end whose region has no one-letter OCR text: on the Dijkstra slide the OCR does not read the I inside its circle) and the margin sketch (node labels, not Mermaid ids), lower-cased, with arrows (→, -->, =>) normalised to `->`. Score = checks passed / checks of the case. Each run file stores the matched evidence of every check, so a pass or fail can be audited (the versions table says which versions had every verdict checked by hand). Step titles, summary and quiz are not checked.

- **dijkstra_AtoE**
  - `init`: The other vertices start at infinity ("∞", "infinity") AND the source A starts at 0.
  - `relax_A`: Relaxing A's edges gives B 5, G 9, H 18 and I 1: at least 3 of these 4 (node, value) pairs are stated.
  - `relax_I_all`: Relaxing I's edges is complete, not only the edge towards E: C 7 AND G improves 9 -> 4 AND E 3.
  - `order`: I is picked / settled / marked done before E is declared final (Dijkstra's own processing order).
  - `answer`: The final step states the path A-I-E ("A -> I -> E", "A to I to E", both hops "A to I" and "I to E", or backwards "E via I, I from A") AND the total 3.
- **tcp_cwnd**
  - `starts_at_1`: The congestion window starts at 1 MSS: a start word, then "1 MSS" / "cwnd = 1" in the same sentence.
  - `doubling`: An explicit doubling sequence of 3+ numbers in one sentence or board note: "1, 2, 4", "2 -> 4 -> 8".
  - `concrete_threshold`: A concrete numeric ssthresh / threshold value is used ("threshold = 8", "ssthresh of 16 MSS"); "½ CongWin" alone does not count.
  - `additive`: After the threshold the window grows linearly, +1 per RTT: "+1 MSS per RTT", "+1/RTT", "one segment every round trip", "over one RTT (or one full window of ACKs) it grows by 1 MSS", a +1 sequence such as "8 -> 9 -> 10", or "linear" with "+1" in one sentence.
  - `timeout`: On a timeout the threshold is halved AND cwnd goes back to 1, both stated in the step(s) that mention the timeout.
- **flowchart_invalid_twice**
  - `path`: The lesson walks from Read input into the Valid? decision (in that order, within one step).
  - `no_branch`: An invalid input takes the No branch to Show error (invalid / No, then error, in one sentence).
  - `loop_back`: After the error the flow returns to Read input ("back to Read input", "loops to Read input", "read input again").
  - `twice`: The second attempt / second error is shown explicitly ("second try", "2nd error", "attempt 2", "invalid again", "another error"); the question's own word "twice" does not count.
  - `exit`: Only a valid input (the Yes branch) reaches Process data / End: a condition word, valid / yes, then process / end / exit in one sentence ("only a Yes ... Process data", "once it is valid ... End").

Bench cases (`samples/bench/cases/<case>.json`) use declarative checks instead: case-insensitive regexes over the same normalised text (without the node-letter prefix). A check passes when every `all` regex matches and at least `min_any` (default 1) of its `any` regexes match. Each case file also holds a reference answer and the image's source and license.

- **math_calvin_cycle** (biology)
  - `fixation`: Fixation: 3 CO₂ (with 3 ribulose-1,5-bisphosphate) give 6 3-phosphoglycerate.
  - `reduction_cost`: Reduction phase uses 6 ATP and 6 NADPH.
  - `regeneration_cost`: Regenerating RuBP uses 3 more ATP.
  - `totals`: Total per 3 CO₂: 9 ATP (and 6 NADPH).
  - `gap_split`: Of the 6 GAP, 5 are recycled (into 3 ribulose-5-phosphate / RuBP) and 1 leaves as the net product.
- **cs_bst_insert** (data structures)
  - `left_at_8`: At the root: 5 < 8, so go left (to 3).
  - `right_at_3_left_at_6`: Then 5 > 3 -> right to 6, and 5 < 6 -> left to 4.
  - `right_child_of_4`: 5 > 4 and 4's right slot is empty: 5 becomes the right child of 4.
  - `search_path`: The path followed is 8 -> 3 -> 6 -> 4 (then 5 is attached below 4).
  - `inorder_after`: In-order traversal afterwards: 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
- **cs_bfs_dfs** (graph algorithms)
  - `bfs_order`: States the BFS order A, B, C, E, D, F, G.
  - `bfs_queue`: Explains that BFS uses a (FIFO) queue.
  - `bfs_levels`: Explains the levels: A's neighbours B, C, E (distance 1) come before D, F, G (distance 2).
  - `dfs_order`: States the DFS order A, B, D, F, E, C, G.
  - `dfs_mechanism`: Explains how DFS differs: a stack / recursion, going deep first and backtracking.
- **cs_dijkstra_a_to_e** (graph algorithms)
  - `b_stays_4`: B's distance is 4 (direct edge); the route via C (2 + 5 = 7) is worse.
  - `d_is_5`: D's distance is 5, via C (2 + 3).
  - `e_is_10`: E's distance is 10 (2 + 8).
  - `path_a_c_e`: The shortest path to E is A -> C -> E.
  - `via_d_is_12`: Rejects reaching E through D: 5 + 7 = 12 is longer than 10.
- **cs_prim_mst** (graph algorithms)
  - `edges_ad_df_ab`: The tree contains A-D (5), D-F (6) and A-B (7).
  - `edges_be_ce_eg`: The tree contains B-E (7), C-E (5) and E-G (9).
  - `prim_order`: Adds the edges in Prim's order from A: A-D, D-F, A-B, B-E, C-E, E-G.
  - `total_39`: Total weight 39.
  - `skips_cycle_edges`: Explains why other edges are skipped: both ends already in the tree / they would form a cycle.
- **math_derivative_tangent** (math)
  - `point`: Point of tangency (1, 1): f(1) = 1.
  - `derivative`: Differentiates: f'(x) = 2x.
  - `slope`: Slope at a = 1: m = f'(1) = 2.
  - `intercept`: Intercept b = 1 − 2 = −1.
  - `equation`: Final tangent line y = 2x − 1.
- **math_pythagoras** (math)
  - `areas`: Counts the three squares: 9, 16 and 25 unit squares.
  - `sides_3_4_5`: Gives the side lengths 3, 4 and 5 (3² + 4² = 5², '3-4-5', '4 by 4' and '3 by 3').
  - `sum_9_16_25`: Adds the two small squares: 9 + 16 = 25.
  - `theorem`: States the theorem: a² + b² = c² (or in words: the squares on the legs add up to the square on the hypotenuse).
  - `rearrangement`: Explains the colours: the 16 red and 9 yellow unit squares together fill the big square on the hypotenuse.
- **math_quadratic** (math)
  - `set_zero`: Sets y = 0, i.e. x² − x − 2 = 0.
  - `method`: Factors to (x − 2)(x + 1) = 0, or uses the quadratic formula with discriminant 1 + 8 = 9 (x = (1 ± 3)/2).
  - `root_2`: States the root x = 2.
  - `root_minus_1`: States the root x = −1.
  - `graph_link`: Connects the roots to the graph: the x-intercepts, where the parabola crosses the x-axis ((−1, 0) and (2, 0)).
- **math_unit_circle** (math)
  - `value_half`: States sin(150°) = 1/2 (0.5, one half).
  - `y_coordinate`: Explains that the sine is the y-coordinate (height) of the point on the unit circle.
  - `point_150`: Reads the 150° point (−√3/2, 1/2) (x negative: cos 150° = −√3/2).
  - `reference_30`: Relates 150° to 30°: reference angle 180° − 150° = 30°, sin 150° = sin 30° (mirror image).
  - `quadrant_sign`: 150° is in the second quadrant (upper left), where the sine (y) is positive.
- **cs_gbn_vs_sr** (networking)
  - `gbn_discards_3_to_8`: (a) The Go-Back-N receiver discards frames 3-8.
  - `gbn_timeout_resends_from_2`: (a) After the timeout the sender goes back and retransmits 2, 3, ..., 8.
  - `sr_buffers_3_to_5`: (b) The Selective Repeat receiver buffers (keeps) frames 3, 4, 5.
  - `sr_nak_only_2`: (b) The receiver sends NAK 2 and only frame 2 is retransmitted.
  - `sr_ack_5`: (b) Once 2 arrives, frames 2-5 are delivered in order and the receiver sends Ack 5.
- **cs_tcp_handshake** (networking)
  - `client_syn_1023`: Segment 1: the client's SYN carries its initial sequence number 1023.
  - `server_isn_2131691`: Segment 2 (SYN-ACK): the server picks its own initial sequence number 2131691.
  - `ack_1024_is_1023_plus_1`: Ack number 1024 = 1023 + 1: the SYN uses one sequence number, 1024 is the next byte expected.
  - `final_ack_2131692`: Segment 3: the client acknowledges with Ack number 2131692 = 2131691 + 1.
  - `third_seq_1024_established`: Segment 3 has Seq 1024 and completes the handshake (connection established, data can flow).
- **cs_deadlock_rag** (operating systems)
  - `p1_holds_r3_waits_r1`: P1 holds an instance of R3 and requests R1.
  - `p2_holds_r1_waits_r2`: P2 holds R1 (and an R3 instance) and requests R2.
  - `p3_holds_r2_waits_r3`: P3 holds R2 and requests R3.
  - `cycle`: Identifies the cycle P1 -> R1 -> P2 -> R2 -> P3 -> R3 -> P1 (or P2 -> R2 -> P3 -> R3 -> P2, or the wait-for cycle P1 -> P2 -> P3 -> P1).
  - `deadlock_because_no_free_instance`: Concludes deadlock: both R3 instances are held by blocked processes, nothing is free, no process can proceed.
- **cs_lru_cache** (operating systems)
  - `e_evicts_a`: E replaces A because A (time 0) is the least recently used.
  - `d_hit_updated`: The second access to D is a hit and D's last-use time is updated (3 -> 5).
  - `f_evicts_b`: F replaces B, which (time 1) is now the least recently used.
  - `six_misses`: 6 misses (A, B, C, D, E, F).
  - `one_hit`: 1 hit (the second D), hit ratio 1/7.
- **cs_sjf_gantt** (operating systems)
  - `order_p9_p8_p7`: At t=9 the shortest waiting job runs first: P9 (1), then P8 (2), then P7 (3).
  - `waits_p7_p8_p9`: P9 waits 2, P8 waits 3, P7 waits 5.
  - `p12_waits_8`: P12 waits 8 (runs 21-24) because the shorter P13 and P14 arrive at 17 and go first.
  - `total_33`: Total waiting time 33.
  - `average_2_36`: Average waiting time 33/14 = 2.36.
- **math_kinematics** (physics)
  - `formula`: Uses s = ut + ½at².
  - `substitution`: Substitutes the numbers: ½ × 2 × 5² (u t = 0).
  - `final_velocity`: Final velocity v = u + at = 10 m/s.
  - `distance_25`: Answer: s = 25 m.
  - `graph_area`: Checks with the v–t graph: the area under it (triangle ½ × 5 × 10) is the same 25 m.
- **math_ohm_internal_resistance** (physics)
  - `total_resistance`: Adds the series resistances: r + R = 3 + 5 = 8 Ω.
  - `current`: Ohm's law for the whole loop: I = ε/(R + r) = 12/8 = 1.5 A.
  - `internal_drop`: Voltage lost inside the battery: Ir = 1.5 × 3 = 4.5 V.
  - `terminal_voltage`: Voltage across R by Ohm's law: IR = 1.5 × 5 = 7.5 V.
  - `kirchhoff`: The drops add up to the EMF: 4.5 V + 7.5 V = 12 V (or 12 − 4.5 = 7.5).
- **math_parallel_meters** (physics)
  - `topology`: R2 and R3 are in series (2 + 4 = 6 Ω) on a branch in parallel with R1.
  - `a2_r1_branch`: A2 (the R1 branch) reads 12/4 = 3 A.
  - `a3_r2r3_branch`: A3 (the R2–R3 branch) reads 12/6 = 2 A.
  - `a1_total`: A1 (total current) reads 3 + 2 = 5 A.
  - `v3_v4_split`: The 12 V splits on the series branch: V3 = 2 × 2 = 4 V and V4 = 2 × 4 = 8 V.

## Files

- `samples/eval/lessons/L0/`: every lesson (`<case>_run<k>.json`: lesson JSON, latency, region texts, checks with evidence), `results.json` (scores), `transcripts.md` (all lessons, readable)
- `samples/eval/lessons/L2/`: every lesson (`<case>_run<k>.json`: lesson JSON, latency, region texts, checks with evidence), `results.json` (scores), `transcripts.md` (all lessons, readable)
- `samples/eval/lessons/L3/`: every lesson (`<case>_run<k>.json`: lesson JSON, latency, region texts, checks with evidence), `results.json` (scores), `transcripts.md` (all lessons, readable)
- `samples/eval/lessons/L4/`: every lesson (`<case>_run<k>.json`: lesson JSON, latency, region texts, checks with evidence), `results.json` (scores), `transcripts.md` (all lessons, readable)

Reproduce: `backend/.venv/Scripts/python backend/scripts/eval_lessons.py --backend <worktree>/backend --version <label> --runs 3 --all`, then `--summary L0 L2 L3 L4`; `--rescore` re-scores saved lessons for free.
