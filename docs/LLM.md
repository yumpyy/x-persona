# LLM Configuration

## Single-Provider Architecture

The agent uses **OpenAI-compatible APIs** via `langchain_openai.ChatOpenAI`. This works with:

- OpenAI (`https://api.openai.com/v1`)
- DeepSeek via DashScope (`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`)
- Ollama (local, `http://localhost:11434/v1`)
- vLLM, LM Studio, Groq, Together AI, or any OpenAI-compatible endpoint

## `x_personas/agent/config.py`

### `get_llm(config)` → `ChatOpenAI`

```python
def get_llm(config) -> ChatOpenAI:
    model = config.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
    base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
    temperature = config.get("temperature", 0.7)
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)
```

#### `get_llm_config()` → `dict`

Builds config dict from env vars for text-only LLM tasks.

### `get_vlm_config()` → `dict | None`

Returns `None` if `VLM_MODEL` is not set (VLM features disabled). Falls back to `VLM_API_KEY` → `OPENAI_API_KEY` and `VLM_BASE_URL` → `OPENAI_BASE_URL`.

## Text LLM vs VLM

| | Text LLM | VLM (Vision) |
|---|---|---|
| Env vars | `OPENAI_MODEL`, `OPENAI_API_KEY`, `OPENAI_BASE_URL` | `VLM_MODEL`, `VLM_API_KEY`, `VLM_BASE_URL` |
| Required | Yes | No (opt-in) |
| Used by | `generate_original_post` | `llm_decide`, `generate_content` |
| When VLM is off | — | Nodes skip image attachments, text-only fallback |

## Temperature Per Node

| Node | Temperature | Purpose | Uses |
|---|---|---|---|
| `llm_decide` | 0.0 | Deterministic, precise decisions | VLM if available, else text LLM |
| `generate_content` | 0.8 | Creative, diverse replies/quotes | VLM if available, else text LLM |
| `generate_original_post` | 0.85 | More creative original tweets | Text LLM only |

## Environment Variables

```env
# Text LLM (required)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# VLM (optional — unset VLM_MODEL to disable multimodal)
VLM_MODEL=gpt-4o
VLM_API_KEY=
VLM_BASE_URL=
```

## Precedence

All configuration comes from `.env` only. No CLI flags for model, API key, or base URL.

### Text LLM
1. `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_BASE_URL` env vars
2. `gpt-4o-mini` (default model)

### VLM
1. `VLM_MODEL` / `VLM_API_KEY` / `VLM_BASE_URL` env vars
2. Falls back to `OPENAI_API_KEY` / `OPENAI_BASE_URL` if VLM-specific not set
3. If `VLM_MODEL` is unset, VLM features are disabled
