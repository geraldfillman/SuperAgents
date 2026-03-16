# MiroFish Runtime

Use these scripts to prepare a portable MiroFish simulation bundle inside `Super_Agents`, run it against a local MiroFish checkout, inspect status, and send shutdown commands.

The integration is intentionally local-only. It does not start the MiroFish Flask backend or Vue frontend.

For repeatable runs, configure the local MiroFish checkout with a real `MiroFish/.env` file. Do not rely on `.env.example`; upstream MiroFish only loads `.env` or `backend/.env` at runtime.

Recommended OpenAI settings:

```env
LLM_API_KEY=your-real-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_BOOST_API_KEY=your-real-openai-key
LLM_BOOST_BASE_URL=https://api.openai.com/v1
LLM_BOOST_MODEL_NAME=gpt-4o-mini
```

`probe_runtime` now validates both package dependencies and runtime config. `run_bundle --openai-defaults` will supply OpenAI-compatible base URL and model defaults for a one-off run when only the API key is set.
