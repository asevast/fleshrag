# neuraldeep.ru — LLM API reference (для coding-агентов)

Base URL: `https://api.neuraldeep.ru/v1` (OpenAI-совместимый)
Auth: `Authorization: Bearer sk-NSlYhFlLl6A_SEqLzkomTQ`

Available models:
- `gpt-oss-120b` — chat · tools · reasoning · 131k ctx · MXFP4 на 2×RTX 4090 48 GB
- `qwen3.6-35b-a3b` — chat · tools · 200k ctx · MoE A3B
- `e5-large` — multilingual embedding · 1024-dim · 3 replicas
- `bge-m3` — multilingual embedding · 1024-dim · 8k ctx
- `bge-reranker` — cross-encoder rerank
- `whisper-1` — speech-to-text multilingual

## Chat
```
POST /v1/chat/completions
{
  "model": "gpt-oss-120b",
  "messages": [{"role":"user","content":"..."}],
  "max_tokens": 500,
  "temperature": 0.3
}
```
Note: у gpt-oss reasoning-токены — ставь max_tokens >= 300, иначе content пустой.
Session sticky: шли `user: <session_id>` → роутер закрепит сессию на одном upstream (prefix cache warm, до 10× экономия).

## Embeddings
```
POST /v1/embeddings
{"model": "e5-large", "input": ["text1","text2"]}
```
Response: `{"data": [{"embedding": [...], "index": 0}], ...}`. dim=1024 для обеих моделей. Кешируется (deterministic).

## Rerank
```
POST /v1/rerank
{"model":"bge-reranker","query":"...","documents":["doc1","doc2"]}
```
Response: `{"results": [{"index": 0, "relevance_score": 0.87}, ...]}` — отсортировано по релевантности.

## Transcription
```
POST /v1/audio/transcriptions   (multipart)
file=@audio.wav
model=whisper-1
```
Response: `{"text": "...", "language": "ru", "duration": 12.3, "segments": [...]}`.

## Structured output
```
POST /v1/chat/completions
{
  "model": "gpt-oss-120b",
  "messages": [...],
  "response_format": {"type":"json_schema","json_schema":{"name":"...","schema":{...},"strict":true}}
}
```
vLLM гарантирует strict JSON при strict:true.

## Tools (agents)
Стандартный OpenAI tool-calling с `tools` + `tool_choice`.
```
{
  "model": "gpt-oss-120b",
  "messages": [...],
  "tools": [{"type":"function","function":{"name":"...","parameters":{...}}}],
  "tool_choice": "auto"
}
```
Ответ: `choices[0].message.tool_calls`.

## Streaming
Добавь `"stream": true` → SSE поток с `data: {...}` чанками, последний `data: [DONE]`.

## Limits (free tier L1)
- Daily budget: $1.00 (~10M input tokens на gpt-oss или ~2M chat output)
- RPM: 60 · Parallel: 4
- Все 6 моделей разлочены сразу
- Streak даёт буст: 3д → +$0.10, 7д → +$0.20, 30д → +$0.50

## Pricing (для расчёта бюджета)
- gpt-oss-120b / qwen3.6: $0.05 input · $0.20 output per 1M tokens
- e5-large / bge-m3: $0.03 input per 1M
- whisper: $0.003 per min

## Python SDK
```python
from openai import OpenAI
client = OpenAI(api_key="sk-NSlYhFlLl6A_SEqLzkomTQ", base_url="https://api.neuraldeep.ru/v1")
r = client.chat.completions.create(model="gpt-oss-120b", messages=[...], max_tokens=500)
```

## JS SDK
```typescript
import OpenAI from "openai";
const client = new OpenAI({ apiKey: "sk-NSlYhFlLl6A_SEqLzkomTQ", baseURL: "https://api.neuraldeep.ru/v1" });
```

Errors:
- 401 auth_error → bad key
- 401 key_model_access_denied → key не подписан на эту модель
- 429 rate limit → >60 req/min или >4 parallel
- 400 context_window_exceeded → укоротить messages
