import React, { useState, useEffect, useRef } from 'react';
import { Mic, Upload, Square, Play, Pause, X, ChevronDown, ChevronUp, Link2, FileText, Zap, CheckCircle, Clock } from 'lucide-react';

const ShopifyVoiceAssistant = () => {
  // ==================== STATE ====================
  const [recordingState, setRecordingState] = useState('idle');
  const [audioBlob, setAudioBlob] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [recordingTime, setRecordingTime] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgentStep, setCurrentAgentStep] = useState(null);
  const [agentSteps, setAgentSteps] = useState([]);
  const [result, setResult] = useState(null);
  const [expandedLog, setExpandedLog] = useState(false);
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const [ttsProgress, setTtsProgress] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [waveformData, setWaveformData] = useState([]);

  const recordingIntervalRef = useRef(null);
  const waveformIntervalRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);

  // ==================== MOCK DATA ====================
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
        reviewSample: 'Best eco-friendly cleaner I\'ve used. Doesn\'t streak!'
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

  // ==================== AUDIO RECORDING ====================
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : 'audio/wav';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      
      const chunks = [];

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mimeType });
        setAudioBlob(blob);
        console.log('Recording saved:', blob.size, 'bytes');
      };

      setRecordingState('recording');
      setRecordingTime(0);
      setLiveTranscript('');
      setWaveformData([]);
      mediaRecorder.start();

      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime((t) => t + 100);
      }, 100);

      // Waveform visualization
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyserRef.current = analyser;

      waveformIntervalRef.current = setInterval(() => {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setWaveformData((prev) => [...prev.slice(-19), avg]);
      }, 50);

    } catch (err) {
      console.error('Microphone error:', err);
      alert('Microphone access denied. Please allow microphone access in your browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
    clearInterval(recordingIntervalRef.current);
    clearInterval(waveformIntervalRef.current);
    setRecordingState('idle');
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioBlob(file);
      setFinalTranscript(`Uploaded: ${file.name}`);
      processAudio();
    }
  };

  const processAudio = () => {
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
        setResult(mockResult);
      }
    };

    processStep();
  };

  const playTTS = () => {
    if (isPlayingTTS) {
      setIsPlayingTTS(false);
      setTtsProgress(0);
    } else {
      setIsPlayingTTS(true);
      setTimeout(() => {
        setTtsProgress(100);
        setIsPlayingTTS(false);
      }, 3000);
    }
  };

  useEffect(() => {
    if (isPlayingTTS) {
      const interval = setInterval(() => {
        setTtsProgress((prev) => Math.min(prev + 2, 100));
      }, 30);
      return () => clearInterval(interval);
    }
  }, [isPlayingTTS]);

  // ==================== RENDER ====================
  return (
    <div className="min-h-screen bg-white">
      {/* Shopify-style Navigation */}
      <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-black rounded flex items-center justify-center text-white font-bold text-sm">
              S
            </div>
            <h1 className="text-lg font-semibold text-gray-900">Agentic Voice-to-Voice AI Assistant</h1>
          </div>
          <div className="text-sm text-gray-600">For Product Discovery</div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Input Section */}
        <div className="mb-12">
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Find Products Faster</h2>
            <p className="text-gray-600">Use your voice or upload audio to discover products instantly</p>
          </div>

          <div className="bg-gray-50 rounded-lg border border-gray-200 p-8">
            {/* Recording Controls */}
            <div className="space-y-6">
              {/* Mic Button */}
              <div className="flex flex-col items-center gap-6">
                <button
                  onClick={recordingState === 'recording' ? stopRecording : startRecording}
                  disabled={isProcessing}
                  className={`relative w-32 h-32 rounded-full flex items-center justify-center text-white font-bold transition transform ${
                    recordingState === 'recording'
                      ? 'bg-red-600 hover:bg-red-700 scale-100'
                      : isProcessing
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-700 hover:shadow-lg'
                  }`}
                  style={{ boxShadow: recordingState === 'recording' ? '0 0 0 8px rgba(220, 38, 38, 0.1)' : 'none' }}
                >
                  <Mic className="w-14 h-14" />
                  {recordingState === 'recording' && (
                    <div className="absolute inset-0 rounded-full border-4 border-red-400 animate-pulse"></div>
                  )}
                </button>

                <div className="text-center">
                  <p className="text-base font-semibold text-gray-900">
                    {recordingState === 'recording' ? '🔴 Recording' : '🎤 Click to record'}
                  </p>
                  {recordingState === 'recording' && (
                    <p className="text-sm text-gray-600 mt-2">{(recordingTime / 1000).toFixed(1)}s</p>
                  )}
                </div>
              </div>

              {/* Waveform */}
              {recordingState === 'recording' && (
                <div className="flex justify-center items-end gap-1 h-16 px-4 bg-white rounded-lg border border-gray-200">
                  {waveformData.map((value, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-green-600 rounded-sm transition-all"
                      style={{ height: `${Math.max(20, (value / 255) * 100)}%` }}
                    />
                  ))}
                </div>
              )}

              {/* Live Transcript */}
              {liveTranscript && (
                <div className="bg-white border border-gray-300 rounded-lg p-4">
                  <p className="text-xs font-semibold text-gray-600 mb-2">LIVE TRANSCRIPT</p>
                  <p className="text-base text-gray-900 font-medium">{liveTranscript}</p>
                  {recordingState === 'recording' && (
                    <span className="inline-block w-2 h-5 bg-green-600 ml-1 animate-pulse"></span>
                  )}
                </div>
              )}

              {/* File Upload & Submit */}
              <div className="flex gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isProcessing || recordingState === 'recording'}
                  className="px-6 py-3 border border-gray-300 text-gray-900 rounded-md hover:bg-gray-100 transition font-medium flex items-center justify-center gap-2 flex-1"
                >
                  <Upload className="w-5 h-5" /> Upload MP3/WAV
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/mp3,audio/wav"
                  onChange={handleFileUpload}
                  className="hidden"
                />

                {audioBlob && (
                  <button
                    onClick={() => {
                      setFinalTranscript(`Recording: ${(recordingTime / 1000).toFixed(1)}s`);
                      processAudio();
                    }}
                    disabled={isProcessing}
                    className="px-8 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition font-semibold flex items-center justify-center gap-2 flex-1"
                  >
                    <Zap className="w-5 h-5" /> Search
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Agent Processing */}
        {isProcessing && (
          <div className="mb-12">
            <div className="mb-6">
              <h3 className="text-2xl font-bold text-gray-900">Processing Your Request</h3>
              <p className="text-gray-600 text-sm mt-1">Our AI agents are analyzing your search in real-time</p>
            </div>

            <div className="space-y-3 bg-gray-50 border border-gray-200 rounded-lg p-6">
              {mockResult.stepLog.map((step, idx) => {
                const isActive = currentAgentStep === step.node;
                const isCompleted = agentSteps.some((s) => s.node === step.node);
                return (
                  <div
                    key={idx}
                    className={`border rounded-lg p-4 transition ${
                      isActive
                        ? 'border-green-600 bg-green-50'
                        : isCompleted
                        ? 'border-gray-300 bg-white'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="mt-0.5">
                        {isActive ? (
                          <div className="w-6 h-6 rounded-full border-2 border-green-600 border-t-transparent animate-spin"></div>
                        ) : isCompleted ? (
                          <CheckCircle className="w-6 h-6 text-green-600" />
                        ) : (
                          <div className="w-6 h-6 rounded-full border-2 border-gray-300"></div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900 capitalize">{step.node}</p>
                        <p className="text-sm text-gray-600 mt-1">{step.message}</p>
                        <p className="text-xs text-gray-500 mt-2">{step.detail}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Technical Details Toggle */}
            <button
              onClick={() => setExpandedLog(!expandedLog)}
              className="mt-4 flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              {expandedLog ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {expandedLog ? 'Hide' : 'Show'} Technical Details
            </button>
            {expandedLog && (
              <div className="mt-3 bg-gray-900 rounded-lg p-4 text-gray-100 font-mono text-xs space-y-1 overflow-auto max-h-40">
                {agentSteps.map((step, idx) => (
                  <div key={idx} className="text-green-400">
                    [{step.timestamp}s] <span className="text-blue-300">[{step.node.toUpperCase()}]</span> {step.detail}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {result && !isProcessing && (
          <div className="space-y-8">
            {/* Answer Section */}
            <div className="border border-gray-200 rounded-lg p-8 bg-white">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-600 uppercase mb-1">Recommendation</h3>
                  <h2 className="text-2xl font-bold text-gray-900">Top Results for You</h2>
                </div>
                <div className="px-3 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                  3 Products Found
                </div>
              </div>
              <p className="text-gray-700 leading-relaxed text-base">{result.answer}</p>
              <div className="mt-6 pt-6 border-t border-gray-200 flex flex-wrap gap-3">
                <span className="text-sm font-medium text-gray-600">Data Sources:</span>
                <div className="flex gap-2 flex-wrap">
                  <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded">🔒 2 Private Docs</span>
                  <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded">🌐 1 Web Source</span>
                </div>
              </div>
            </div>

            {/* Applied Filters */}
            <div className="border border-gray-200 rounded-lg p-6 bg-white">
              <h3 className="font-semibold text-gray-900 mb-4">Applied Filters</h3>
              <div className="flex flex-wrap gap-3">
                <span className="px-4 py-2 bg-gray-100 text-gray-800 rounded-md text-sm font-medium">
                  💰 $0 - $15
                </span>
                <span className="px-4 py-2 bg-gray-100 text-gray-800 rounded-md text-sm font-medium">
                  🧪 Eco-Friendly
                </span>
                <span className="px-4 py-2 bg-gray-100 text-gray-800 rounded-md text-sm font-medium">
                  📦 Cleaner
                </span>
              </div>
            </div>

            {/* TTS Player */}
            <div className="border border-gray-200 rounded-lg p-6 bg-white">
              <h3 className="font-semibold text-gray-900 mb-4">Listen to Results</h3>
              <div className="flex items-center gap-4">
                <button
                  onClick={playTTS}
                  className="w-12 h-12 rounded-full bg-green-600 text-white flex items-center justify-center hover:bg-green-700 transition flex-shrink-0"
                >
                  {isPlayingTTS ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                </button>

                <div className="flex-1">
                  <div className="w-full h-2 bg-gray-300 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-600 transition-all"
                      style={{ width: `${ttsProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mt-2">{ttsProgress}% • 0:45 seconds</p>
                </div>

                <button className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition">
                  📜 Transcript
                </button>
              </div>
            </div>

            {/* Products Table */}
            <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h3 className="font-semibold text-gray-900">Detailed Comparison</h3>
                <p className="text-sm text-gray-600 mt-1">Click any product to see full details and data lineage</p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50">
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Product</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Price</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Rating</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Type</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Sources</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.products.map((product, idx) => (
                      <tr
                        key={idx}
                        onClick={() => setSelectedProduct(product)}
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition"
                      >
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-semibold text-gray-900">{product.title}</p>
                            <p className="text-sm text-gray-600">{product.brand}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="font-semibold text-gray-900">${product.price.toFixed(2)}</p>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-1">
                            <span className="text-yellow-500">★</span>
                            <span className="font-semibold text-gray-900">{product.rating.toFixed(1)}</span>
                            <span className="text-xs text-gray-600">({product.ratingCount})</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm text-gray-600">{product.material}</span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex gap-2 flex-wrap">
                            {product.source.map((src, i) => (
                              <button
                                key={i}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (src.type === 'web') window.open(src.url, '_blank');
                                }}
                                className={`px-3 py-1 text-xs font-medium rounded flex items-center gap-1 transition ${
                                  src.type === 'private'
                                    ? 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                                    : 'bg-green-100 text-green-800 hover:bg-green-200'
                                }`}
                              >
                                {src.type === 'private' ? (
                                  <>
                                    <FileText className="w-3 h-3" /> {src.docId}
                                  </>
                                ) : (
                                  <>
                                    <Link2 className="w-3 h-3" /> {src.label}
                                  </>
                                )}
                              </button>
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

      {/* Product Detail Modal */}
      {selectedProduct && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl">
            {/* Modal Header */}
            <div className="sticky top-0 border-b border-gray-200 p-6 flex justify-between items-start bg-white">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedProduct.title}</h2>
                <p className="text-gray-600 text-sm mt-1">{selectedProduct.brand}</p>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-8 space-y-8">
              {/* Price & Rating Grid */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-sm font-semibold text-gray-600 mb-2">Price</p>
                  <p className="text-3xl font-bold text-green-600">${selectedProduct.price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-600 mb-2">Customer Rating</p>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">⭐</span>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">{selectedProduct.rating.toFixed(1)}</p>
                      <p className="text-xs text-gray-600">{selectedProduct.ratingCount.toLocaleString()} reviews</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Description</h3>
                <p className="text-gray-700 leading-relaxed">{selectedProduct.description}</p>
              </div>

              {/* Ingredients */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Ingredients</h3>
                <p className="text-gray-700 text-sm bg-gray-50 rounded-lg p-4 border border-gray-200">{selectedProduct.ingredients}</p>
              </div>

              {/* Data Lineage */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">📊 Data Lineage</h3>
                <div className="space-y-3">
                  {selectedProduct.source.map((src, i) => (
                    <div
                      key={i}
                      className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-semibold text-gray-900 flex items-center gap-2">
                            {src.type === 'private' ? (
                              <>
                                <FileText className="w-4 h-4" /> Private Catalog
                              </>
                            ) : (
                              <>
                                <Link2 className="w-4 h-4" /> Web Source
                              </>
                            )}
                          </p>
                          <p className="text-xs text-gray-600 mt-1">
                            {src.type === 'private'
                              ? `Document ID: ${src.docId}`
                              : `Source: ${new URL(src.url).hostname}`}
                          </p>
                        </div>
                        {src.type === 'web' && (
                          <button
                            onClick={() => window.open(src.url, '_blank')}
                            className="px-3 py-1 bg-green-600 text-white text-xs font-semibold rounded hover:bg-green-700 transition"
                          >
                            Open ↗
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Review */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Customer Review</h3>
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <p className="text-yellow-500 mb-2">⭐⭐⭐⭐⭐</p>
                  <p className="text-gray-700 italic">"{selectedProduct.reviewSample}"</p>
                </div>
              </div>

              {/* Close Button */}
              <button
                onClick={() => setSelectedProduct(null)}
                className="w-full py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition font-semibold"
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