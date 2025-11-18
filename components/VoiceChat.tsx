美女吧import React, { useState, useRef, useEffect } from "react";
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

export default function VoiceChat() {
  // Message state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  
  // Voice settings
  const [userSettings, setUserSettings] = useState<VoiceSettings>({
    voiceId: "21m00Tcm4TlvDq8ikWAM", // Default Rachel voice
    language: "en"
  });
  const [agentSettings, setAgentSettings] = useState<VoiceSettings>({
    voiceId: "pNInz6obpgDQGcFmaJgB", // Default Adam voice
    language: "en"
  });
  const [availableVoices, setAvailableVoices] = useState<VoiceOption[]>([]);
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
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);
  
  // Fetch available voices
  const fetchVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/voices`);
      if (response.ok) {
        const voices = await response.json();
        setAvailableVoices(voices);
      }
    } catch (error) {
      console.error("Failed to fetch voices:", error);
      // Set default voices if fetch fails
      setAvailableVoices([
        { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel", language: "en" },
        { id: "pNInz6obpgDQGcFmaJgB", name: "Adam", language: "en" }
      ]);
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
  
  // Start recording
  const startRecording = async () => {
    try {
      console.log("=== Starting recording ===");
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("Got audio stream, tracks:", stream.getAudioTracks().length);
      
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
      
      // Create MediaRecorder
      console.log("Creating MediaRecorder...");
      console.log("Supported MIME types:", {
        webmOpus: MediaRecorder.isTypeSupported("audio/webm;codecs=opus"),
        webm: MediaRecorder.isTypeSupported("audio/webm"),
        mp4: MediaRecorder.isTypeSupported("audio/mp4")
      });
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus"
      });
      
      console.log("MediaRecorder created, MIME type:", mediaRecorder.mimeType);
      
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        console.log("ondataavailable fired, data size:", event.data.size);
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          console.log(`Audio chunk captured: ${event.data.size} bytes`);
          
          // Convert to base64 and send via WebSocket
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64data = (reader.result as string).split(",")[1];
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({
                type: "audio",
                data: base64data,
                language: userSettings.language
              }));
              console.log(`Sent audio chunk: ${base64data.length} base64 chars`);
            } else {
              console.warn(`WebSocket not open, state: ${wsRef.current?.readyState}`);
            }
          };
          reader.readAsDataURL(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
        
        console.log(`Recording stopped. Total chunks collected: ${audioChunksRef.current.length}`);
        
        // Send stop signal
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: "stop",
            language: userSettings.language
          }));
          console.log("Sent stop signal to backend");
        } else {
          console.error(`WebSocket not open when stopping. State: ${wsRef.current?.readyState}`);
        }
        
        setIsRecording(false);
        setIsTranscribing(true);
        setStatus("transcribing");
      };
      
      console.log("Starting MediaRecorder with 100ms timeslice...");
      mediaRecorder.start(100); // Collect data every 100ms
      console.log("MediaRecorder state after start:", mediaRecorder.state);
      
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setStatus("recording");
      setRealtimeTranscript("");
      
    } catch (error) {
      console.error("Failed to start recording:", error);
      alert("Failed to access microphone. Please check permissions.");
    }
  };
  
  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
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
    <div className="h-screen bg-background border-l border-border flex flex-col w-[400px]">
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
                  onChange={(e) => setUserSettings({ ...userSettings, voiceId: e.target.value })}
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
                  <option value="en">EN</option>
                  <option value="zh">ZH</option>
                  <option value="es">ES</option>
                  <option value="fr">FR</option>
                  <option value="de">DE</option>
                  <option value="ja">JA</option>
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
                  onChange={(e) => setAgentSettings({ ...agentSettings, voiceId: e.target.value })}
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
                  <option value="en">EN</option>
                  <option value="zh">ZH</option>
                  <option value="es">ES</option>
                  <option value="fr">FR</option>
                  <option value="de">DE</option>
                  <option value="ja">JA</option>
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

