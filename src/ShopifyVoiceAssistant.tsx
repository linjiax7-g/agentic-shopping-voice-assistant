import { useState, useRef } from 'react';
 

const ShopifyVoiceAssistant = () => {
  const [recordingState, setRecordingState] = useState('idle');
  const [audioBlob, setAudioBlob] = useState<any>(null);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgentStep, setCurrentAgentStep] = useState<any>(null);
  const [agentSteps, setAgentSteps] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [expandedLog, setExpandedLog] = useState(false);
  const [answerTtsProgress, setAnswerTtsProgress] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [waveformData, setWaveformData] = useState<number[]>([]);
  const [isPlayingRecorded, setIsPlayingRecorded] = useState(false);
  const [recordedProgress, setRecordedProgress] = useState(0);
  const [showTranscript, setShowTranscript] = useState(false);
  const [isPlayingTranscriptTTS, setIsPlayingTranscriptTTS] = useState(false);
  const [transcriptTtsProgress, setTranscriptTtsProgress] = useState(0);
  const [isPlayingAnswerTTS, setIsPlayingAnswerTTS] = useState(false);
  const [answerTranscript, setAnswerTranscript] = useState('');

  const recordingIntervalRef = useRef<any>(null);
  const waveformIntervalRef = useRef<any>(null);
  
  const mediaRecorderRef = useRef<any>(null);
  const audioContextRef = useRef<any>(null);
  const analyserRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);
  const recordedAudioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptAudioRef = useRef<HTMLAudioElement | null>(null);
  const answerAudioRef = useRef<HTMLAudioElement | null>(null);

  const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const mockResult = {
    query: "Recommend an eco-friendly stainless-steel cleaner under fifteen dollars.",
    answer: "I found 3 products matching your criteria. My top recommendation is Brand X Steel-Safe Eco Cleaner—it has a 4.6★ rating with over 2,800 reviews and is typically priced at $12.49. This product uses plant-based surfactants and is fully biodegradable. I've also identified 2 alternative options that may suit your needs.",
    task: 'recommendation',
    constraints: {
      price: { min: 0, max: 15 },
      material: 'Eco-Friendly',
      category: 'Cleaner'
    },
    products: [
      {
        id: 1,
        title: 'Brand X Steel-Safe Eco Cleaner',
        price: 12.49,
        rating: 4.6,
        ratingCount: 2843,
        brand: 'Brand X',
        material: 'Stainless Steel + Eco',
        description: 'Plant-based surfactants, biodegradable formula',
        source: [{ type: 'private', docId: 'B07XYZ123', label: 'Catalog' }, { type: 'web', url: 'https://amazon.com', label: 'Amazon' }],
        ingredients: 'Water, plant-based surfactants, essential oils',
        reviewSample: "Best eco-friendly cleaner I've used. Doesn't streak!"
      },
      {
        id: 2,
        title: 'Brand Y Eco Clear Cleaner',
        price: 14.99,
        rating: 4.2,
        ratingCount: 1203,
        brand: 'Brand Y',
        material: 'Stainless Steel',
        description: 'Natural ingredients, no harsh chemicals',
        source: [{ type: 'web', url: 'https://walmart.com', label: 'Walmart' }],
        ingredients: 'Water, plant extracts, vinegar',
        reviewSample: 'Great value, mild smell'
      },
      {
        id: 3,
        title: 'Budget Shine Cleaner',
        price: 9.99,
        rating: 3.8,
        ratingCount: 456,
        brand: 'Budget Shine',
        material: 'Plastic Safe',
        description: 'Affordable all-purpose cleaner',
        source: [{ type: 'private', docId: 'B09ABC789', label: 'Catalog' }],
        ingredients: 'Water, cleaning agents, alcohol',
        reviewSample: 'Good for the price, slight chemical smell'
      }
    ],
    stepLog: [
      { node: 'router', status: 'completed', message: 'Intent Classification', detail: 'Identified: Recommendation task. Constraints: price ≤ $15, material: eco-friendly', timestamp: 0 },
      { node: 'planner', status: 'completed', message: 'Retrieval Planning', detail: 'Planned hybrid search: Private RAG + Live web search', timestamp: 0.8 },
      { node: 'retriever', status: 'completed', message: 'Product Retrieval', detail: 'Retrieved 5 products. Filtered to 3 eco-friendly items under $15', timestamp: 1.6 },
      { node: 'answerer', status: 'completed', message: 'Answer Generation', detail: 'Generated natural language response with citations', timestamp: 2.4 }
    ]
  };

  const playRecordedAudio = async () => {
    try {
      if (!audioBlob) return;
      if (isPlayingRecorded) {
        if (recordedAudioRef.current) {
          recordedAudioRef.current.pause();
          recordedAudioRef.current.currentTime = 0;
        }
        setIsPlayingRecorded(false);
        setRecordedProgress(0);
        return;
      }
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      recordedAudioRef.current = audio;
      setIsPlayingRecorded(true);
      setRecordedProgress(0);
      audio.ontimeupdate = () => {
        if (audio.duration) {
          const progress = (audio.currentTime / audio.duration) * 100;
          setRecordedProgress(progress);
        }
      };
      audio.onended = () => {
        setIsPlayingRecorded(false);
        setRecordedProgress(100);
        setTimeout(() => setRecordedProgress(0), 500);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setIsPlayingRecorded(false);
        setRecordedProgress(0);
        URL.revokeObjectURL(url);
        alert('Failed to play recording.');
      };
      await audio.play();
    } catch (e) {
      setIsPlayingRecorded(false);
      setRecordedProgress(0);
      alert('Playback error.');
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });
      const mimeType = (window as any).MediaRecorder && (window as any).MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/wav';
      const mediaRecorder = new MediaRecorder(stream as MediaStream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      const chunks: Blob[] = [];
      mediaRecorder.ondataavailable = (e: any) => chunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        setAudioBlob(blob);
        processAudio();
      };
      setRecordingState('recording');
      setRecordingTime(0);
      setLiveTranscript('');
      setWaveformData([]);
      mediaRecorder.start();
      recordingIntervalRef.current = setInterval(() => { setRecordingTime((t) => t + 100); }, 100);
      const audioContext = new ((window as any).AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream as MediaStream);
      source.connect(analyser);
      analyserRef.current = analyser;
      waveformIntervalRef.current = setInterval(() => {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setWaveformData((prev) => [...prev.slice(-19), avg]);
      }, 50);
      try {
        const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SR) {
          const recognition = new SR();
          recognitionRef.current = recognition;
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';
          recognition.onresult = (event: any) => {
            let interim = '';
            let final = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
              const tr = event.results[i][0].transcript.trim();
              if (event.results[i].isFinal) final += tr + ' ';
              else interim += tr + ' ';
            }
            if (interim) setLiveTranscript(interim);
            if (final) setFinalTranscript((prev) => (prev ? `${prev} ${final}` : final));
          };
          recognition.onerror = () => {};
          recognition.onend = () => {};
          recognition.start();
        }
      } catch (e) {
        // ignore recognition errors
      }
    } catch (err) {
      alert('Microphone access denied. Please allow microphone access in your browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
    }
    clearInterval(recordingIntervalRef.current);
    clearInterval(waveformIntervalRef.current);
    setRecordingState('idle');
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
    setFinalTranscript((prev) => prev || liveTranscript);
    setLiveTranscript('');
    setShowTranscript(false);
    if (!finalTranscript && audioBlob) {
      const fd = new FormData();
      const file = new File([audioBlob], 'recording.wav', { type: audioBlob.type || 'audio/wav' });
      fd.append('audio_file', file);
      fetch(`${API_BASE_URL}/api/asr`, { method: 'POST', body: fd })
        .then(async (r) => {
          if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            throw new Error(err.detail || 'ASR failed');
          }
          return r.json();
        })
        .then((data) => {
          if (data && data.text) {
            setFinalTranscript(data.text);
          }
        })
        .catch(() => {});
    }
  };

  

  const openAudioFilePicker = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/mp3,audio/wav';
    input.onchange = async (e: any) => {
      const target = e.target as HTMLInputElement;
      const file = target.files && target.files[0];
      if (file) {
        setAudioBlob(file);
        processAudio();
        try {
          const fd = new FormData();
          fd.append('audio_file', file);
          const r = await fetch(`${API_BASE_URL}/api/asr`, { method: 'POST', body: fd });
          if (r.ok) {
            const data = await r.json();
            if (data && data.text) setFinalTranscript(data.text);
          }
        } catch {}
      }
    };
    input.click();
  };

  const processAudio = async () => {
    setRecordingState('processing');
    setIsProcessing(true);
    setAgentSteps([]);
    const steps = mockResult.stepLog;
    let index = 0;
    const processStep = () => {
      if (index < steps.length) {
        const step = steps[index];
        setCurrentAgentStep(step.node);
        setAgentSteps((prev) => [...prev, { ...step, status: 'completed' }]);
        index++;
        setTimeout(processStep, 800);
      } else {
        setCurrentAgentStep(null);
        setIsProcessing(false);
        setRecordingState('idle');
        const query = mockResult.query;
        fetchQueryResults(query);
      }
    };
    processStep();
  };

  

  const playTranscriptTTS = async () => {
    if (isPlayingTranscriptTTS) {
      if (transcriptAudioRef.current) {
        transcriptAudioRef.current.pause();
        transcriptAudioRef.current.currentTime = 0;
      }
      setIsPlayingTranscriptTTS(false);
      setTranscriptTtsProgress(0);
    } else {
      try {
        const text = finalTranscript || liveTranscript || 'Transcript not available';
        setIsPlayingTranscriptTTS(true);
        setTranscriptTtsProgress(0);
        const response = await fetch(`${API_BASE_URL}/api/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice: 'alloy' })
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'TTS generation failed');
        }
        const data = await response.json();
        const audio = new Audio(`${API_BASE_URL}${data.audio_url}`);
        transcriptAudioRef.current = audio;
        audio.ontimeupdate = () => {
          if (audio.duration) {
            const progress = (audio.currentTime / audio.duration) * 100;
            setTranscriptTtsProgress(progress);
          }
        };
        audio.onended = () => {
          setIsPlayingTranscriptTTS(false);
          setTranscriptTtsProgress(100);
          setTimeout(() => setTranscriptTtsProgress(0), 500);
        };
        audio.onerror = () => {
          setIsPlayingTranscriptTTS(false);
          setTranscriptTtsProgress(0);
          alert('Failed to play audio. Please try again.');
        };
        await audio.play();
      } catch (error: any) {
        setIsPlayingTranscriptTTS(false);
        setTranscriptTtsProgress(0);
        alert(`Failed to generate speech: ${error.message}`);
      }
    }
  };

  const playAnswerTTS = async () => {
    if (isPlayingAnswerTTS) {
      if (answerAudioRef.current) {
        answerAudioRef.current.pause();
        answerAudioRef.current.currentTime = 0;
      }
      setIsPlayingAnswerTTS(false);
      setAnswerTtsProgress(0);
    } else {
      try {
        const text = result?.answer || 'Answer not available';
        setIsPlayingAnswerTTS(true);
        setAnswerTtsProgress(0);
        const response = await fetch(`${API_BASE_URL}/api/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice: 'alloy' })
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'TTS generation failed');
        }
        const data = await response.json();
        const audio = new Audio(`${API_BASE_URL}${data.audio_url}`);
        answerAudioRef.current = audio;
        audio.ontimeupdate = () => {
          if (audio.duration) {
            const progress = (audio.currentTime / audio.duration) * 100;
            setAnswerTtsProgress(progress);
          }
        };
        audio.onended = () => {
          setIsPlayingAnswerTTS(false);
          setAnswerTtsProgress(100);
          setTimeout(() => setAnswerTtsProgress(0), 500);
        };
        audio.onerror = () => {
          setIsPlayingAnswerTTS(false);
          setAnswerTtsProgress(0);
          alert('Failed to play audio. Please try again.');
        };
        const blobResp = await fetch(`${API_BASE_URL}${data.audio_url}`);
        if (blobResp.ok) {
          const audioBlob = await blobResp.blob();
          const fd = new FormData();
          fd.append('audio_file', new File([audioBlob], 'answer.mp3', { type: audioBlob.type || 'audio/mpeg' }));
          try {
            const asrResp = await fetch(`${API_BASE_URL}/api/asr`, { method: 'POST', body: fd });
            if (asrResp.ok) {
              const asrData = await asrResp.json();
              if (asrData && asrData.text) setAnswerTranscript(asrData.text);
            }
          } catch {}
        }
        await audio.play();
      } catch (error: any) {
        setIsPlayingAnswerTTS(false);
        setAnswerTtsProgress(0);
        alert(`Failed to generate speech: ${error.message}`);
      }
    }
  };

  const toggleTranscript = async () => {
    const next = !showTranscript;
    setShowTranscript(next);
    if (next) {
      if (isProcessing) {
        if (!isPlayingRecorded) {
          await playRecordedAudio();
        }
      } else {
        if (!finalTranscript && audioBlob) {
          try {
            const fd = new FormData();
            const file = new File([audioBlob], 'recording.wav', { type: audioBlob.type || 'audio/wav' });
            fd.append('audio_file', file);
            const r = await fetch(`${API_BASE_URL}/api/asr`, { method: 'POST', body: fd });
            if (r.ok) {
              const data = await r.json();
              if (data && data.text) setFinalTranscript(data.text);
            }
          } catch {}
        }
        await playTranscriptTTS();
      }
    } else {
      if (transcriptAudioRef.current) {
        transcriptAudioRef.current.pause();
        transcriptAudioRef.current.currentTime = 0;
      }
      setIsPlayingTranscriptTTS(false);
      setTranscriptTtsProgress(0);
    }
  };

  const fetchQueryResults = async (query: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Query failed');
      }
      const data = await response.json();
      setResult({
        query: data.query,
        answer: data.answer,
        task: data.task,
        constraints: data.constraints,
        products: data.products || [],
        citations: data.citations || [],
        stepLog: agentSteps
      });
      setAnswerTranscript(data.answer || '');
    } catch (error: any) {
      setResult(mockResult);
      setAnswerTranscript(mockResult.answer);
      alert(`API Error: ${error.message}. Showing mock data instead.`);
    }
  };

  return (
    <div className="pixel-page">
      <nav className="pixel-nav">
        <div className="pixel-main" style={{ paddingTop: 16, paddingBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 className="pixel-title">Agentic Voice-to-Voice AI Assistant</h1>
          </div>
        </div>
      </nav>

      <main className="pixel-main">
        {/* Input Section */}
        <div className="mb-12">
          <div className="mb-8"></div>

          <div className="pixel-card">
            {/* Recording Controls */}
            <div className="space-y-6">
              {/* Mic Button & Playback/Transcript */}
              <div className="flex flex-col items-center gap-6">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    aria-label={recordingState === 'recording' ? 'Stop recording' : 'Start recording'}
                    onClick={recordingState === 'recording' ? stopRecording : startRecording}
                    disabled={isProcessing}
                    className={`pixel-button pixel-button--row ${
                      recordingState === 'recording' ? 'pixel-button--danger' : isProcessing ? 'pixel-button--secondary' : 'pixel-button--green'
                    }`}
                    style={{ padding: '0 12px' }}
                  >
                    {recordingState === 'recording' ? '🔴 Recording' : '🎤 Click to record'}
                  </button>

                  <button
                    type="button"
                    aria-label="Upload audio file"
                    onClick={openAudioFilePicker}
                    disabled={isProcessing || recordingState === 'recording'}
                    className="pixel-button pixel-button--row"
                  >
                    📤 Upload MP3/WAV
                  </button>

                  {recordingState !== 'recording' && audioBlob && (
                    <button
                      type="button"
                      aria-expanded={showTranscript}
                      onClick={toggleTranscript}
                      className={`pixel-button pixel-button--row ${showTranscript ? 'pixel-button--primary' : 'pixel-button--secondary'}`}
                    >
                      🎧 My Audio
                    </button>
                  )}
                </div>

                <div className="text-center">
                  {recordingState === 'recording' && (
                    <p className="text-sm text-gray-600 mt-2">{(recordingTime / 1000).toFixed(1)}s</p>
                  )}
                </div>
              </div>
              {isPlayingRecorded && (
                <div style={{ width: '100%', maxWidth: 480, margin: '0 auto' }}>
                  <div className="pixel-progress">
                    <div className="bar" style={{ width: `${recordedProgress}%` }} />
                  </div>
                  <p style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{recordedProgress.toFixed(0)}% • Your recording</p>
                </div>
              )}
              {/* Waveform */}
              {recordingState === 'recording' && (
                <div className="pixel-card" style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', gap: 4, height: 64 }}>
                  {waveformData.map((value, i) => (
                    <div
                      key={i}
                      style={{ flex: 1, background: '#48d38a', height: `${Math.max(20, (value / 255) * 100)}%` }}
                    />
                  ))}
                </div>
              )}

              {/* Live Transcript */}
              {liveTranscript && (
                <div className="pixel-card">
                  <p style={{ fontSize: 16, fontWeight: 400, color: '#222', marginBottom: 8 }}>LIVE TRANSCRIPT</p>
                  <p style={{ fontSize: 16, color: '#222', fontWeight: 400 }}>{liveTranscript}</p>
                </div>
              )}

              {showTranscript && recordingState !== 'recording' && (
                <div className="pixel-card">
                  <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 16 }}>Audio Transcript</h3>
                  {finalTranscript ? (
                    <p style={{ fontSize: 16, color: '#222', fontWeight: 400 }}>{finalTranscript}</p>
                  ) : (
                    <p style={{ fontSize: 13, color: '#666' }}>Transcript unavailable in this browser.</p>
                  )}
                </div>
              )}

              {showTranscript && isPlayingTranscriptTTS && (
                <div style={{ width: '100%', maxWidth: 480, margin: '12px auto 0' }}>
                  <div className="pixel-progress">
                    <div className="bar" style={{ width: `${transcriptTtsProgress}%` }} />
                  </div>
                  <p style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{transcriptTtsProgress.toFixed(0)}% • Listening to transcript</p>
                </div>
              )}

              {/* File Upload & Submit */}
              
            </div>
          </div>
        </div>

        {/* Agent Processing */}
        {isProcessing && (
          <div style={{ marginBottom: 48 }}>
            <div style={{ marginBottom: 24 }}>
              <h3 className="pixel-section-title">Processing Your Request</h3>
            </div>

            <div className="pixel-card" style={{ padding: 16 }}>
              {mockResult.stepLog.map((step, idx) => {
                const isActive = currentAgentStep === step.node;
                const isCompleted = agentSteps.some((s) => s.node === step.node);
                return (
                  <div
                    key={idx}
                    className="pixel-card"
                    style={{ marginBottom: 12, background: isActive ? '#e8ffe8' : isCompleted ? '#ffffff' : '#ffffff', borderColor: isActive ? '#067e06' : isCompleted ? '#111111' : '#111111' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                      <div style={{ marginTop: 2 }}>
                        {isActive ? (
                          <div style={{ width: 24, height: 24, border: '4px solid #067e06' }}></div>
                        ) : isCompleted ? (
                          <span>✅</span>
                        ) : (
                          <div style={{ width: 24, height: 24, border: '4px solid #cccccc' }}></div>
                        )}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 16, fontWeight: 700, color: '#222', textTransform: 'capitalize' }}>{step.node}</p>
                        <p style={{ fontSize: 16, color: '#666', marginTop: 4 }}>{step.message}</p>
                        <p style={{ fontSize: 16, color: '#777', marginTop: 8 }}>{step.detail}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Technical Details Toggle */}
            <button
              onClick={() => setExpandedLog(!expandedLog)}
              className="pixel-button pixel-button--secondary"
              style={{ marginTop: 16 }}
            >
              {expandedLog ? '▲' : '▼'} {expandedLog ? 'Hide' : 'Show'} Technical Details
            </button>
            {expandedLog && (
              <div style={{ marginTop: 12, background: '#111', padding: 12, color: '#eaeaea', fontFamily: 'monospace', fontSize: 12, overflow: 'auto', maxHeight: 160 }}>
                {agentSteps.map((step, idx) => (
                  <div key={idx} style={{ color: '#4ade80' }}>
                    [{step.timestamp}s] <span style={{ color: '#93c5fd' }}>[{step.node.toUpperCase()}]</span> {step.detail}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {result && !isProcessing && (
          <div style={{ display: 'grid', gap: 24 }}>
            {/* Answer Section */}
            <div className="pixel-card">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="pixel-title" style={{ marginBottom: 8 }}>Recommendation</h3>
                </div>
                
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
                <button
                  type="button"
                  aria-label="Play recommendation audio"
                  onClick={playAnswerTTS}
                  className="pixel-button pixel-button--row pixel-button--secondary"
                >
                  🔊 Play
                </button>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, minHeight: 48 }}>
                  <div style={{ flex: 1 }}>
                    <div className="pixel-progress">
                      <div className="bar" style={{ width: `${answerTtsProgress}%` }} />
                    </div>
                  </div>
                  <span style={{ fontSize: 12, color: '#666' }}>{answerTtsProgress.toFixed(0)}% • Playing</span>
                </div>
              </div>
              {answerTranscript && (
                <div className="pixel-card" style={{ marginTop: 12 }}>
                  <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 16 }}>TTS Transcript</h3>
                  <p style={{ fontSize: 16, color: '#222', fontWeight: 400 }}>{answerTranscript}</p>
                </div>
              )}
              
              <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                <span style={{ fontSize: 16, fontWeight: 700, color: '#222' }}>Data Sources:</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span className="pixel-chip">🔒 2 Private Docs</span>
                  <span className="pixel-chip">🌐 1 Web Source</span>
                </div>
              </div>
            </div>

            {/* Applied Filters */}
            <div className="pixel-card">
              <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 16 }}>Applied Filters</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                <span className="pixel-chip">💰 $0 - $15</span>
                <span className="pixel-chip">🧪 Eco-Friendly</span>
                <span className="pixel-chip">📦 Cleaner</span>
              </div>
            </div>

            {/* TTS Player */}
            

            {/* Products Table */}
            <div className="pixel-card" style={{ padding: 0 }}>
              <div style={{ padding: '16px 24px', borderBottom: '4px solid var(--pixel-border)', background: '#eef1ff' }}>
                <h3 style={{ fontWeight: 700, color: '#222' }}>Detailed Comparison</h3>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table className="pixel-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Price</th>
                      <th>Rating</th>
                      <th>Type</th>
                      <th>Sources</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.products.map((product: any, idx: number) => (
                      <tr
                        key={idx}
                        onClick={() => setSelectedProduct(product)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td>
                          <div>
                            <p style={{ fontWeight: 700, color: '#222' }}>{product.title}</p>
                          </div>
                        </td>
                        <td>
                          <p style={{ fontWeight: 700, color: '#222' }}>${product.price.toFixed(2)}</p>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ color: '#f59e0b' }}>★</span>
                            <span style={{ fontWeight: 700, color: '#222' }}>{product.rating.toFixed(1)}</span>
                            <span style={{ fontSize: 12, color: '#666' }}>({product.ratingCount})</span>
                          </div>
                        </td>
                        <td>
                          <span style={{ fontSize: 14, color: '#666' }}>{(product.material || '').toLowerCase().includes('eco') ? 'Eco' : product.material}</span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            {product.source.map((src: any, i: number) => (
                              <span key={i} className="pixel-chip">
                                {src.type === 'private' ? (
                                  <>📄 {src.docId}</>
                                ) : (
                                  <>🔗 {src.label}</>
                                )}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {selectedProduct && (
        <div className="pixel-modal-overlay" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16 }}>
          <div className="pixel-modal" style={{ maxWidth: 720, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ position: 'sticky', top: 0, borderBottom: '4px solid var(--pixel-border)', padding: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'var(--pixel-card)' }}>
              <div>
                <h2 className="pixel-section-title">{selectedProduct.title}</h2>
                <p style={{ color: '#666', fontSize: 13, marginTop: 4 }}>{selectedProduct.brand}</p>
              </div>
              <button onClick={() => setSelectedProduct(null)} className="pixel-button pixel-button--secondary" style={{ padding: '6px 8px', fontSize: 12 }}>
                ✖
              </button>
            </div>

            <div style={{ padding: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <p style={{ fontSize: 12, fontWeight: 700, color: '#666', marginBottom: 8 }}>Price</p>
                  <p style={{ fontSize: 28, fontWeight: 800, color: '#067e06' }}>${selectedProduct.price.toFixed(2)}</p>
                </div>
                <div>
                  <p style={{ fontSize: 12, fontWeight: 700, color: '#666', marginBottom: 8 }}>Customer Rating</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 24 }}>⭐</span>
                    <div>
                      <p style={{ fontSize: 24, fontWeight: 800, color: '#222' }}>{selectedProduct.rating.toFixed(1)}</p>
                      <p style={{ fontSize: 12, color: '#666' }}>{selectedProduct.ratingCount.toLocaleString()} reviews</p>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 12 }}>Description</h3>
                <p style={{ color: '#333', lineHeight: 1.7 }}>{selectedProduct.description}</p>
              </div>

              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 12 }}>Ingredients</h3>
                <p className="pixel-card" style={{ padding: 16, fontSize: 14, color: '#333' }}>{selectedProduct.ingredients}</p>
              </div>

              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 12 }}>📊 Data Lineage</h3>
                <div style={{ display: 'grid', gap: 12 }}>
                  {selectedProduct.source.map((src: any, i: number) => (
                    <div key={i} className="pixel-card" style={{ padding: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                        <div>
                          <p style={{ fontWeight: 700, color: '#222', display: 'flex', alignItems: 'center', gap: 8 }}>
                            {src.type === 'private' ? (
                              <>📄 Private Catalog</>
                            ) : (
                              <>🔗 Web Source</>
                            )}
                          </p>
                          <p style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                            {src.type === 'private' ? `Document ID: ${src.docId}` : `Source: ${new URL(src.url).hostname}`}
                          </p>
                        </div>
                        {src.type === 'web' && (
                          <button onClick={() => window.open(src.url, '_blank')} className="pixel-button pixel-button--primary" style={{ padding: '6px 8px', fontSize: 12 }}>
                            Open ↗
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 24 }}>
                <h3 style={{ fontWeight: 700, color: '#222', marginBottom: 12 }}>Customer Review</h3>
                <div className="pixel-card" style={{ padding: 16 }}>
                  <p style={{ color: '#f59e0b', marginBottom: 8 }}>⭐⭐⭐⭐⭐</p>
                  <p style={{ color: '#333', fontStyle: 'italic' }}>
                    "{selectedProduct.reviewSample}"
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedProduct(null)}
                className="pixel-button pixel-button--primary"
                style={{ width: '100%', padding: '12px 16px', fontWeight: 700, marginTop: 24 }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ShopifyVoiceAssistant;