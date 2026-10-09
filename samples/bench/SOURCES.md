# Benchmark image sources

Every image in `images/`, where it came from, its license and author.

## Math / physics / biology cases (`cases/math_*.json`)

| file | source URL | license | author |
|---|---|---|---|
| images/math_quadratic_roots.png | https://commons.wikimedia.org/wiki/File:Polynomialdeg2.svg (1280 px PNG render) | Public domain | Original hand-drawn version: N.Mori; updated version: Rubber Duck |
| images/math_unit_circle.png | https://commons.wikimedia.org/wiki/File:Unit_circle_angles_color.svg (1280 px PNG render) | Public domain | Jim.belk |
| images/math_pythagoras_squares.jpg | https://commons.wikimedia.org/wiki/File:Pythagorean_theorem.jpg (original file, identical SHA-1) | Public domain | Ntozis |
| images/math_derivative_tangent.png | https://commons.wikimedia.org/wiki/File:Graph_of_parabola_and_tangent_line.png (original size, re-encoded) | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | The Editor's Apprentice |
| images/math_calvin_cycle.png | https://commons.wikimedia.org/wiki/File:Calvin_cycle.svg (1280 px PNG render) | CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0) | Yikrazuul |
| images/math_ohm_internal_resistance.jpg | https://commons.wikimedia.org/wiki/File:Basic_electric_circuit_with_potentials.jpg (original file) | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | Frankemann |
| images/math_parallel_meters.png | https://commons.wikimedia.org/wiki/File:Parallel_circuit_3_resistors_2_branches_both_meters.png (original, transparent background flattened onto white) | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | Paulgwilliamson |
| images/math_kinematics_slide.png | copy of samples/synthetic/clean/formulas_kinematics.png (made by backend/scripts/make_samples.py) | generated | DrawExplain synthetic sample generator |

Identification: each PNG was compared with the Commons thumbnail rendered at the same width (grayscale 64x64
similarity 1.000, same size); the Pythagoras JPEG has the same SHA-1 as the Commons original. An earlier `math_incline_friction.png` was removed because its
source could not be identified with confidence.

## Computer science cases (`cases/cs_*.json`)

All nine are real Wikimedia Commons files (no generated images). SVGs: Commons PNG render, downscaled to the width shown.
Rasters narrower than 900 px: upscaled 2x (Lanczos) so the small text stays legible for OCR. Transparent backgrounds are flattened onto white.

| file | source URL | license | author |
|---|---|---|---|
| images/cs_bfs_dfs.png | https://commons.wikimedia.org/wiki/File:Graph.traversal.example.svg (1280 px PNG render) | CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0) | Miles |
| images/cs_prim_mst.png | https://commons.wikimedia.org/wiki/File:Prim_Algorithm_0.svg (1280 px PNG render) | CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0) | Alexander Drichel |
| images/cs_dijkstra_a_to_e.png | https://commons.wikimedia.org/wiki/File:Shortest_path_example_graph.png (original 1600x1200, flattened) | CC0 1.0 | Shirisha Gongati |
| images/cs_bst_insert.png | https://commons.wikimedia.org/wiki/File:Binary_search_tree.svg (1280 px PNG render) | Public domain | Derrick Coetzee (Dcoetzee); SVG reworked by Booyabazooka |
| images/cs_tcp_handshake.png | https://commons.wikimedia.org/wiki/File:TCP_Handshake.png (705x527 original, 2x upscale) | CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0) | Sajidur89 |
| images/cs_gbn_vs_sr.png | https://commons.wikimedia.org/wiki/File:Go_Back_N.jpg (640x400 JPEG, 2x upscale, saved as PNG) | CC BY-SA 2.5 (https://creativecommons.org/licenses/by-sa/2.5) | Kjnawal at English Wikibooks |
| images/cs_sjf_gantt.png | https://commons.wikimedia.org/wiki/File:Shortest_job_first.png (820x497 original, 2x upscale) | CC0 1.0 | Maxtremus |
| images/cs_lru_cache.png | https://commons.wikimedia.org/wiki/File:Lruexample.png (756x372 original, 2x upscale) | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | Advaitjavadekar |
| images/cs_deadlock_rag.png | https://commons.wikimedia.org/wiki/File:GrafoDeadlock.png (503x566 original, 2x upscale) | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | A.gr209 |

Notes: the Commons description of `Shortest_path_example_graph.png` says the shortest A->E path is A-C-D-E = 12. That is
wrong: A-C-E = 2 + 8 = 10 (the image itself states no answer). The case expects 10.
Rejected candidates: `Round-robin_schedule_quantum_3.png` / `Round_Robin_Schedule_Example.jpg` (they cycle by process
number, not a FIFO ready queue), `RR_voorbeeld.jpg` (its waiting times are inconsistent), `BeladysAnomaly.png` and
`Anomalia_di_Belady.svg` (swapped axes / impossible fault counts), `Gobackn.svg` (labels in Greek).
