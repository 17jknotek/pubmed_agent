"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

const DEFAULT_API_URL = "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
}

export default function DrivePage() {
  const apiUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL,
    []
  );

  const [connected, setConnected] = useState<boolean | null>(null);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkDriveStatus();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  async function checkDriveStatus() {
    try {
      const res = await fetch(`/api/backend/drive/status`, {
        credentials: "include",
      });
      const data = await res.json();
      setConnected(data.connected);
      if (data.connected) fetchFiles();
    } catch {
      setConnected(false);
    }
  }

  async function fetchFiles() {
    try {
      const res = await fetch(`/api/backend/drive/files`, {
        credentials: "include",
      });
      const data = await res.json();
      setFiles(data.files || []);
    } catch {
      console.error("Failed to fetch files");
    }
  }

  async function openFile(file: DriveFile) {
    setSelectedFileId(file.id);
    setSelectedFileName(file.name);
    setFileError(null);
    setFileContent("");
    setFileLoading(true);
    try {
      const res = await fetch(`/api/backend/drive/file/${encodeURIComponent(file.id)}`, {
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error("Failed to load file");
      }
      const data = await res.json();
      setFileContent(data.content || "");
    } catch {
      setFileError("Could not load file. Please try again.");
    } finally {
      setFileLoading(false);
    }
  }

  async function handleSend() {
    if (!input.trim() || chatLoading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatLoading(true);

    try {
      const res = await fetch(`/api/backend/drive/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ message: userMessage }),
      });
      if (!res.ok) {
        throw new Error("Chat failed");
      }
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response || "" },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  if (connected === null) {
    return (
      <main className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">Checking Drive connection...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <div className="max-w-4xl w-full mx-auto px-4 py-8 flex flex-col flex-1">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Drive Agent</h1>
            <p className="text-gray-400 text-sm mt-1">
              Browse and preview your Google Drive files
            </p>
          </div>
          <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm transition">
            ← PubMed Search
          </Link>
        </div>

        {!connected ? (
          /* Not connected state */
          <div className="flex-1 flex flex-col items-center justify-center gap-6">
            <div className="text-center">
              <div className="text-6xl mb-4">📂</div>
              <h2 className="text-xl font-semibold text-white mb-2">
                Connect your Google Drive
              </h2>
              <p className="text-gray-400 max-w-md">
                Grant read-only access to your Drive so the agent can answer
                questions about your files. Your token is stored securely
                server-side and never exposed to the browser.
              </p>
            </div>

            <a
              href={`/api/backend/drive/auth`}
              className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-lg font-medium transition"
            >
              Connect Google Drive
            </a>
          </div>
        ) : (
          /* Connected state — file browser + chat */
          <div className="flex flex-col flex-1 gap-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-gray-400 text-sm">
                Connected. Select a file to preview.
              </p>
              <button
                onClick={fetchFiles}
                className="text-sm text-blue-400 hover:text-blue-300 transition"
              >
                Refresh files
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* File list */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Files ({files.length})
                </p>
                {files.length === 0 ? (
                  <p className="text-gray-500 text-sm">
                    No files found (only Google Docs + text files are shown).
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {files.map((f) => {
                      const active = selectedFileId === f.id;
                      return (
                        <button
                          key={f.id}
                          onClick={() => openFile(f)}
                          className={`text-left rounded-md px-3 py-2 text-sm transition border ${
                            active
                              ? "bg-blue-950/40 border-blue-800 text-blue-200"
                              : "bg-gray-950/30 border-gray-800 text-gray-200 hover:border-gray-700"
                          }`}
                        >
                          <div className="font-medium truncate">{f.name}</div>
                          <div className="text-xs text-gray-500 truncate">{f.mimeType}</div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Preview */}
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Preview {selectedFileName ? `— ${selectedFileName}` : ""}
                </p>

                {!selectedFileId ? (
                  <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-500 text-sm">Pick a file to preview.</p>
                  </div>
                ) : fileLoading ? (
                  <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-400 text-sm">Loading…</p>
                  </div>
                ) : fileError ? (
                  <div className="flex-1 flex items-center justify-center">
                    <p className="text-red-300 text-sm">{fileError}</p>
                  </div>
                ) : (
                  <pre className="flex-1 whitespace-pre-wrap break-words text-sm text-gray-200 leading-relaxed overflow-auto rounded-md bg-gray-950/40 border border-gray-800 p-3">
                    {fileContent || "(Empty file)"}
                  </pre>
                )}
              </div>
            </div>

            {/* Chat */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col min-h-[420px]">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Chat
              </p>

              <div className="flex-1 flex flex-col gap-3 overflow-auto pr-1">
                {messages.length === 0 && (
                  <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center">
                    <p className="text-gray-400 text-sm">
                      Ask questions about your Drive files. Try:
                    </p>
                    <div className="flex flex-col gap-2">
                      {[
                        "What files do I have access to?",
                        "Summarize a file in my Drive",
                        "What topics are covered across my documents?",
                      ].map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => setInput(suggestion)}
                          className="text-blue-400 hover:text-blue-300 text-sm transition"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-2xl px-4 py-3 rounded-lg text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-gray-950/40 border border-gray-800 text-gray-200"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-950/40 border border-gray-800 px-4 py-3 rounded-lg">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:0.2s]" />
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:0.4s]" />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>

              <div className="flex gap-3 pt-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Ask anything about your Drive files..."
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
                />
                <button
                  onClick={handleSend}
                  disabled={chatLoading}
                  className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white px-6 py-3 rounded-lg font-medium transition"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}