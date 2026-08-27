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



# Lab W2D5: Compose and Teams (Serving Stack)

## Objective
Transition the FastAPI serving service from manual `docker run` commands to a version-controlled **Docker Compose** deployment. The objective includes securing the API from unbounded GPU consumption, configuring internal health checks, and successfully passing the automated verification.

## Key Achievements
- **Docker Compose Setup:** Authored `compose.yaml` to orchestrate the AI serving container (`hadeel88/aidc-serving:cpu-v2`), utilizing environment variables and named volumes for HuggingFace model caching.
- **API Security (Authentication):** Implemented a mandatory `Bearer Token` check for all `/v1/*` endpoints to protect GPU resources, while deliberately keeping `/health` open for future Kubernetes probes.
- **Resource Limits (Max Tokens):** Enforced a hard ceiling on `max_tokens` (256) per request to mitigate unbounded consumption (OWASP LLM10).
- **Custom Health Check:** Configured a Python-based Docker health check directly in `compose.yaml` (bypassing the lack of `curl` in the `python:3.11-slim` base image).
- **Verification:** Successfully passed the rigorous `verify.sh` automated checks, earning the **GREEN CHECK: PASS**.

---

## Pre-Lab Predictions vs. Actual Outcomes

| Question / Scenario | My Prediction | Actual Outcome & Reflection |
| :--- | :--- | :--- |
| **1. After `docker compose up -d`, how long until `docker compose ps` reports the service as healthy?** | About 60 seconds. | **Accurate.** It took around 1-2 minutes. I initially got a `000` HTTP response when testing too early, confirming the model was still loading into CPU. The `start_period: 120s` handled this perfectly. |
| **2. If you change `MODEL_ID` in `.env` and run `docker compose up -d` again, does compose recreate the container?** | Yes. | **Correct.** Docker Compose detects changes in the mapped environment variables and forces a container recreation to apply the new state. |
| **3. The healthcheck runs INSIDE the container. Does the base image have `curl`?** | No. | **Correct.** The `python:3.11-slim` base image strips out non-essential tools like `curl`. To solve this, we used a Python one-liner (`python -c "import urllib..."`) for the health probe. |
| **4. Your service currently has no key. If you published this port to the internet right now, how long until someone else is generating tokens on your GPU?** | 1 hour. | **Highly Realistic.** Bots constantly scan open ports (like 8000). Implementing the `API_KEY` (OWASP LLM10) was a critical step to prevent unbounded GPU consumption. |
| **5. After adding a key in step 4, which endpoint must still answer WITHOUT one, and why?** | `/health`, because health probes need to access it without authentication. | **Confirmed.** I verified this via `curl`. `/v1/models` returned `401 Unauthorized` without a key, while `/health` returned `200 OK`, ensuring future Kubernetes liveness probes will work. |