"""serving-stack: the FastAPI service (week 2, CPU, tiny model).

This is the starter. GET /health is done for you and works as soon as the model
loads: treat it as the worked example. Your job is the two routes marked TODO.
Correctness before speed. The model runs on CPU this week; do not add a GPU.

Run it:
    uvicorn main:app --host 0.0.0.0 --port 8000

Model: Qwen/Qwen2.5-0.5B-Instruct (about 0.5B params; loads on CPU in seconds
once cached). The first ever load downloads weights; the prep-week verify-env
pass pre-seeded the Hugging Face cache, so a cached load is fast.
"""
from __future__ import annotations

import os
import time
import uuid

import torch
from fastapi import FastAPI
from transformers import AutoModelForCausalLM, AutoTokenizer

from schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse,
    ModelList,
    ModelCard,
    Choice,
    ResponseMessage,
    Usage,
)

MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")

app = FastAPI(title="serving-stack", version="wk2")

# Load once at import time. CPU only this week.
print(f"loading {MODEL_ID} on cpu ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
model.to("cpu")
model.eval()
print("model ready")


# ---------------------------------------------------------------------------
# GET /health  -- DONE. This is the worked example. Copy its shape.
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness and readiness.

    Contract: returns 200 with {"status": "ok", "model": "<id>"} once the model
    is loaded. Kubernetes probes (week 4) and the agentic client's retry logic
    (weeks 4 to 6) call this. It must be cheap and must not run the model.
    """
    return HealthResponse(status="ok", model=MODEL_ID)


# ---------------------------------------------------------------------------
# GET /v1/models  -- TODO
# ---------------------------------------------------------------------------
@app.get("/v1/models", response_model=ModelList)
def list_models() -> ModelList:
    """List the served model id(s).

    Contract (OpenAI-compatible):
      response body: {"object": "list", "data": [ {ModelCard}, ... ]}
      each ModelCard has: id (== MODEL_ID), object == "model", created (unix
      seconds), owned_by.
    Week 2 serves exactly one model, so data has one entry: MODEL_ID.

    Build a ModelList from schemas.py and return it. Use int(time.time()) for
    created.
    """
    return ModelList(
        data=[
            ModelCard(
                id=MODEL_ID,
                created=int(time.time()),
            )
        ]
    )


# ---------------------------------------------------------------------------
# POST /v1/chat/completions  -- TODO (non-streaming first)
# ---------------------------------------------------------------------------
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: ChatCompletionRequest) -> ChatCompletionResponse:
    """Run the model over the messages and return an OpenAI-compatible completion.

    Contract (non-streaming, the week-2 target):
      request:  ChatCompletionRequest (model, messages[], max_tokens, temperature)
      response: ChatCompletionResponse with
        id            a unique string, e.g. "chatcmpl-" + uuid4().hex
        object        "chat.completion"
        created       int(time.time())
        model         req.model (echo it back today; the reference rejects
                      unknown ids with a 400 model_not_found - match that
                      behaviour once your served id is stable, because the
                      consumer's client checks the id character for character)
        choices[0]    Choice(message=ResponseMessage(role="assistant",
                      content=<generated text>), finish_reason="stop" or "length")
        usage         Usage(prompt_tokens, completion_tokens, total_tokens),
                      all non-negative and total == prompt + completion

    Suggested steps:
      1. Build the prompt with the chat template:
            input_ids = tokenizer.apply_chat_template(
                [m.model_dump() for m in req.messages],
                add_generation_prompt=True, return_tensors="pt")
      2. prompt_tokens = input_ids.shape[1]
      3. Generate (no_grad, do_sample based on temperature > 0):
            out = model.generate(input_ids, max_new_tokens=req.max_tokens)
      4. new_tokens = out[0][prompt_tokens:]; completion_tokens = len(new_tokens)
      5. text = tokenizer.decode(new_tokens, skip_special_tokens=True)
      6. finish_reason = "length" if completion_tokens >= req.max_tokens else "stop"
      7. Assemble and return the ChatCompletionResponse.

    Generation blocks the event loop this week. That is acceptable: week 3's
    engine owns concurrency. Name it, do not solve it here.
    """
    try:
        # 1. Build the prompt with the chat template:
        input_ids = tokenizer.apply_chat_template(
            [m.model_dump() for m in req.messages],
            add_generation_prompt=True, return_tensors="pt"
        )
        
        if not isinstance(input_ids, torch.Tensor):
            input_ids = input_ids["input_ids"]

        # 2. prompt_tokens = input_ids.shape[1]
        prompt_tokens = input_ids.shape[1]

        # 3. Generate (no_grad, do_sample based on temperature > 0):
        with torch.no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=req.max_tokens,
                do_sample=req.temperature > 0,
                temperature=req.temperature if req.temperature > 0 else None,
                pad_token_id=tokenizer.eos_token_id
            )

        # 4. new_tokens = out[0][prompt_tokens:]; completion_tokens = len(new_tokens)
        new_tokens = out[0][prompt_tokens:]
        completion_tokens = len(new_tokens)

        # 5. text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        text = tokenizer.decode(new_tokens, skip_special_tokens=True)

        # 6. finish_reason = "length" if completion_tokens >= req.max_tokens else "stop"
        finish_reason = "length" if completion_tokens >= req.max_tokens else "stop"

        # 7. Assemble and return the ChatCompletionResponse.
        return ChatCompletionResponse(
            id="chatcmpl-" + uuid.uuid4().hex,
            created=int(time.time()),
            model=req.model,
            choices=[
                Choice(
                    index=0,
                    message=ResponseMessage(role="assistant", content=text),
                    finish_reason=finish_reason
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e


# ---------------------------------------------------------------------------
# Streaming is a DELTA STEP, not required for the green check. See the README.
# When you add it: same route, if req.stream is True return a
# StreamingResponse of Server-Sent Events. Each event is
#   data: {chat.completion.chunk with choices[0].delta.content}\n\n
# and the stream ends with the literal line
#   data: [DONE]\n\n
# ---------------------------------------------------------------------------