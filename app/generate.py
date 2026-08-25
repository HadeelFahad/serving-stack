
import torch, time
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

def load(dtype):
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    if dtype == "fp16":
        m = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map="cuda")
    elif dtype == "int8":
        m = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=BitsAndBytesConfig(load_in_8bit=True), device_map="cuda")
    elif dtype == "int4":
        m = AutoModelForCausalLM.from_pretrained(MODEL_ID, quantization_config=BitsAndBytesConfig(load_in_4bit=True), device_map="cuda")
    else:
        raise ValueError(dtype)
    return tok, m

def tokens_per_s(dtype, new_tokens=128):
    tok, m = load(dtype)
    msgs = [{"role": "user", "content": "Explain what a GPU does, in three sentences."}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to("cuda")
    m.generate(**{"input_ids": ids}, max_new_tokens=8)  # warm-up, not timed
    torch.cuda.synchronize()
    t0 = time.time()
    out = m.generate(**{"input_ids": ids}, max_new_tokens=new_tokens, do_sample=False)
    torch.cuda.synchronize()
    dt = time.time() - t0
    generated = out.shape[1] - ids.shape[1]
    return generated / dt

if __name__ == "__main__":
    for d in ["fp16", "int8", "int4"]:
        print(d, "%.1f tok/s" % tokens_per_s(d))
