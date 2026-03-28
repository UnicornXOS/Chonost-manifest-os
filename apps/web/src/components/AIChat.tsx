// src/components/AIChat.tsx
// AI Chat Component for Craft IDE
// Provides chat interface with AI providers (Ollama, OpenRouter, etc.)

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Settings, RefreshCw, Loader2 } from "lucide-react";
import {
  aiProviderManager,
  generateText,
  generateCode,
  analyzeContent,
  type AIMessage,
} from "../lib/aiProviders";

interface ChatMessage extends AIMessage {
  id: string;
  timestamp: Date;
  isError?: boolean;
}

export default function AIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("llama3.1:8b");
  const [selectedProvider, setSelectedProvider] = useState("ollama");
  const [providers, setProviders] = useState<any[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize with welcome message
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content:
          "Hello! I'm your AI assistant. I can help you with writing, coding, analysis, and more. What would you like to work on?",
        timestamp: new Date(),
      },
    ]);

    // Load available providers
    loadProviders();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadProviders = async () => {
    const availableProviders = aiProviderManager.getAvailableProviders();
    setProviders(availableProviders);

    // Set default provider
    if (availableProviders.length > 0) {
      const defaultProvider = aiProviderManager.getDefaultProvider();
      if (defaultProvider) {
        setSelectedProvider(defaultProvider.name.toLowerCase());

        // Get available models for the provider
        if (defaultProvider.name.toLowerCase() === "ollama") {
          try {
            const ollamaProvider = aiProviderManager.getProvider("ollama");
            if (ollamaProvider) {
              const models = await (ollamaProvider as any).getAvailableModels();
              if (models.length > 0) {
                setSelectedModel(models[0]);
              }
            }
          } catch (error) {
            console.error("Failed to load Ollama models:", error);
          }
        }
      }
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Check if it's a special command
      const response = await handleSpecialCommands(input.trim());

      if (!response) {
        // Regular AI chat
        const aiResponse = await generateText(
          input.trim(),
          selectedModel,
          selectedProvider
        );

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: aiResponse,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("AI chat error:", error);

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Sorry, I encountered an error: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
        timestamp: new Date(),
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSpecialCommands = async (input: string): Promise<boolean> => {
    const lowerInput = input.toLowerCase();

    if (lowerInput.startsWith("/code ")) {
      const description = input.substring(6);
      const code = await generateCode(
        description,
        "typescript",
        selectedModel,
        selectedProvider
      );

      const codeMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Here's the TypeScript code:\n\n\`\`\`typescript\n${code}\n\`\`\``,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, codeMessage]);
      return true;
    }

    if (lowerInput.startsWith("/analyze ")) {
      const content = input.substring(9);
      const analysis = await analyzeContent(
        content,
        "improvements",
        selectedModel,
        selectedProvider
      );

      const analysisMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Content Analysis:\n\n${analysis}`,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, analysisMessage]);
      return true;
    }

    if (lowerInput === "/help") {
      const helpMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Available commands:
- /code <description> - Generate TypeScript code
- /analyze <content> - Analyze and improve content
- /help - Show this help message

You can also just chat normally with me!`,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, helpMessage]);
      return true;
    }

    return false;
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    if (window.confirm("Are you sure you want to clear the entire chat history?")) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: "Chat cleared. How can I help you?",
          timestamp: new Date(),
        },
      ]);
    }
  };

  const testConnection = async () => {
    try {
      const results = await aiProviderManager.testAllConnections();
      console.log("Connection test results:", results);

      // Reload providers after testing
      loadProviders();
    } catch (error) {
      console.error("Connection test failed:", error);
    }
  };

  return (
    <div className="ai-chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <Bot size={20} />
          <span>AI Assistant</span>
        </div>
        <div className="header-right">
          <button
            className="icon-button"
            onClick={testConnection}
            title="Test Connections"
          >
            <RefreshCw size={16} />
          </button>
          <button
            className="icon-button"
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="settings-panel">
          <div className="setting-group">
            <label>Provider:</label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              title="Select AI Provider"
            >
              {providers.map((provider) => (
                <option key={provider.name} value={provider.name.toLowerCase()}>
                  {provider.name}
                </option>
              ))}
            </select>
          </div>

          <div className="setting-group">
            <label>Model:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              title="Select AI Model"
            >
              {providers
                .find((p) => p.name.toLowerCase() === selectedProvider)
                ?.models?.map((model: string) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                )) || []}
            </select>
          </div>

          <button className="clear-button" onClick={clearChat}>
            Clear Chat
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="messages-container">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.role} ${
              message.isError ? "error" : ""
            }`}
          >
            <div className="message-avatar">
              {message.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className="message-content">
              <div className="message-text">{message.content}</div>
              <div className="message-timestamp">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">
              <Bot size={16} />
            </div>
            <div className="message-content">
              <div className="message-text">
                <Loader2 size={16} className="animate-spin" />
                Thinking...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Use /help for commands)"
          disabled={isLoading}
          rows={1}
          className="chat-input"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="send-button"
          title={
            isLoading
              ? "Thinking..."
              : !input.trim()
              ? "Please enter a message to send"
              : "Send message"
          }
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
