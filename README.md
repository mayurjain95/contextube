# ContexTube

Video intelligence pipeline that takes a YouTube URL, transcribes/loads it, indexes it into
a vector store, and answers questions using only what's actually in the
video. If the answer isn't there, it says so instead of guessing.

## How it works

1. `POST /api/index` — give it a YouTube URL. It pulls the transcript
   (LangChain's `YoutubeLoader` first, `yt-dlp` as a fallback if that fails
   or is blocked), chunks it, embeds it with OpenAI embeddings, and stores
   it in a Chroma collection scoped to that video's ID.
2. `POST /api/ask` — give it a `video_id` and a question. It retrieves the
   most relevant chunks and checks their similarity scores *before* calling
   the LLM. If nothing clears the confidence threshold, it returns
   "This wasn't covered in the video" without ever invoking the model —
   so the guardrail is structural, not just a prompt instruction.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The app uses Ollama for local embeddings and chat responses. Install Ollama,
start it, and download the models before running the backend:

```bash
brew install ollama
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.2
```

If you previously indexed videos with OpenAI embeddings, remove the old local
store before indexing them again:

```bash
rm -rf chroma_store
```

Visit `http://localhost:8000/docs` for interactive API docs.

## Example flow

```bash
curl -X POST localhost:8000/api/index \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

curl -X POST localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"video_id": "VIDEO_ID", "question": "What does the speaker say about X?"}'
```

## Known rough edges to watch for

- `YoutubeLoader` (via `youtube-transcript-api`) gets rate-limited or
  blocked by YouTube periodically. The `yt-dlp` fallback in
  `transcript_loader.py` exists specifically for this — if you see it
  triggering often, that's expected, not a bug.
- The LangChain-loader path currently returns one untimed blob of text
  (no per-line timestamps), so timestamp citations only work reliably
  when the yt-dlp fallback is the one that ran. Worth tightening later
  if you want timestamps to always be available — see "Next steps."
- `retrieval_score_threshold` in `.env` controls how strict the "was this
  covered" guardrail is. Chroma's relevance score isn't perfectly
  calibrated across embedding models, so tune this against a few real
  questions rather than trusting the default blindly.

## Frontend

Vite + React, no UI framework, no state library — just `useState` and
`fetch`. Three states in one page: URL input, indexing status, chat.
The vite dev server proxies `/api` to `http://localhost:8000`, so run the
backend first.

```bash
cd frontend
npm install
npm run dev
```

## Test-writing agent

`agent/test_writer.py` is a small agentic loop: it pulls the app's *live*
OpenAPI schema (so any endpoint you've added shows up automatically), asks
Claude to write pytest tests for a given router, actually runs them, and
if any fail, feeds the real pytest output back to Claude to fix — up to 3
attempts.

```bash
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...
python -m agent.test_writer app/routers/video.py
```

Generated tests land in `tests/test_<router_name>.py`. To cover a new
router you add later, just point it at that file — nothing else changes.

The generated tests mock external calls (OpenAI, Chroma) so running them
never costs money or needs a real `OPENAI_API_KEY`. The Anthropic key is
only used by the agent itself, to generate the test code.

## Next steps (not built yet)

- Recommendation step: after answering, optionally suggest external
  resources for concepts mentioned but not deeply explained — this is a
  good candidate for a LangGraph step later (answer → decide whether to
  recommend → search → respond), rather than cramming it into one chain
- Persist a video_id → title/URL mapping so the frontend can show a
  library of already-indexed videos instead of requiring the raw ID
- Multi-video / cross-video Q&A (bigger scope change — separate project
  phase, not a small addition)
