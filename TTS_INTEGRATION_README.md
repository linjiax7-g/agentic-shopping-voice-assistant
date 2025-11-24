# TTS Integration Complete Setup Guide

This guide explains how to run the complete voice shopping assistant with TTS integration.

## Architecture Overview

```
Frontend (React/TSX)
    ↓ HTTP Requests
Backend (FastAPI)
    ↓ Calls
Voice Module (TTS)
    ↓ Uses
OpenAI TTS API
```

---

## 🗂️ File Structure

```
applied_genai_final_frontend/
├── voice/                                  # ✨ NEW - TTS Backend
│   ├── __init__.py
│   ├── tts.py                             # OpenAI TTS implementation
│   └── api.py                             # FastAPI REST endpoints
│
├── tts_output/                            # ✨ NEW - Generated audio files
│
├── voice_shopping_assistant_ui.tsx        # ✅ UPDATED - Frontend with API integration
├── requirements.txt                       # ✅ UPDATED - Added FastAPI
├── .env.example                           # ✨ NEW - Backend env template
├── FRONTEND_ENV_EXAMPLE                   # ✨ NEW - Frontend env template
└── TTS_INTEGRATION_README.md             # 📖 This file
```

---

## 📦 Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Key new dependencies:**
- `fastapi>=0.104.0` - REST API framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `python-multipart>=0.0.6` - File upload support
- `openai>=1.0.0` - TTS API client

### 2. Set Up Environment Variables

**Backend (.env):**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

**Frontend (.env in your React project):**
```bash
# For Create React App
REACT_APP_API_URL=http://localhost:8000

# For Vite
VITE_API_URL=http://localhost:8000
```

---

## 🚀 Running the Application

### Step 1: Start the Backend API

```bash
# Method 1: Using uvicorn directly
uvicorn voice.api:app --reload --port 8000

# Method 2: Using Python
python -m voice.api

# Method 3: Using the API file directly
python voice/api.py
```

**You should see:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
======================================================================
Voice Shopping Assistant API Starting...
======================================================================
Output directory: tts_output
CORS origins: ['http://localhost:3000', 'http://localhost:5173']
OpenAI API configured: True
======================================================================
```

### Step 2: Verify Backend is Running

```bash
# Health check
curl http://localhost:8000/health

# Test TTS endpoint
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "voice": "alloy"}'
```

### Step 3: Start the Frontend

```bash
# Navigate to your React project
cd your-react-project

# Install dependencies (if needed)
npm install

# Start development server
npm run dev
# or
npm start
```

---

## 🔌 API Endpoints

### 1. **Health Check**
- **Endpoint:** `GET /health`
- **Response:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2024-01-20T12:00:00",
    "openai_configured": true
  }
  ```

### 2. **Generate TTS**
- **Endpoint:** `POST /api/tts`
- **Request:**
  ```json
  {
    "text": "I found 3 products matching your criteria...",
    "voice": "alloy",
    "model": "tts-1"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "audio_id": "uuid-here",
    "audio_url": "/api/tts/audio/uuid-here",
    "duration_estimate": 5.2
  }
  ```

### 3. **Get TTS Audio**
- **Endpoint:** `GET /api/tts/audio/{audio_id}`
- **Response:** MP3 audio file

### 4. **Complete Query Pipeline**
- **Endpoint:** `POST /api/query`
- **Request:**
  ```json
  {
    "query": "organic shampoo under $20"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "query": "organic shampoo under $20",
    "answer": "I found 3 products...",
    "citations": ["DOC 1", "DOC 2"],
    "products": [...],
    "task": "product_search",
    "constraints": {...},
    "audio_id": "uuid-here",
    "audio_url": "/api/tts/audio/uuid-here",
    "step_log": [...]
  }
  ```

---

## 🎭 Voice Options

OpenAI TTS supports 6 voices:

| Voice | Description | Best For |
|-------|-------------|----------|
| `alloy` | Neutral, balanced | General purpose |
| `echo` | Male, clear | Professional tone |
| `fable` | British accent, expressive | Storytelling |
| `onyx` | Deep male | Authoritative |
| `nova` | Female, energetic | Upbeat content |
| `shimmer` | Female, warm and soft | Friendly tone |

**To change voice in frontend:**
Edit `voice_shopping_assistant_ui.tsx` line 218:
```typescript
voice: 'nova'  // Change to any voice above
```

---

## 🧪 Testing

### Test 1: Backend TTS Module

```bash
# Test TTS generation directly
python -c "
from voice.tts import synthesize_speech
synthesize_speech('Hello world', 'test.mp3', voice='nova')
print('✅ TTS test successful - check test.mp3')
"
```

### Test 2: API Endpoints

```bash
# Test TTS endpoint
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Testing TTS API", "voice": "alloy"}' \
  | jq

# Test query endpoint (requires LangGraph setup)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "organic shampoo under $20"}' \
  | jq
```

### Test 3: Frontend Integration

1. Start backend: `uvicorn voice.api:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Open browser to frontend URL
4. Click "Search" button
5. When results appear, click the Play button in "Listen to Results" section
6. You should hear the AI-generated speech

---

## 🔧 Troubleshooting

### Issue: "OPENAI_API_KEY not set"

**Solution:**
```bash
export OPENAI_API_KEY='sk-your-key-here'
# Or add to .env file
```

### Issue: "CORS error" in browser console

**Solution:**
1. Check backend logs for CORS_ORIGINS
2. Ensure your frontend URL is included
3. Update `.env`:
   ```
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

### Issue: "Audio file not found" (404)

**Solution:**
- Check `tts_output/` directory exists
- Verify audio was generated (check backend logs)
- Try generating new audio

### Issue: "TTS generation failed"

**Possible causes:**
1. Invalid API key → Check `OPENAI_API_KEY`
2. Text too long → OpenAI limit is 4096 characters
3. Network issues → Check internet connection
4. API quota exceeded → Check OpenAI dashboard

---

## 📊 Code Integration Points

### Frontend Changes (voice_shopping_assistant_ui.tsx)

| Line | Change | Description |
|------|--------|-------------|
| 27-30 | Added | `audioRef` and `API_BASE_URL` |
| 197-266 | Updated | `playTTS()` - Real API integration |
| 268-305 | Added | `fetchQueryResults()` function |
| 171-199 | Updated | `processAudio()` - Calls backend |

### Backend Structure

```python
voice/
├── __init__.py           # Module exports
├── tts.py               # Core TTS functionality
│   ├── synthesize_speech()        # Main TTS function
│   ├── synthesize_speech_chunked() # For long text
│   └── estimate_audio_duration()   # Duration estimation
│
└── api.py               # FastAPI REST API
    ├── /health          # Health check
    ├── POST /api/tts    # Generate TTS
    ├── GET /api/tts/audio/{id}  # Serve audio
    ├── POST /api/query  # Complete pipeline
    └── POST /api/cleanup # Clean old files
```

---

## 🎯 Next Steps

### Immediate Enhancements
1. **Add voice selection UI** - Let users choose voice
2. **Add download button** - Download generated audio
3. **Add audio caching** - Cache responses for same queries
4. **Add loading states** - Better UX during TTS generation

### Future Features
1. **ASR Integration** - Add Whisper for speech-to-text
2. **Streaming TTS** - Stream audio as it's generated
3. **Voice cloning** - Use ElevenLabs for custom voices
4. **Multi-language** - Support languages beyond English

---

## 📚 Related Documentation

- [Integration Guide](handoff_notes/integration_guide.md) - Full team integration guide
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenAI TTS API Docs](https://platform.openai.com/docs/guides/text-to-speech)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## ✅ Checklist

**Backend Setup:**
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with `OPENAI_API_KEY`
- [ ] Backend starts without errors (`uvicorn voice.api:app --reload`)
- [ ] Health check returns 200 (`curl http://localhost:8000/health`)

**Frontend Setup:**
- [ ] Frontend env configured (`REACT_APP_API_URL` or `VITE_API_URL`)
- [ ] Frontend updated with new TSX code
- [ ] Frontend dev server running
- [ ] No CORS errors in browser console

**Integration Testing:**
- [ ] TTS generation works (`POST /api/tts`)
- [ ] Audio playback works in frontend
- [ ] Query pipeline works (`POST /api/query`)
- [ ] Audio progress bar updates correctly

---

## 🆘 Support

If you encounter issues:

1. **Check logs:**
   - Backend: Console where uvicorn is running
   - Frontend: Browser DevTools Console

2. **Verify setup:**
   ```bash
   # Backend health
   curl http://localhost:8000/health

   # API key set
   echo $OPENAI_API_KEY
   ```

3. **Common fixes:**
   - Restart backend server
   - Clear browser cache
   - Check firewall/antivirus
   - Verify port 8000 is not in use

---

## 📄 License

This integration follows the same license as the main project.

**Happy coding! 🎉**
