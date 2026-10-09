# Grounding evaluation

IoU between each drawing box and the ground-truth box; hit@t = share of elements with IoU >= t.

## Overall

| model | method | n | mean IoU | hit@0.5 | hit@0.75 | hit@0.9 | centre in box |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | fused | 407 | 0.812 | 86% | 81% | 68% | 90% |
| gpt-4.1-mini | ids_only | 407 | 0.793 | 84% | 79% | 66% | 92% |
| gpt-4.1-mini | raw | 407 | 0.111 | 5% | 0% | 0% | 19% |
| gpt-4.1-mini | som_approx | 407 | 0.128 | 7% | 1% | 0% | 22% |
| gpt-5.4-mini | fused | 407 | 0.829 | 89% | 83% | 69% | 91% |
| gpt-5.4-mini | ids_only | 407 | 0.772 | 82% | 77% | 65% | 90% |
| gpt-5.4-mini | raw | 407 | 0.592 | 65% | 34% | 15% | 83% |
| gpt-5.4-mini | som_approx | 407 | 0.552 | 62% | 31% | 11% | 82% |

## hit@0.75 by image set

| model | method | clean | photo | dark | small | fixtures | quick |
|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | raw | 37% | 21% | 31% | 50% | 39% | 100% |
| gpt-5.4-mini | som_approx | 38% | 30% | 31% | 48% | 15% | 83% |
| gpt-5.4-mini | ids_only | 85% | 70% | 93% | 80% | 68% | 100% |
| gpt-5.4-mini | fused | 87% | 71% | 90% | 85% | 88% | 100% |
| gpt-4.1-mini | raw | 1% | 0% | 0% | 0% | 0% | 17% |
| gpt-4.1-mini | som_approx | 1% | 0% | 0% | 8% | 1% | 0% |
| gpt-4.1-mini | ids_only | 84% | 71% | 90% | 88% | 73% | 100% |
| gpt-4.1-mini | fused | 84% | 71% | 90% | 82% | 85% | 100% |

## How the fused pipeline grounded each target

| model | grounding | count |
|---|---|---|
| gpt-4.1-mini | consensus | 110 |
| gpt-4.1-mini | id_only | 279 |
| gpt-4.1-mini | llm_only | 7 |
| gpt-4.1-mini | llm_refined | 11 |
| gpt-5.4-mini | consensus | 331 |
| gpt-5.4-mini | cv_snap | 14 |
| gpt-5.4-mini | id_only | 38 |
| gpt-5.4-mini | llm_only | 16 |
| gpt-5.4-mini | llm_refined | 8 |
