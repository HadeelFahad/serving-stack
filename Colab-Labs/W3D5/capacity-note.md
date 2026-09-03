# Capacity note (team, one page)

## The numbers

- Locked model: `Qwen/Qwen2.5-1.5B-Instruct-AWQ`
- Target p95 end-to-end latency (our SLO today): `2.0 seconds`
- Knee concurrency (highest concurrency whose p95 is still under target): `8`
- Tokens per second at the knee: `482.46 tokens/s`
- Max sustainable request rate at the target p95: `4.65 req/s`

## The limiting family

- Memory-bound: this workload is decode-heavy, where LLM serving is typically limited by memory movement rather than compute.

## Why the knee, not the peak

- The knee is the useful capacity because it keeps p95 within our 2.0-second SLO, while higher concurrency gives more throughput but causes latency to exceed the target.
