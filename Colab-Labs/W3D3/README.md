# W3D3 - The Engine Swap

In this lab, I replaced the previous inference setup with vLLM while keeping the same OpenAI-compatible `/v1` API.

I compared vLLM throughput with my W3D2 static batching baseline using concurrency levels 1, 4, and 8.

## Prediction vs Actual

| Metric | Before the Run | Actual |
|---|---:|---:|
| vLLM speedup at concurrency 8 | Predicted: 1.5x | 2.40x |
| Static batching scaling (1 → 8) | Known from W3D2: 2.90x | 2.90x |
| vLLM scaling (1 → 8) | Predicted: 3.5x | 4.29x |
| Continuous batching scaling advantage | Predicted: ~1.2x larger | 1.48x larger |

The static batching scaling was already known from W3D2:

`97.5 / 33.6 = 2.90x`

For vLLM, I predicted around `3.5x` scaling from concurrency 1 to 8.

Based on that prediction:

`3.5 / 2.90 = 1.21x`

So I expected continuous batching to scale about `1.2x` better than static batching.

Actual vLLM scaling:

`234.4 / 54.7 = 4.29x`

Actual continuous batching scaling advantage:

`4.29 / 2.90 = 1.48x`

## Results

| Concurrency | Static Baseline (tokens/s) | vLLM (tokens/s) | Speedup |
|---:|---:|---:|---:|
| 1 | 33.6 | 54.7 | 1.63x |
| 4 | 49.0 | 165.4 | 3.38x |
| 8 | 97.5 | 234.4 | 2.40x |


vLLM scaled better because continuous batching can replace finished requests instead of keeping finished sequences in fixed batch slots.

## Green Check

- Baseline batch-8: 97.5 tokens/s
- vLLM concurrency-8: 234.4 tokens/s
- Speedup at concurrency 8: 2.40x
- GREEN CHECK: PASS

![Green Check](green_check.png)
