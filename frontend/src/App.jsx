import React, { useState, useEffect, useRef } from 'react';

const generateSessionId = () => Math.random().toString(36).substring(2, 15);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [videoId, setVideoId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isIndexing, setIsIndexing] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId] = useState(generateSessionId());
  const [indexingStatus, setIndexingStatus] = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // Determine videoId from active tab
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const url = tabs[0]?.url;
        if (url && url.includes('youtube.com/watch')) {
          try {
            const urlObj = new URL(url);
            const vParam = urlObj.searchParams.get('v');
            if (vParam) {
              setVideoId(vParam);
              indexVideo(vParam);
            } else {
              setError("No video ID found in URL.");
            }
          } catch (e) {
            setError("Error parsing URL.");
          }
        } else {
          setError("Please open a YouTube video first.");
        }
      });
    } else {
      // Setup for local dev testing outside extension
      setVideoId('dQw4w9WgXcQ'); // Placeholder
      setError("Not running in an extension environment.");
    }
  }, []);

  const fetchWithTimeout = (url, options, timeoutMs = 90000) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(url, { ...options, signal: controller.signal })
      .finally(() => clearTimeout(timer));
  };

  const indexVideo = async (id) => {
    setIsIndexing(true);
    setError(null);

    try {
      // Step 1: Wake up the server (Render free tier cold start)
      setIndexingStatus('Waking up server... (may take ~30s on first load)');
      try {
        await fetchWithTimeout(`${API_BASE_URL}/health`, {}, 60000);
      } catch (_) {
        // Health check failing is non-fatal — proceed anyway
      }

      // Step 2: Index the video — long videos can take 4-5 min to embed
      setIndexingStatus('Analyzing video transcript... (may take a few minutes for long videos)');
      const res = await fetchWithTimeout(`${API_BASE_URL}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: id }),
      }, 600000); // 10 min — long videos have many chunks to embed

      if (!res.ok) {
        throw new Error('Failed to index video.');
      }
      setMessages([{ role: 'assistant', content: 'Video indexed successfully! What would you like to know?' }]);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out. The server may be waking up — please try again in a moment.');
      } else {
        setError(err.message);
      }
    } finally {
      setIsIndexing(false);
      setIndexingStatus('');
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !videoId || isAsking || isIndexing) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsAsking(true);

    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          video_id: videoId,
          question: userMessage,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to get answer');
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err) {
      const msg = err.name === 'AbortError' ? 'Request timed out. Please try again.' : err.message;
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${msg}` }]);
    } finally {
      setIsAsking(false);
    }
  };

  // Convert "MM:SS" to seconds
  const parseTimeToSeconds = (timeStr) => {
    const parts = timeStr.split(':').map(Number);
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
  };

  const handleSeek = (timeStr) => {
    const seconds = parseTimeToSeconds(timeStr.trim());
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'seekTo', time: seconds });
      });
    }
  };

  // ── Inline renderer: bold (**text**) + timestamp buttons [MM:SS-MM:SS] ──
  const renderInline = (text, keyPrefix) => {
    // Split on **bold** spans and [timestamp] patterns simultaneously
    const parts = text.split(/(\*\*[^*]+\*\*|\[(?:\d{1,2}:\d{2}(?::\d{2})?(?:-\d{1,2}:\d{2}(?::\d{2})?)?)\])/g);
    return parts.map((part, i) => {
      const boldMatch = part.match(/^\*\*(.+)\*\*$/);
      if (boldMatch) {
        return <strong key={`${keyPrefix}-b${i}`}>{boldMatch[1]}</strong>;
      }
      const tsMatch = part.match(/^\[(\d{1,2}:\d{2}(?::\d{2})?(?:-\d{1,2}:\d{2}(?::\d{2})?)?)\]$/);
      if (tsMatch) {
        const startTime = tsMatch[1].split('-')[0];
        return (
          <button
            key={`${keyPrefix}-ts${i}`}
            className="timestamp-btn"
            onClick={() => handleSeek(startTime)}
            title="Click to jump to this point in the video"
          >
            [{tsMatch[1]}]
          </button>
        );
      }
      return part ? <span key={`${keyPrefix}-t${i}`}>{part}</span> : null;
    });
  };

  // ── Block renderer: parses markdown line-by-line into React elements ──
  const renderMessageContent = (content) => {
    const lines = content.split('\n');
    const elements = [];
    let listItems = [];
    let key = 0;

    const flushList = () => {
      if (listItems.length > 0) {
        elements.push(<ul key={`ul-${key++}`} className="msg-list">{listItems}</ul>);
        listItems = [];
      }
    };

    lines.forEach((line) => {
      // ## Heading
      const headingMatch = line.match(/^#{1,3}\s+(.+)/);
      if (headingMatch) {
        flushList();
        elements.push(
          <p key={key++} className="msg-heading">{renderInline(headingMatch[1], `h${key}`)}</p>
        );
        return;
      }

      // - Bullet point
      const bulletMatch = line.match(/^[-*]\s+(.+)/);
      if (bulletMatch) {
        listItems.push(
          <li key={`li-${key++}`} className="msg-bullet">{renderInline(bulletMatch[1], `li${key}`)}</li>
        );
        return;
      }

      // Empty line — flush pending list, add spacer
      if (line.trim() === '') {
        flushList();
        if (elements.length > 0) {
          elements.push(<div key={`sp-${key++}`} className="msg-spacer" />);
        }
        return;
      }

      // Plain paragraph line
      flushList();
      elements.push(
        <p key={key++} className="msg-para">{renderInline(line, `p${key}`)}</p>
      );
    });

    flushList();
    return elements;
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>YouTube Chat</h1>
        <div className={`status-dot ${videoId && !error ? 'online' : 'offline'}`} />
      </header>
      
      <main className="chat-window">
        {error && <div className="error-banner">{error}</div>}
        
        {isIndexing && messages.length === 0 && (
          <div className="indexing-state">
            <div className="spinner"></div>
            <p>{indexingStatus || 'Connecting...'}</p>
          </div>
        )}

        <div className="messages-container">
          {messages.map((msg, i) => (
            <div key={i} className={`message-bubble ${msg.role}`}>
              {renderMessageContent(msg.content)}
            </div>
          ))}
          {isAsking && (
            <div className="message-bubble assistant loading">
              <span className="dot"></span><span className="dot"></span><span className="dot"></span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <form className="input-area" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isIndexing ? "Indexing video..." : "Ask a question about this video..."}
          disabled={isIndexing || !videoId}
        />
        <button 
          type="submit" 
          disabled={!input.trim() || isIndexing || isAsking || !videoId}
          className="send-btn"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </div>
  );
}

export default App;
