# W3D1 GPU Inference Profiling Lab

## Objective

Profile `Qwen/Qwen2.5-1.5B-Instruct` on a real NVIDIA T4 GPU and observe how:

- VRAM changes with context length.
- FP16 compares with INT8 quantization.
- GPU utilisation differs from actual throughput.
- Increasing batch size affects tokens/s and GPU utilisation.

---

## Prediction vs Actual Results

| Metric | Prediction | Actual Result |
|---|---:|---:|
| FP16 weights | ~3 GB | Not directly measured |
| INT8 weights | ~1.5 GB | Not directly measured |
| FP16 VRAM @ 512 context | 3.5 GB | **3.113 GB** |
| FP16 VRAM @ 4096 context | 4.5 GB | **3.568 GB** |
| Single-request GPU utilisation | 50% | **53.3%** |

The prediction expected the 4096-token context to consume more VRAM than the 512-token context because the KV cache grows with context length. The actual measurements confirmed this behavior.

---

## Profiling Matrix Results

| Dtype | Context | VRAM (GB) | GPU Utilisation (%) | Tokens/s |
|---|---:|---:|---:|---:|
| FP16 | 512 | 3.113 | 53.3 | 25.1 |
| FP16 | 2048 | 3.295 | 61.7 | 27.1 |
| FP16 | 4096 | 3.568 | 83.7 | 24.0 |
| INT8 | 512 | 1.805 | 23.5 | 5.5 |
| INT8 | 2048 | 2.035 | 26.3 | 5.3 |
| INT8 | 4096 | 2.309 | 28.5 | 4.9 |

### Observations

- VRAM increased as the context length increased.
- INT8 used significantly less VRAM than FP16.
- INT8 reduced memory usage, but it did not improve inference speed in this experiment.
- A higher GPU utilisation value did not necessarily mean higher token throughput.

---

## Batch 1 vs Batch 8

| Metric | Batch 1 | Batch 8 |
|---|---:|---:|
| VRAM | 3.113 GB | 3.527 GB |
| GPU Utilisation | 45.0% | 68.0% |
| Tokens/s | 27.4 | 193.8 |

**Tokens/s ratio:** `7.07x`

**GPU utilisation increase:** `23 percentage points`

Although GPU utilisation increased from **45% to 68%**, throughput increased from **27.4 to 193.8 tokens/s**, which is about **7.07x higher**.

This demonstrates that:

> **High GPU utilisation does not necessarily mean the GPU is being used efficiently.**

GPU utilisation shows that the GPU is busy, while throughput shows how much useful inference work is actually being completed.

---

## Verification

```text
rows: 6
dtypes: ['fp16', 'int8']
contexts: [512, 2048, 4096]
batch-1 tokens/s: 27.4
batch-8 tokens/s: 193.8

GREEN CHECK: PASS
