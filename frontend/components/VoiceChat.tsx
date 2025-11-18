import React, { useState, useRef, useEffect, useMemo } from "react";
import type { KeyboardEvent } from "react";
import { Mic, Send, Play, Pause, Settings, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "@/lib/utils";

interface AgentDocument {
  title?: string;
  price?: number;
  brand?: string;
  source?: string;
  [key: string]: any;
}

interface AgentMetadata {
  citations?: string[];
  retrievedDocs?: AgentDocument[];
  plan?: Record<string, any>;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isVoiceInput?: boolean;
  metadata?: AgentMetadata;
}

interface VoiceSettings {
  voiceId: string;
  language: string;
}

interface VoiceOption {
  id: string;
  name: string;
  language: string;
}

interface AgentAPIResponse {
  query: string;
  answer: string;
  citations: string[];
  plan: Record<string, any>;
  retrieved_docs: AgentDocument[];
  step_log: Record<string, any>[];
}

const FALLBACK_LANGUAGES = ["en", "zh", "es", "fr", "de", "ja"];

export default function VoiceChat() {
  // Message state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  
  // Default voices as fallback
  const DEFAULT_VOICES: VoiceOption[] = [
    { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel", language: "en" },
    { id: "pNInz6obpgDQGcFmaJgB", name: "Adam", language: "en" },
    { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella", language: "en" },
    { id: "ErXwobaYiN019PkySvjV", name: "Antoni", language: "en" },
  ];
  
  // Voice settings
  const [userSettings, setUserSettings] = useState<VoiceSettings>({
    voiceId: "21m00Tcm4TlvDq8ikWAM", // Default Rachel voice
    language: "en"
  });
  const [agentSettings, setAgentSettings] = useState<VoiceSettings>({
    voiceId: "pNInz6obpgDQGcFmaJgB", // Default Adam voice
    language: "en"
  });
  const [availableVoices, setAvailableVoices] = useState<VoiceOption[]>(DEFAULT_VOICES);
  const [showSettings, setShowSettings] = useState(false);
  
  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [realtimeTranscript, setRealtimeTranscript] = useState("");
  
  // Playback state
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [isAgentResponding, setIsAgentResponding] = useState(false);
  
  // Status
  const [status, setStatus] = useState<"ready" | "recording" | "transcribing" | "playing">("ready");
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const isRecordingRef = useRef<boolean>(false);
  
  // API base URL
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const WS_URL = API_BASE_URL.replace("http", "ws");
  
  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, realtimeTranscript]);
  
  // Fetch available voices on mount
  useEffect(() => {
    fetchVoices();
  }, []);

  const requestAgentResponse = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed) return;

    try {
      setIsAgentResponding(true);
      const response = await fetch(`${API_BASE_URL}/api/agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: trimmed,
          language: agentSettings.language
        })
      });

      if (!response.ok) {
        throw new Error(`Agent request failed with status ${response.status}`);
      }

      const data: AgentAPIResponse = await response.json();

      const aiMessage: Message = {
        id: `agent-${Date.now()}`,
        role: "assistant",
        content: data.answer || "I couldn't find an answer yet, please try again.",
        timestamp: new Date(),
        metadata: {
          citations: data.citations || [],
          retrievedDocs: data.retrieved_docs || [],
          plan: data.plan || {}
        }
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Agent response failed:", error);
      const fallbackMessage: Message = {
        id: `agent-error-${Date.now()}`,
        role: "assistant",
        content: "I'm having trouble reaching the product agent right now.",
        timestamp: new Date()
      };
      setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setIsAgentResponding(false);
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (processorRef.current) {
        processorRef.current.disconnect();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);
  
  // Fetch available voices
  const fetchVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/voices`);
      if (response.ok) {
        const voices = await response.json();
        if (voices && voices.length > 0) {
          setAvailableVoices(voices);
          console.log(`Loaded ${voices.length} voices from API`);

          const syncSettingsWithVoices = (prev: VoiceSettings, fallback?: VoiceOption): VoiceSettings => {
            const voiceMatch = voices.find((voice: VoiceOption) => voice.id === prev.voiceId);
            if (voiceMatch) {
              if (voiceMatch.language && voiceMatch.language !== prev.language) {
                return { ...prev, language: voiceMatch.language };
              }
              return prev;
            }
            if (fallback) {
              return {
                voiceId: fallback.id,
                language: fallback.language || prev.language
              };
            }
            return prev;
          };

          setUserSettings((prev) => syncSettingsWithVoices(prev, voices[0]));
          setAgentSettings((prev) => syncSettingsWithVoices(prev, voices[1] || voices[0]));
        } else {
          console.warn("API returned empty voices list, using defaults");
          setAvailableVoices(DEFAULT_VOICES);
        }
      } else {
        console.warn(`Failed to fetch voices: ${response.status}, using defaults`);
        setAvailableVoices(DEFAULT_VOICES);
      }
    } catch (error) {
      console.error("Failed to fetch voices:", error);
      console.log("Using default voices");
      setAvailableVoices(DEFAULT_VOICES);
    }
  };

  const languageOptions = useMemo(() => {
    const languages = new Set<string>(FALLBACK_LANGUAGES);
    availableVoices.forEach((voice) => {
      if (voice.language) {
        languages.add(voice.language);
      }
    });

    [userSettings.language, agentSettings.language].forEach((lang) => {
      if (lang) {
        languages.add(lang);
      }
    });

    return Array.from(languages);
  }, [availableVoices, userSettings.language, agentSettings.language]);

  const handleVoiceSelection = (voiceId: string, target: "user" | "agent") => {
    const selectedVoice = availableVoices.find((voice) => voice.id === voiceId);
    if (target === "user") {
      setUserSettings((prev) => ({
        ...prev,
        voiceId,
        language: selectedVoice?.language || prev.language
      }));
    } else {
      setAgentSettings((prev) => ({
        ...prev,
        voiceId,
        language: selectedVoice?.language || prev.language
      }));
    }
  };
  
  // Initialize WebSocket connection
  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    const ws = new WebSocket(`${WS_URL}/ws/voice`);
    
    ws.onopen = () => {
      console.log("WebSocket connected");
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "transcript") {
        setIsTranscribing(false);
        setStatus("ready");
        
        if (data.is_final && data.text) {
          // Add final transcript as user message
          const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: data.text,
            timestamp: new Date(),
            isVoiceInput: true
          };
          setMessages((prev) => [...prev, userMessage]);
          setRealtimeTranscript("");
          
          requestAgentResponse(data.text);
        } else if (!data.is_final) {
          // Update realtime transcript
          setRealtimeTranscript(data.text);
        }
      } else if (data.type === "error") {
        console.error("WebSocket error:", data.message);
        setIsTranscribing(false);
        setStatus("ready");
        setRealtimeTranscript("");
      }
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsTranscribing(false);
      setStatus("ready");
    };
    
    ws.onclose = () => {
      console.log("WebSocket disconnected");
      wsRef.current = null;
    };
    
    wsRef.current = ws;
  };
  
  // Start recording with AudioContext for PCM format
  const startRecording = async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      audioStreamRef.current = stream;
      
      // Connect WebSocket
      connectWebSocket();
      
      // Wait for WebSocket to be ready
      await new Promise((resolve) => {
        const checkReady = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            clearInterval(checkReady);
            resolve(true);
          }
        }, 100);
      });
      
      // Create AudioContext for PCM extraction
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      let audioChunkCount = 0;
      
      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          console.log("Skipping audio process:", { 
            isRecording: isRecordingRef.current, 
            hasWs: !!wsRef.current, 
            wsState: wsRef.current?.readyState 
          });
          return;
        }
        
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Convert Float32Array to Int16Array (PCM 16-bit)
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Convert to base64
        const base64 = btoa(
          String.fromCharCode(...new Uint8Array(pcmData.buffer))
        );
        
        // Send to WebSocket
        try {
          wsRef.current.send(JSON.stringify({
            type: "audio",
            data: base64,
            language: userSettings.language
          }));
          audioChunkCount++;
          if (audioChunkCount % 10 === 0) {
            console.log(`Sent ${audioChunkCount} audio chunks`);
          }
        } catch (error) {
          console.error("Failed to send audio data:", error);
        }
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      processorRef.current = processor;
      setIsRecording(true);
      isRecordingRef.current = true;
      setStatus("recording");
      setRealtimeTranscript("");
      
      console.log("Recording started, isRecordingRef:", isRecordingRef.current);
      
    } catch (error) {
      console.error("Failed to start recording:", error);
      alert("Failed to access microphone. Please check permissions.");
    }
  };
  
  // Stop recording
  const stopRecording = () => {
    console.log("Stopping recording...");
    setIsRecording(false);
    isRecordingRef.current = false;
    
    // Disconnect AudioContext processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    
    // Close AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    // Stop media stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
    
    // Send stop signal to WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "stop",
        language: userSettings.language
      }));
    }
    
    setIsTranscribing(true);
    setStatus("transcribing");
  };
  
  // Toggle recording
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };
  
  // Send text message
  const sendTextMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
      isVoiceInput: false
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    requestAgentResponse(userMessage.content);
  };
  
  // Play TTS audio for a message
  const playTTSAudio = async (messageId: string, text: string, role: "user" | "assistant") => {
    if (playingMessageId === messageId) {
      // Stop playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setPlayingMessageId(null);
      setStatus("ready");
      return;
    }
    
    try {
      setStatus("playing");
      setPlayingMessageId(messageId);
      
      // Get voice settings based on role
      const settings = role === "user" ? userSettings : agentSettings;
      
      // Call TTS API
      const response = await fetch(`${API_BASE_URL}/api/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: text,
          voice_id: settings.voiceId,
          language: settings.language
        })
      });
      
      if (!response.ok) {
        throw new Error("TTS request failed");
      }
      
      const data = await response.json();
      
      // Decode base64 audio and play
      const audioData = atob(data.audio_base64);
      const audioArray = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }
      
      const audioBlob = new Blob([audioArray], { type: "audio/mpeg" });
      const audioUrl = URL.createObjectURL(audioBlob);
      
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      
      audio.onended = () => {
        setPlayingMessageId(null);
        setStatus("ready");
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
      
    } catch (error) {
      console.error("Failed to play TTS audio:", error);
      setPlayingMessageId(null);
      setStatus("ready");
    }
  };
  
  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };
  
  return (
    <div className="h-screen bg-background flex flex-col w-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-light bg-background-secondary">
        <h3 className="text-body font-semibold">Voice Chat</h3>
        <Button
          onClick={() => setShowSettings(!showSettings)}
          variant="ghost"
          size="icon"
          className="h-8 w-8 hover:bg-muted rounded-full"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Settings Panel */}
      {showSettings && (
        <div className="px-4 py-3 border-b border-border-light bg-muted/30">
          <div className="space-y-3">
            {/* User Settings */}
            <div>
              <label className="text-xs font-semibold text-foreground-secondary mb-1 block">
                User Voice
              </label>
              <div className="flex gap-2">
                <select
                  value={userSettings.voiceId}
                  onChange={(e) => handleVoiceSelection(e.target.value, "user")}
                  className="flex-1 text-xs px-2 py-1.5 rounded border border-border bg-background"
                >
                  {availableVoices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name}
                    </option>
                  ))}
                </select>
                <select
                  value={userSettings.language}
                  onChange={(e) => setUserSettings({ ...userSettings, language: e.target.value })}
                  className="w-20 text-xs px-2 py-1.5 rounded border border-border bg-background"
                >
                  {languageOptions.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Agent Settings */}
            <div>
              <label className="text-xs font-semibold text-foreground-secondary mb-1 block">
                Agent Voice
              </label>
              <div className="flex gap-2">
                <select
                  value={agentSettings.voiceId}
                  onChange={(e) => handleVoiceSelection(e.target.value, "agent")}
                  className="flex-1 text-xs px-2 py-1.5 rounded border border-border bg-background"
                >
                  {availableVoices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name}
                    </option>
                  ))}
                </select>
                <select
                  value={agentSettings.language}
                  onChange={(e) => setAgentSettings({ ...agentSettings, language: e.target.value })}
                  className="w-20 text-xs px-2 py-1.5 rounded border border-border bg-background"
                >
                  {languageOptions.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex flex-col",
              message.role === "user" ? "items-end" : "items-start"
            )}
          >
            <div
              className={cn(
                "chat-bubble max-w-[85%] group",
                message.role === "user"
                  ? "chat-bubble-sent"
                  : "chat-bubble-received"
              )}
            >
              <div className="flex items-start gap-2">
                <div className="flex-1 space-y-1">
                  <p className="text-caption">{message.content}</p>
                  {message.metadata?.citations && message.metadata.citations.length > 0 && (
                    <p className="text-[10px] text-foreground-secondary">
                      Sources: {message.metadata.citations.join(", ")}
                    </p>
                  )}
                  {message.metadata?.retrievedDocs && message.metadata.retrievedDocs.length > 0 && (
                    <div className="text-[10px] text-foreground-secondary space-y-0.5">
                      {message.metadata.retrievedDocs.slice(0, 2).map((doc, index) => (
                        <div key={`${doc.title ?? "doc"}-${index}`}>
                          {doc.title ?? "Result"}
                          {doc.price !== undefined && ` • $${doc.price}`}
                          {doc.source && ` • ${doc.source}`}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {message.isVoiceInput && (
                    <Mic className="w-3 h-3 text-foreground-secondary flex-shrink-0" />
                  )}
                  <Button
                    onClick={() => playTTSAudio(message.id, message.content, message.role)}
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Play audio"
                  >
                    {playingMessageId === message.id ? (
                      <Pause className="w-3 h-3" />
                    ) : (
                      <Play className="w-3 h-3" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
            <span className="text-xs text-foreground-secondary mt-1 px-1">
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        ))}
        
        {/* Realtime transcript bubble */}
        {realtimeTranscript && (
          <div className="flex flex-col items-end">
            <div className="chat-bubble chat-bubble-sent max-w-[85%] opacity-70">
              <p className="text-caption italic">{realtimeTranscript}</p>
            </div>
            <span className="text-xs text-foreground-secondary mt-1 px-1">
              Transcribing...
            </span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <div className="p-4 border-t border-border-light bg-background">
        <div className="flex items-end gap-2 mb-2">
          <Button
            onClick={toggleRecording}
            disabled={isTranscribing || isAgentResponding}
            size="icon"
            className={cn(
              "h-10 w-10 rounded-full transition-all duration-200",
              isRecording
                ? "bg-red-500 hover:bg-red-600 animate-pulse"
                : "bg-primary hover:bg-primary-hover"
            )}
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            <Mic className="w-4 h-4" />
          </Button>
          
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isRecording || isTranscribing || isAgentResponding}
              placeholder="Type or use voice..."
              className="w-full rounded-[20px] bg-muted border-none px-4 py-2.5 text-caption focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200 disabled:opacity-50"
            />
          </div>
          
          <Button
            onClick={sendTextMessage}
            disabled={!input.trim() || isRecording || isTranscribing || isAgentResponding}
            size="icon"
            className="h-10 w-10 rounded-full bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        
        {/* Status bar */}
        <div className="text-xs text-center text-foreground-secondary">
          {status === "ready" && !isAgentResponding && "Ready"}
          {status === "ready" && isAgentResponding && "Agent thinking..."}
          {status === "recording" && "Recording..."}
          {status === "transcribing" && "Transcribing..."}
          {status === "playing" && "Playing audio..."}
        </div>
      </div>
    </div>
  );
}

