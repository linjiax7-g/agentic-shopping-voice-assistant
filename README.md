# Voice Assistant

Single repository hosting a FastAPI backend with Whisper ASR plus ElevenLabs TTS, and a Next.js voice chat frontend. This README consolidates all operational notes that used to live in the individual guides.

## Highlights
- Real-time microphone capture, streaming to Whisper via WebSocket, final transcripts pushed back to the UI
- Text-to-speech playback through ElevenLabs with configurable voice and language per participant
- Language-aware UI: choose ASR/TTS language codes per user/agent before recording or playback
- Production ready pieces: health endpoint, CORS, deployable via Gunicorn/Uvicorn or Docker, frontend static build

## Architecture Overview
```
┌──────────────┐      WebSocket (/ws/voice)      ┌──────────────────┐
│  VoiceChat   │ ─────────────────────────────►  │ FastAPI backend  │
│  (Next.js)   │ ◄────────── transcripts ─────── │  backend/main.py │
└────┬─────────┘                                 └───────┬──────────┘
     │ REST (/api/tts, /api/voices, /health)             │
     ▼                                                   ▼
Frontend state & UI                         VoicePipeline orchestrates
messages, settings, recording       ┌──────── WhisperASR ───────┐
logic, and audio playback           │                          │ │
                                    └──────── ElevenLabsTTS ───┘ ▼
```
- `components/VoiceChat.tsx` manages WebSocket streaming, PCM conversion, UI, and TTS playback
- `backend/main.py` hosts the WebSocket endpoint plus REST APIs
- `agentic-shopping-voice-assistant/voice/pipeline.py` coordinates buffering, session state, Whisper ASR (`voice/asr.py`), and ElevenLabs TTS (`voice/tts.py`)

## Requirements
- Windows 10/11 or Linux/macOS
- Python 3.9+ (virtual environment already at `venv/`)
- Node.js 18+ with npm or yarn
- ElevenLabs API key (for TTS). See [ElevenLabs API reference](https://elevenlabs.io/docs/api-reference/introduction)

## Repository Layout
```
VoiceAssistant/
├── backend/            # FastAPI app (main.py)
├── frontend/           # Next.js app (app/, components/, etc.)
├── agentic-shopping-voice-assistant/
│   ├── graph/          # LangGraph workflow + retrievers + models
│   └── voice/          # Shared ASR/TTS pipeline used by backend
├── env.example         # Backend env template
├── requirements.txt    # Python dependencies
├── run_frontend.*
└── README.md           # You are here
```

## Environment Configuration
1. Backend `.env` (copy from `env.example`)
   ```env
   WHISPER_MODEL=base
   WHISPER_DEVICE=cpu
   ELEVENLABS_API_KEY=your_elevenlabs_key
   ```
2. Frontend `frontend/.env.local`
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   For production, point `NEXT_PUBLIC_API_URL` at your deployed backend.

## Local Setup & Running
### Backend (Terminal 1)
```powershell
cd D:\Projects\Applied_GenAI\VoiceAssistant
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt      # first time
cd backend
python main.py                       # or: uvicorn main:app --reload --port 8000
```
Expected logs include Whisper model loading and Uvicorn on port 8000. Health check: `http://localhost:8000/health`.

### Frontend (Terminal 2)
```powershell
cd D:\Projects\Applied_GenAI\VoiceAssistant\frontend
npm install            # first time
npm run dev            # serves http://localhost:3000
```

### Verifying
1. Navigate to `http://localhost:3000`
2. Open dev tools console for debug logs
3. Hit the microphone button, speak, then stop
4. Ensure a transcript message appears
5. Hover over any message and press Play to hear TTS

## Using the Voice Chat UI
- **Recording:** Microphone button toggles capture. Browser will prompt for permission the first time. Capture runs at 16 kHz mono PCM.
- **Text input:** Type in the input box and press Enter.
- **TTS Playback:** Hover over a message, press the play icon; stops when toggled again.
- **Settings panel:** Click the gear icon to pick user/agent voices and languages. The dropdown on the right controls both ASR (recordings) and TTS (payload language code). Select the target language before you start speaking.
- **Languages:** Whisper can auto-detect, but for best accuracy choose the spoken language first. For TTS, ElevenLabs pronounces whatever text you send; translate the text yourself if you need an actual non-English response.

## API Surface
| Endpoint      | Method    | Description                                 |
|---------------|-----------|---------------------------------------------|
| `/ws/voice`   | WebSocket | Stream base64 PCM audio (`type: "audio"`) and receive transcripts (`type: "transcript"`) |
| `/api/agent`  | POST      | `{ text }` ⇒ LangGraph shopping response (`answer`, `citations`, `retrieved_docs`) |
| `/api/tts`    | POST      | `{ text, voice_id, language, stability?, similarity_boost? }` ⇒ base64 MP3 |
| `/api/voices` | GET       | List of available ElevenLabs voices (id, name, language, metadata) |
| `/health`     | GET       | Returns ASR/TTS availability flags |
| `/`           | GET       | Basic service metadata |
Swagger UI lives at `http://localhost:8000/docs`.

## Development Commands
### Python
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd backend
python main.py                     # dev server
uvicorn main:app --reload          # alternative
```
### Node.js
```bash
cd frontend
npm run dev        # develop
npm run build      # compile
npm start          # serve production build
npm run lint       # lint
```

## Deployment Notes
- **Backend**
  - Gunicorn example: `gunicorn backend.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120`
  - Docker: base image `python:3.10-slim`, copy `requirements.txt`, install deps, copy `backend/` plus `agentic-shopping-voice-assistant/voice/`, expose 8000, run uvicorn
- **Frontend**
  - Set `NEXT_PUBLIC_API_URL` to your backend origin, run `npm run build`, then `npm start` or host via your static provider
- **Reverse proxy**
  - Nginx should proxy `/api/` and `/ws/` to the backend, forwarding Upgrade headers for WebSocket. Increase proxy timeouts for long-lived streams.
- **Environment**
  - Ensure `ELEVENLABS_API_KEY` exists in production and you have credits/plan allowance. Whisper can run CPU-only; GPU requires CUDA/cuDNN installed.

## Troubleshooting
- **Frontend “Failed to fetch”** – backend not running or CORS blocked; verify `http://localhost:8000/health`.
- **Microphone errors** – ensure browser permission granted, use Chrome/Edge, no other app holding the mic.
- **No ASR output** – confirm backend logs show audio chunks; if Whisper tries CUDA but cuDNN missing, set `WHISPER_DEVICE=cpu` (already default).
- **TTS service unavailable** – check ElevenLabs key and account limits; backend logs will show HTTP errors.
- **Voices list empty** – backend falls back to default voice IDs; confirm `/api/voices` reachable.
- **Language mismatches** – pick the appropriate code in the settings panel before recording or playback; TTS does not translate the text automatically.

## Testing Checklist
- Backend logs show audio chunk receipt and transcription
- Frontend displays transcripts and allows text messages
- TTS playback works for both user and agent messages
- Switching voices or languages updates subsequent recordings/responses
- `/health` reports both `asr_available` and `tts_available` as true

## Next Steps
- Integrate your conversational AI backend by replacing the placeholder echo response in `components/VoiceChat.tsx`
- Add translation before calling `/api/tts` if you need multilingual spoken replies
- Harden deployment: HTTPS everywhere, process supervisor, monitoring (Prometheus, logs), and caching for voice lists

## Reference
- ElevenLabs API documentation: [https://elevenlabs.io/docs/api-reference/introduction](https://elevenlabs.io/docs/api-reference/introduction)


