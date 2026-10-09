# Grounding evaluation

IoU between each drawing box and the ground-truth box; hit@t = share of elements with IoU >= t.

## Overall

| model | method | n | mean IoU | hit@0.5 | hit@0.75 | hit@0.9 | centre in box |
|---|---|---|---|---|---|---|---|
| gpt-4.1-mini | fused | 407 | 0.772 | 82% | 73% | 57% | 90% |
| gpt-4.1-mini | ids_only | 407 | 0.758 | 80% | 72% | 56% | 93% |
| gpt-4.1-mini | raw | 407 | 0.122 | 6% | 1% | 0% | 23% |
| gpt-4.1-mini | som_approx | 407 | 0.141 | 8% | 1% | 0% | 24% |
| gpt-5.4-mini | fused | 407 | 0.800 | 86% | 77% | 59% | 93% |
| gpt-5.4-mini | ids_only | 407 | 0.711 | 74% | 67% | 54% | 92% |
| gpt-5.4-mini | raw | 407 | 0.614 | 70% | 37% | 14% | 87% |
| gpt-5.4-mini | som_approx | 407 | 0.561 | 65% | 28% | 10% | 86% |

## hit@0.75 by image set

| model | method | clean | photo | dark | small | fixtures | quick |
|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | raw | 37% | 30% | 31% | 50% | 38% | 100% |
| gpt-5.4-mini | som_approx | 38% | 23% | 31% | 48% | 9% | 83% |
| gpt-5.4-mini | ids_only | 85% | 37% | 93% | 80% | 66% | 100% |
| gpt-5.4-mini | fused | 87% | 53% | 90% | 85% | 85% | 100% |
| gpt-4.1-mini | raw | 1% | 1% | 0% | 0% | 0% | 17% |
| gpt-4.1-mini | som_approx | 1% | 1% | 0% | 8% | 1% | 0% |
| gpt-4.1-mini | ids_only | 84% | 49% | 90% | 88% | 72% | 100% |
| gpt-4.1-mini | fused | 84% | 48% | 90% | 82% | 84% | 100% |

## How the fused pipeline grounded each target

| model | grounding | count |
|---|---|---|
| gpt-4.1-mini | consensus | 122 |
| gpt-4.1-mini | id_only | 264 |
| gpt-4.1-mini | llm_only | 7 |
| gpt-4.1-mini | llm_refined | 14 |
| gpt-5.4-mini | consensus | 341 |
| gpt-5.4-mini | cv_snap | 11 |
| gpt-5.4-mini | id_only | 31 |
| gpt-5.4-mini | llm_only | 15 |
| gpt-5.4-mini | llm_refined | 9 |
