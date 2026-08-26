# serving-stack

The one system this course builds. Your team creates this repository once from
the template, and every lab from week 2 to graduation is a change to it. There
is no week where you start again.

## What is here

```
app/        empty. Your service goes here, starting week 2 day 2
docs/       the API contract the Agentic AI cohort integrates against
scripts/    verify-env.sh, which checks your machine against what the labs need
PINS.md     every version this course depends on
setup.md    how to work in this repository
```

That is the whole repository, and the shortness of that list is the point. You
are not given a finished system to read. You build one, a day at a time, and by
week 6 another cohort's agents are calling it.

## What you add, and when

| Week | Day | What you add |
|---|---|---|
| 2 | Mon | `app/` behind an OpenAI-compatible `/v1` on CPU |
| 2 | Tue | `Dockerfile`, and your image on Docker Hub |
| 2 | Wed | `Dockerfile.gpu`, the same code on a GPU |
| 2 | Thu | `compose.yaml`, the stack described rather than run by hand |
| 3 | Thu | `bench/`, the harness that measures all of it |

Each one is a lab, and each one starts from files that day hands you. Lab
instructions, decks and quizzes are on the course Drive, one folder per week.
This repository is your code.

## Start here

```bash
./scripts/verify-env.sh     # checks your machine, writes verify-env-report.json
```

Then read `setup.md`. It is short, and it covers the two things that go wrong:
committing a key, and committing a model.

## W2D3: Image Size Comparison

| Stage | Image Size |
| :--- | :--- |
| naive build (full base, cached pip) | 16.4 GB |
| your slim build | 4.15 GB |

## W2D4: Performance Comparison (CPU vs T4 GPU)

To evaluate the generation performance of the AI model, a probe generation test was conducted comparing the local CPU fallback against the cloud-based Tesla T4 GPU.

| Environment | Hardware / Image | Speed (tokens/sec) | Evidence / Notes |
| :--- | :--- | :--- | :--- |
| **Local Environment** | CPU Fallback | 2.0 | Estimated local CPU performance |
| **Google Colab** | NVIDIA Tesla T4 | 25.4 | Documented in `gpu_evidence.json` |

### Conclusion:
* **Speedup:** The GPU configuration is significantly faster, achieving a generation speed of **25.4 tokens per second**.
* **Image Size Impact:** The GPU-enabled container image is larger due to the inclusion of CUDA base layers and GPU-optimized PyTorch dependencies.

![Docker Image Sizes](artifacts/W2D4/image_size_comparison_gpu-v1_cpu-v1.png)