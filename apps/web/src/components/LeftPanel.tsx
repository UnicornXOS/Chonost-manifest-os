import { useState, useEffect } from "react";
import { useAppStore } from "../state/store";
import LazyVisualDashboard from "./LazyVisualDashboard";
import { runAnalyzeOrSidecar } from "../lib/platform";
import { AIProvider, initializeAIService, chatWithAI, setProvider } from "../services/aiService";

export default function LeftPanel() {
  const { content, setData } = useAppStore();
  const [q, setQ] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<AIProvider>(AIProvider.GOOGLE);
  const [isAIReady, setIsAIReady] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>("");

  useEffect(() => {
    // Initialize default Google AI if API key is available
    const apiKey = (import.meta as any).env?.VITE_GOOGLE_AI_API_KEY;
    if (apiKey && apiKey !== 'your_google_ai_api_key_here') {
      try {
        initializeAIService({ provider: AIProvider.GOOGLE, apiKey });
        setIsAIReady(true);
        setLog((l) => [`${new Date().toLocaleTimeString()}: AI พร้อมใช้งาน (${AIProvider.GOOGLE})`, ...l]);
      } catch (error) {
        console.error('Failed to initialize AI:', error);
        setLog((l) => [`${new Date().toLocaleTimeString()}: ไม่สามารถเริ่ม AI ได้`, ...l]);
      }
    }
  }, []);

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value as AIProvider;
    setSelectedProvider(provider);
    let apiKey = '';
    switch (provider) {
      case AIProvider.GOOGLE:
        apiKey = (import.meta as any).env?.VITE_GOOGLE_AI_API_KEY || '';
        break;
      case AIProvider.OPENAI:
        apiKey = (import.meta as any).env?.VITE_OPENAI_API_KEY || '';
        break;
      case AIProvider.ANTHROPIC:
        apiKey = (import.meta as any).env?.VITE_ANTHROPIC_API_KEY || '';
        break;
      case AIProvider.XAI:
        apiKey = (import.meta as any).env?.VITE_XAI_API_KEY || '';
        break;
    }
    if (apiKey && apiKey !== `your_${provider.toLowerCase()}_api_key_here`) {
      try {
        initializeAIService({ provider, apiKey });
        setIsAIReady(true);
        setLog((l) => [`${new Date().toLocaleTimeString()}: เปลี่ยนไปใช้ ${provider} สำเร็จ`, ...l]);
      } catch (error) {
        console.error(`Failed to initialize ${provider}:`, error);
        setIsAIReady(false);
        setLog((l) => [`${new Date().toLocaleTimeString()}: ไม่สามารถเริ่ม ${provider} ได้`, ...l]);
      }
    } else {
      setIsAIReady(false);
      setLog((l) => [`${new Date().toLocaleTimeString()}: กรุณาตั้งค่า API key สำหรับ ${provider}`, ...l]);
    }
  };

  const run = async () => {
    const input = q || content;
    if (!input.trim() || !isAIReady) return;

    try {
      const messages = [{ role: 'user' as const, content: input }];
      const response = await chatWithAI(messages);
      setAnalysisResult(response);
      setQ("");
      setLog((l) => [`${new Date().toLocaleTimeString()}: แชทสำเร็จ (${selectedProvider})`, ...l]);
    } catch (error) {
      console.error('AI chat failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setAnalysisResult(`เกิดข้อผิดพลาด: ${errorMessage}`);
      setLog((l) => [`${new Date().toLocaleTimeString()}: แชทล้มเหลว`, ...l]);
    }
  };
  return (
    <div className="panel" style={{ padding: 8 }}>
      <h3>แดชบอร์ด</h3>
      <LazyVisualDashboard />
      <div className="card" style={{ marginTop: 8 }}>
        <h4 style={{ margin: "0 0 8px" }}>
          แชท AI {isAIReady && <span style={{ color: '#10b981', fontSize: '12px' }}>● {selectedProvider} พร้อม</span>}
        </h4>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", gap: 6, alignItems: 'center' }}>
            <label htmlFor="ai-provider-select" style={{ fontSize: 14, marginRight: 4 }}>AI Provider:</label>
            <select
              id="ai-provider-select"
              value={selectedProvider}
              onChange={handleProviderChange}
              style={{ padding: 4, fontSize: 14 }}
            >
              <option value={AIProvider.GOOGLE}>Google AI</option>
              <option value={AIProvider.OPENAI}>OpenAI</option>
              <option value={AIProvider.ANTHROPIC}>Anthropic</option>
              <option value={AIProvider.XAI}>xAI</option>
            </select>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="ถาม AI (เลือก provider ก่อน)"
              style={{ flex: 1 }}
              onKeyPress={(e) => e.key === 'Enter' && run()}
            />
            <button
              className="btn"
              onClick={run}
              disabled={!isAIReady || (!q.trim() && !content.trim())}
              title={
                !isAIReady
                  ? "กรุณาตั้งค่า AI provider และ API key ก่อน"
                  : !q.trim() && !content.trim()
                  ? "กรุณาป้อนข้อความที่จะส่ง"
                  : ""
              }
            >
              ส่งข้อความ
            </button>
          </div>

        {analysisResult && (
          <div style={{
            marginTop: 8,
            padding: 8,
            backgroundColor: '#f3f4f6',
            borderRadius: 4,
            maxHeight: 200,
            overflow: 'auto',
            fontSize: '14px',
            lineHeight: '1.4'
          }}>
            <strong>ผลการวิเคราะห์:</strong><br />
            {analysisResult}
          </div>
        )}

        <div style={{ marginTop: 8, maxHeight: 100, overflow: "auto", color: "#9ca3af", fontSize: '12px' }}>
          {log.slice(0, 5).map((l, i) => <div key={i}>{l}</div>)}
        </div>
        </div>
      </div>
    </div>
  );
}
