# Grounding evaluation

IoU between each drawing box and the ground-truth box; hit@t = share of elements with IoU >= t.

## Overall

| model | method | n | mean IoU | hit@0.5 | hit@0.75 | hit@0.9 | centre in box |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | fused | 143 | 0.822 | 85% | 83% | 69% | 93% |
| gpt-4.1-mini | ids_only | 143 | 0.758 | 77% | 75% | 62% | 98% |
| gpt-4.1-mini | raw | 143 | 0.113 | 3% | 1% | 0% | 24% |
| gpt-4.1-mini | som_approx | 143 | 0.127 | 7% | 1% | 0% | 20% |
| gpt-5.4-mini | fused | 338 | 0.799 | 86% | 76% | 58% | 93% |
| gpt-5.4-mini | ids_only | 338 | 0.696 | 73% | 63% | 50% | 94% |
| gpt-5.4-mini | raw | 338 | 0.603 | 68% | 36% | 13% | 86% |
| gpt-5.4-mini | som_approx | 338 | 0.526 | 57% | 23% | 9% | 84% |

## hit@0.75 by image set

| model | method | clean | photo | dark | small | fixtures | quick |
|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | raw | 37% | 30% | - | - | 38% | 100% |
| gpt-5.4-mini | som_approx | 32% | 20% | - | - | 9% | 83% |
| gpt-5.4-mini | ids_only | 85% | 38% | - | - | 66% | 100% |
| gpt-5.4-mini | fused | 89% | 55% | - | - | 85% | 100% |
| gpt-4.1-mini | raw | 0% | 0% | - | - | 0% | 17% |
| gpt-4.1-mini | som_approx | 0% | 3% | - | - | 1% | 0% |
| gpt-4.1-mini | ids_only | 94% | 69% | - | - | 72% | 100% |
| gpt-4.1-mini | fused | 94% | 69% | - | - | 84% | 100% |

## How the fused pipeline grounded each target

| model | grounding | count |
|---|---|---|
| gpt-4.1-mini | consensus | 43 |
| gpt-4.1-mini | id_only | 95 |
| gpt-4.1-mini | llm_only | 2 |
| gpt-4.1-mini | llm_refined | 3 |
| gpt-5.4-mini | consensus | 288 |
| gpt-5.4-mini | cv_snap | 5 |
| gpt-5.4-mini | id_only | 32 |
| gpt-5.4-mini | llm_only | 4 |
| gpt-5.4-mini | llm_refined | 9 |

Skipped (responses not cached, --cache-only): 19 image x model pairs: clean/dense_architecture.png gpt-4.1-mini, clean/cell_organelles.png gpt-4.1-mini, clean/bar_chart.png gpt-4.1-mini, clean/flowchart_loop.png gpt-4.1-mini, clean/formulas_kinematics.png gpt-4.1-mini, clean/free_body.png gpt-4.1-mini, photo/bar_chart.jpg gpt-4.1-mini, photo/cell_organelles.jpg gpt-4.1-mini, photo/dense_architecture.jpg gpt-4.1-mini, photo/formulas_kinematics.jpg gpt-4.1-mini, photo/free_body.jpg gpt-4.1-mini, dark/flowchart_loop.png gpt-5.4-mini, dark/formulas_kinematics.png gpt-5.4-mini, dark/flowchart_loop.png gpt-4.1-mini, dark/formulas_kinematics.png gpt-4.1-mini, small/cell_organelles.png gpt-5.4-mini, small/cell_organelles.png gpt-4.1-mini, small/dense_architecture.png gpt-5.4-mini, small/dense_architecture.png gpt-4.1-mini

GPU (SAM 2.1): 17 requests, 37.4s in total, 0 failures; 19 fused targets SAM-refined.
