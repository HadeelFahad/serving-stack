"""serving-stack: the FastAPI service (week 2, CPU, tiny model).

INSTRUCTOR REFERENCE for Lab W2D2. This is the starter with its two TODOs
filled in, and nothing else added beyond the optional streaming delta at the
bottom. It is deliberately NOT the finished serving-stack/app/main.py, which
carries the engine backends and the GPU path that weeks 3 to 5 teach.

Scope, matching the lab objective exactly:
    GET  /health                  given in the starter
    GET  /v1/models               TODO 1
    POST /v1/chat/completions     TODO 2, non-streaming
    POST /v1/chat/completions     streaming delta, optional, at the bottom

Run it:
    uvicorn main:app --host 0.0.0.0 --port 8000
Then, from the lab directory:
    python verify.py
"""
from __future__ import annotations

import json
import os
import time
import uuid
import logging

import torch
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from transformers import AutoModelForCausalLM, AutoTokenizer

from schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    HealthResponse,
    ModelCard,
    ModelList,
    ResponseMessage,
    Usage,
)

MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
API_KEY = os.environ.get("API_KEY", "")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 256))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="serving-stack", version="wk2")

async def verify_token(authorization: str = Header(None)):
    if not API_KEY:
        logger.warning("WARNING: API_KEY is empty. Running unauthenticated!")
        return
    
    expected_header = f"Bearer {API_KEY}"
    if authorization != expected_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

print(f"loading {MODEL_ID} on cpu ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
model.to("cpu")
model.eval()
print("model ready")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness and readiness. Given in the starter; must not run the model."""
    return HealthResponse(status="ok", model=MODEL_ID)


# ---------------------------------------------------------------------------
# TODO 1 -- GET /v1/models
# ---------------------------------------------------------------------------
@app.get("/v1/models", response_model=ModelList, dependencies=[Depends(verify_token)])
def list_models() -> ModelList:
    """Week 2 serves exactly one model, so data has exactly one card.

    Marking note: the only thing that matters here is that ModelCard.id equals
    MODEL_ID character for character. The consumer's client compares it to the
    id it sends back in the completion request.
    """
    return ModelList(
        data=[ModelCard(id=MODEL_ID, created=int(time.time()), owned_by="aidc")]
    )


# ---------------------------------------------------------------------------
# TODO 2 -- POST /v1/chat/completions, non-streaming
# ---------------------------------------------------------------------------
def _build_inputs(req: ChatCompletionRequest):
    """Apply the chat template and return (input_ids, prompt_tokens)."""
    input_ids = tokenizer.apply_chat_template(
        [m.model_dump() for m in req.messages],
        add_generation_prompt=True,
        return_tensors="pt",
    )
    
    if not isinstance(input_ids, torch.Tensor):
        input_ids = input_ids["input_ids"]
        
    return input_ids, input_ids.shape[1]


def _generate(input_ids, req: ChatCompletionRequest):
    """Run the model. Blocks the event loop: week 3's engine owns concurrency."""
    with torch.no_grad():
        out = model.generate(
            input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=req.max_tokens,
            do_sample=req.temperature > 0,
            temperature=req.temperature if req.temperature > 0 else None,
            pad_token_id=tokenizer.eos_token_id,
        )
    return out[0][input_ids.shape[1]:]


@app.post("/v1/chat/completions", response_model=None, dependencies=[Depends(verify_token)])
def chat_completions(req: ChatCompletionRequest):
    """Non-streaming completion in the OpenAI shape.

    Marking notes, in the order students get them wrong:
      - usage.total_tokens must equal prompt + completion. The verifier checks
        the arithmetic, not just the presence of the field.
      - completion_tokens must be > 0. A student who decodes the whole output
        instead of the new tokens gets a plausible-looking answer with the
        prompt echoed back and the count wrong.
      - finish_reason is "length" only when the generation was cut off by
        max_tokens, otherwise "stop".
      - the id must be unique per call; a constant string passes the verifier
        but breaks the agentic client in week 4.
    """
    if req.max_tokens > MAX_TOKENS:
        req.max_tokens = MAX_TOKENS
        
    if req.model != MODEL_ID:
        # The contract in the starter: reject unknown ids rather than silently
        # serving something else. The consumer checks the id it gets back.
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": f"model '{req.model}' not found",
                              "type": "invalid_request_error",
                              "code": "model_not_found"}},
        )

    input_ids, prompt_tokens = _build_inputs(req)

    if req.stream:
        return _stream(input_ids, prompt_tokens, req)

    new_tokens = _generate(input_ids, req)
    completion_tokens = int(new_tokens.shape[0])
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    return ChatCompletionResponse(
        id="chatcmpl-" + uuid.uuid4().hex,
        created=int(time.time()),
        model=req.model,
        choices=[
            Choice(
                index=0,
                message=ResponseMessage(role="assistant", content=text),
                finish_reason="length" if completion_tokens >= req.max_tokens else "stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


# ---------------------------------------------------------------------------
# DELTA STEP -- streaming. Not required for the green check.
# ---------------------------------------------------------------------------
def _stream(input_ids, prompt_tokens: int, req: ChatCompletionRequest):
    """Server-Sent Events in the OpenAI chunk shape.

    Generated here the simple way: produce the whole completion, then emit it
    token by token. That is honest for week 2 (it does not reduce time to first
    token) and it is what the streaming delta asks for. A real incremental
    stream needs TextIteratorStreamer on a worker thread; week 3's engine gives
    it properly.
    """
    new_tokens = _generate(input_ids, req)
    cid = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    def chunk(delta: dict, finish=None) -> str:
        payload = {
            "id": cid, "object": "chat.completion.chunk", "created": created,
            "model": req.model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        return "data: " + json.dumps(payload) + "\n\n"

    def events():
        yield chunk({"role": "assistant", "content": ""})
        for tok in new_tokens:
            piece = tokenizer.decode([tok], skip_special_tokens=True)
            if piece:
                yield chunk({"content": piece})
        yield chunk({}, finish="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")