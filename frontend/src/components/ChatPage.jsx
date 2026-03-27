import { useState, useEffect, useRef } from 'react'
import { Send, Code, FileText, Check, X, RefreshCw, Download, Mic, MicOff, Globe, User, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

// ── Helpers ───────────────────────────────────────────────────────────────────
function getFileName(path) {
  const parts = (path || '').replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || path || 'Unknown'
}

function dedupeSourcesByDoc(sources) {
  if (!sources?.length) return []
  const seen = new Set()
  return sources.filter(s => {
    const key = s.document_id && s.document_id !== 'unknown'
      ? s.document_id
      : getFileName(s.source)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).slice(0, 3)
}

// ── Sources component ─────────────────────────────────────────────────────────
function SourcesList({ sources }) {
  const [expanded, setExpanded] = useState(false)
  const unique = dedupeSourcesByDoc(sources)
  if (!unique.length) return null

  const SHOW_MAX = 2
  const visible = expanded ? unique : unique.slice(0, SHOW_MAX)
  const hasMore = unique.length > SHOW_MAX

  const EXT_COLORS = {
    pdf:  { bg: 'rgba(224,90,43,0.1)',  text: '#c1440e' },
    txt:  { bg: 'rgba(37,99,235,0.1)',  text: '#1d4ed8' },
    md:   { bg: 'rgba(124,58,237,0.1)', text: '#6d28d9' },
    docx: { bg: 'rgba(29,109,214,0.1)', text: '#1558a8' },
  }

  return (
    <div style={srcStyles.wrapper}>
      <span style={srcStyles.label}>
        <FileText size={11} style={{ flexShrink: 0 }} />
        Sources
      </span>
      <div style={srcStyles.chips}>
        {visible.map((s, i) => {
          const name = getFileName(s.source)
          const ext = name.split('.').pop()?.toLowerCase() || ''
          const ec = EXT_COLORS[ext] ?? { bg: 'rgba(100,100,100,0.1)', text: '#555' }
          return (
            <span key={i} style={srcStyles.chip} title={s.source}>
              <span style={{ ...srcStyles.ext, background: ec.bg, color: ec.text }}>
                {ext.toUpperCase() || 'DOC'}
              </span>
              <span style={srcStyles.chipName}>{name}</span>
            </span>
          )
        })}
        {hasMore && (
          <button onClick={() => setExpanded(e => !e)} style={srcStyles.moreBtn}>
            {expanded
              ? <><ChevronUp size={10} /> less</>
              : <><ChevronDown size={10} /> +{unique.length - SHOW_MAX} more</>}
          </button>
        )}
      </div>
    </div>
  )
}

const srcStyles = {
  wrapper: {
    display: 'flex', alignItems: 'flex-start', gap: '7px',
    marginTop: '10px', flexWrap: 'wrap',
  },
  label: {
    display: 'flex', alignItems: 'center', gap: '4px',
    fontSize: '11px', fontWeight: 600,
    color: 'var(--color-text-secondary, #888)',
    whiteSpace: 'nowrap', marginTop: '4px', flexShrink: 0,
  },
  chips: {
    display: 'flex', flexWrap: 'wrap', gap: '5px', flex: 1, minWidth: 0,
  },
  chip: {
    display: 'inline-flex', alignItems: 'center', gap: '5px',
    background: 'var(--color-background-secondary, rgba(0,0,0,0.04))',
    border: '1px solid var(--color-border-tertiary, rgba(0,0,0,0.08))',
    borderRadius: '6px', padding: '3px 8px 3px 5px',
    maxWidth: '200px', overflow: 'hidden', fontSize: '11px',
    cursor: 'default',
  },
  ext: {
    fontSize: '9px', fontWeight: 700, padding: '1px 4px',
    borderRadius: '3px', flexShrink: 0, letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  chipName: {
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
    color: 'var(--color-text-primary, #333)',
    maxWidth: '140px',
  },
  moreBtn: {
    display: 'inline-flex', alignItems: 'center', gap: '3px',
    background: 'none',
    border: '1px solid var(--color-border-tertiary, rgba(0,0,0,0.1))',
    borderRadius: '6px', padding: '3px 8px', fontSize: '11px',
    color: 'var(--color-text-secondary, #888)', cursor: 'pointer',
  },
}

// ── Confidence + Feedback widget ──────────────────────────────────────────────
function ConfidenceFeedback({ confidence, feedbackRecordId, token, initialVote }) {
  // FIX: initialise vote from the persisted value that came back from the backend
  const [vote, setVote] = useState(initialVote ?? null)
  const [submitted, setSubmitted] = useState(initialVote != null)
  const [loading, setLoading] = useState(false)

  // Keep in sync if the prop changes (e.g. history reload delivers a vote)
  useEffect(() => {
    if (initialVote != null) {
      setVote(initialVote)
      setSubmitted(true)
    }
  }, [initialVote])

  if (!confidence) return null

  const levels = {
    high:   { color: '#16a34a', bg: 'rgba(22,163,74,0.1)',  dot: '#22c55e', text: 'High confidence' },
    medium: { color: '#b45309', bg: 'rgba(245,158,11,0.1)', dot: '#f59e0b', text: 'Medium confidence' },
    low:    { color: '#b91c1c', bg: 'rgba(239,68,68,0.1)',  dot: '#ef4444', text: 'Low confidence' },
  }
  const cfg = levels[confidence.label] ?? { color: '#888', bg: 'rgba(128,128,128,0.1)', dot: '#aaa', text: 'No data' }
  const pct = confidence.score != null ? Math.round(confidence.score * 100) : null

  async function submit(v) {
    if (submitted || loading || !feedbackRecordId) return
    setLoading(true)
    setVote(v)
    try {
      await fetch('http://localhost:8000/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ record_id: feedbackRecordId, vote: v })
      })
      setSubmitted(true)
    } catch (e) {
      console.error('Feedback error:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={cfStyles.row}>
      {/* Confidence pill */}
      <span style={{ ...cfStyles.pill, color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}28` }}>
        <span style={{ ...cfStyles.dot, background: cfg.dot, boxShadow: `0 0 0 3px ${cfg.dot}22` }} />
        {cfg.text}
        {pct != null && (
          <span style={{ ...cfStyles.pct, color: cfg.color, background: `${cfg.color}14` }}>
            {pct}%
          </span>
        )}
      </span>

      <span style={cfStyles.divider} />

      {/* Feedback — lucide SVG icons instead of emoji */}
      {!submitted ? (
        <span style={cfStyles.fbRow}>
          <span style={cfStyles.fbLabel}>Helpful?</span>
          <button
            onClick={() => submit(1)}
            disabled={loading}
            title="Yes, helpful"
            style={{
              ...cfStyles.thumbBtn,
              ...(vote === 1 ? cfStyles.thumbUpActive : {}),
            }}
          >
            <ThumbsUp size={13} strokeWidth={2} />
          </button>
          <button
            onClick={() => submit(-1)}
            disabled={loading}
            title="No, not helpful"
            style={{
              ...cfStyles.thumbBtn,
              ...(vote === -1 ? cfStyles.thumbDownActive : {}),
            }}
          >
            <ThumbsDown size={13} strokeWidth={2} />
          </button>
        </span>
      ) : (
        <span style={cfStyles.thanks}>
          {vote === 1
            ? <><ThumbsUp size={11} style={{ marginRight: 4, verticalAlign: 'middle' }} />Thanks — system learned</>
            : <><ThumbsDown size={11} style={{ marginRight: 4, verticalAlign: 'middle' }} />Noted, will improve</>}
        </span>
      )}
    </div>
  )
}

const cfStyles = {
  row: {
    display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap',
    marginTop: '10px', paddingTop: '10px',
    borderTop: '1px solid var(--color-border-tertiary, rgba(0,0,0,0.07))',
  },
  pill: {
    display: 'inline-flex', alignItems: 'center', gap: '6px',
    fontSize: '11px', fontWeight: 600, letterSpacing: '0.01em',
    padding: '4px 9px 4px 7px', borderRadius: '999px',
    whiteSpace: 'nowrap', userSelect: 'none',
  },
  dot: {
    width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
  },
  pct: {
    fontWeight: 500, fontSize: '10px',
    padding: '1px 5px', borderRadius: '4px',
  },
  divider: {
    width: '1px', height: '14px', flexShrink: 0,
    background: 'var(--color-border-tertiary, rgba(0,0,0,0.1))',
  },
  fbRow: {
    display: 'flex', alignItems: 'center', gap: '5px',
  },
  fbLabel: {
    fontSize: '11px', color: 'var(--color-text-secondary, #888)',
  },
  thumbBtn: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    width: '28px', height: '24px',
    background: 'var(--color-background-secondary, rgba(0,0,0,0.04))',
    border: '1px solid var(--color-border-tertiary, rgba(0,0,0,0.1))',
    borderRadius: '6px', cursor: 'pointer',
    color: 'var(--color-text-secondary, #666)',
    transition: 'all 0.12s', padding: 0,
  },
  thumbUpActive: {
    background: 'rgba(22,163,74,0.12)',
    border: '1px solid rgba(22,163,74,0.35)',
    color: '#16a34a',
    transform: 'scale(1.1)',
  },
  thumbDownActive: {
    background: 'rgba(239,68,68,0.12)',
    border: '1px solid rgba(239,68,68,0.35)',
    color: '#dc2626',
    transform: 'scale(1.1)',
  },
  thanks: {
    display: 'inline-flex', alignItems: 'center',
    fontSize: '11px', color: 'var(--color-text-secondary, #888)',
    fontStyle: 'italic',
  },
}

// ─────────────────────────────────────────────────────────────────────────────

function ChatPage({ sessionId: propSessionId, onSessionChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(propSessionId)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // FIX: persist selectedDb in localStorage so it survives reloads
  const [selectedDb, setSelectedDb] = useState(
    () => localStorage.getItem('selectedDb') || 'local'
  )

  const [editingIndex, setEditingIndex] = useState(null)
  const [editingText, setEditingText] = useState('')
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)

  const messagesEndRef = useRef(null)
  const previousSessionRef = useRef(null)
  const recognitionRef = useRef(null)
  const token = localStorage.getItem('token')

  // Persist selectedDb whenever it changes
  const handleDbChange = (db) => {
    setSelectedDb(db)
    localStorage.setItem('selectedDb', db)
  }

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  useEffect(() => { scrollToBottom() }, [messages])

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    setSpeechSupported(true)
    const r = new SR()
    r.continuous = false; r.interimResults = false; r.lang = 'en-US'
    r.onstart = () => setIsListening(true)
    r.onresult = (e) => {
      let t = ''
      for (let i = 0; i < e.results.length; i++)
        if (e.results[i].isFinal) t += e.results[i][0].transcript + ' '
      if (t.trim()) setInput(p => p + t)
    }
    r.onerror = (e) => { setIsListening(false); if (e.error === 'not-allowed') alert('Microphone access denied.') }
    r.onend = () => setIsListening(false)
    recognitionRef.current = r
    return () => r.stop()
  }, [])

  const toggleVoiceInput = () => {
    if (!speechSupported) { alert('Speech recognition not supported. Use Chrome/Edge/Safari.'); return }
    isListening ? recognitionRef.current.stop() : recognitionRef.current.start()
  }

  // Sync session from App-level prop
  useEffect(() => {
    if (propSessionId !== sessionId) {
      setSessionId(propSessionId)
      setMessages([])
      setEditingIndex(null)
      setEditingText('')
    }
  }, [propSessionId])

  useEffect(() => {
    const check = () => {
      const saved = localStorage.getItem('lastSessionId')
      if (saved !== previousSessionRef.current) {
        previousSessionRef.current = saved
        setSessionId(saved); setMessages([])
        setEditingIndex(null); setEditingText('')
      }
    }
    check()
    const iv = setInterval(check, 500)
    return () => clearInterval(iv)
  }, [])

  // FIX: load history including confidence + feedback from backend
  useEffect(() => {
    if (!sessionId) { setMessages([]); return }
    setLoadingHistory(true)
    fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/messages`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : [])
      .then(data => setMessages(data.map(m => ({
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        responseTime: m.response_time_ms,
        // FIX: use db_scope from backend — no hardcoded 'local' fallback
        // The backend must store and return this. If it truly isn't stored yet,
        // fall back to the current selectedDb (not always 'local').
        dbScope: m.db_scope || selectedDb,
        // FIX: these now come from the backend (see backend changes below)
        confidence: m.confidence || null,
        feedbackRecordId: m.feedback_record_id || null,
        // FIX: restore the persisted vote so the button shows correctly after reload
        persistedVote: m.feedback_vote ?? null,
      }))))
      .catch(e => console.error('History load failed:', e))
      .finally(() => setLoadingHistory(false))
  }, [sessionId])

  const sendMessage = async () => {
    if (!input.trim()) return
    if (isListening) recognitionRef.current.stop()
    const currentDb = selectedDb
    const userMessage = { role: 'user', content: input, dbScope: currentDb }
    setMessages(p => [...p, userMessage])
    setInput('')
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: userMessage.content, session_id: sessionId, use_rag: true, db_scope: currentDb })
      })
      const data = await res.json()
      if (!sessionId) {
        setSessionId(data.session_id)
        localStorage.setItem('lastSessionId', data.session_id)
        previousSessionRef.current = data.session_id
        onSessionChange?.(data.session_id)
        window.dispatchEvent(new CustomEvent('newChatSession'))
      }
      setMessages(p => [...p, {
        role: 'assistant', content: data.answer,
        sources: data.sources || [], responseTime: data.response_time_ms,
        dbScope: currentDb,
        confidence: data.confidence || null,
        feedbackRecordId: data.feedback_record_id || null,
        persistedVote: null,
      }])
    } catch (e) {
      setMessages(p => [...p, {
        role: 'assistant', content: 'Sorry, there was an error. Please try again.',
        dbScope: currentDb, confidence: null, feedbackRecordId: null, persistedVote: null,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const saveEditedMessage = async () => {
    if (!editingText.trim()) return
    const newQuery = editingText
    const editIdx = editingIndex
    const dbScopeForEdit = messages[editIdx].dbScope || selectedDb
    setIsRegenerating(true)
    const updated = [...messages]
    updated[editIdx].content = newQuery
    if (updated[editIdx + 1]?.role === 'assistant') updated.splice(editIdx + 1, 1)
    setMessages(updated)
    setEditingIndex(null); setEditingText('')
    try {
      const res = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: newQuery, session_id: sessionId, use_rag: true, db_scope: dbScopeForEdit })
      })
      const data = await res.json()
      setMessages(p => [...p, {
        role: 'assistant', content: data.answer, sources: data.sources || [],
        responseTime: data.response_time_ms, dbScope: dbScopeForEdit,
        confidence: data.confidence || null, feedbackRecordId: data.feedback_record_id || null,
        persistedVote: null,
      }])
    } catch (e) {
      setMessages(p => [...p, {
        role: 'assistant', content: 'Error regenerating. Please try again.',
        dbScope: dbScopeForEdit, confidence: null, feedbackRecordId: null, persistedVote: null,
      }])
    } finally {
      setIsRegenerating(false)
    }
  }

  const startNewChat = () => {
    setMessages([]); setSessionId(null)
    localStorage.removeItem('lastSessionId')
    previousSessionRef.current = null
    onSessionChange?.(null)
    window.dispatchEvent(new CustomEvent('newChatSession'))
  }

  const exportChatAsMarkdown = () => {
    if (!messages.length) { alert('No messages to export!'); return }
    let md = `# Chat Export\n\n**Exported:** ${new Date().toLocaleString()}\n\n---\n\n`
    messages.forEach(msg => {
      md += `## ${msg.role === 'user' ? '👤 User' : '🤖 Assistant'}\n\n${msg.content}\n\n`
      if (msg.sources?.length) md += `**Sources:** ${dedupeSourcesByDoc(msg.sources).map(s => getFileName(s.source)).join(', ')}\n\n`
      if (msg.responseTime) md += `*${msg.responseTime}ms*\n\n`
      md += `---\n\n`
    })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([md], { type: 'text/markdown' }))
    a.download = `chat-${new Date().toISOString().split('T')[0]}.md`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div>
          <h2>Code Assistant Chat</h2>
          <p>Ask questions about your codebase</p>
        </div>
        <div className="chat-header-buttons">
          <button onClick={exportChatAsMarkdown} className="export-button" disabled={!messages.length}>
            <Download size={16} /> Export
          </button>
          <button onClick={startNewChat} className="new-chat-button">+ New Chat</button>
        </div>
      </div>

      <div className="messages-container">
        {loadingHistory ? (
          <div className="empty-state">
            <div className="typing-indicator"><span/><span/><span/></div>
            <p>Loading chat history...</p>
          </div>
        ) : !messages.length ? (
          <div className="empty-state">
            <Code size={64} />
            <h3>Start a conversation</h3>
            <p>Ask me anything about your company's code or documentation</p>
            <p style={{ fontSize: '14px', color: '#888', marginTop: '12px' }}>
              Choose between your local documents or shared team documents below
            </p>
          </div>
        ) : null}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.dbScope && (
              <div className={`db-badge ${msg.dbScope}`}>
                {msg.dbScope === 'shared' ? <><Globe size={12}/> Shared</> : <><User size={12}/> Local</>}
              </div>
            )}

            <div className="message-content">
              {editingIndex === idx && msg.role === 'user' ? (
                <>
                  <textarea className="edit-box" value={editingText}
                    onChange={e => setEditingText(e.target.value)} autoFocus />
                  <div className="edit-buttons">
                    <button onClick={saveEditedMessage} className="save-btn"
                      disabled={isRegenerating || !editingText.trim()}>
                      {isRegenerating ? <><RefreshCw size={16} className="spinning"/> Regenerating...</> : <><Check size={16}/> Submit</>}
                    </button>
                    <button onClick={() => { setEditingIndex(null); setEditingText('') }}
                      className="cancel-btn" disabled={isRegenerating}>
                      <X size={16}/> Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <ReactMarkdown components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : <code className={className} {...props}>{children}</code>
                    }
                  }}>{msg.content}</ReactMarkdown>

                  {msg.role === 'user' && (
                    <button className="inline-edit-btn"
                      onClick={() => { setEditingIndex(idx); setEditingText(msg.content) }}>
                      Edit
                    </button>
                  )}

                  {msg.role === 'assistant' && <SourcesList sources={msg.sources} />}
                  {msg.role === 'assistant' && (
                    <ConfidenceFeedback
                      confidence={msg.confidence}
                      feedbackRecordId={msg.feedbackRecordId}
                      token={token}
                      initialVote={msg.persistedVote}
                    />
                  )}
                </>
              )}

              {msg.responseTime && (
                <div className="response-time">Response time: {msg.responseTime}ms</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="typing-indicator"><span/><span/><span/></div>
          </div>
        )}
        {isRegenerating && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator"><span/><span/><span/></div>
              <p style={{ marginTop: '8px', fontSize: '14px', color: '#94a3b8' }}>Regenerating...</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <div className="db-selector">
          {/* FIX: use handleDbChange instead of setSelectedDb directly */}
          <button className={`db-option ${selectedDb === 'local' ? 'active' : ''}`}
            onClick={() => handleDbChange('local')} title="Search your personal documents">
            <User size={16}/> My Documents
          </button>
          <button className={`db-option ${selectedDb === 'shared' ? 'active' : ''}`}
            onClick={() => handleDbChange('shared')} title="Search shared team documents">
            <Globe size={16}/> Shared Documents
          </button>
        </div>

        <textarea value={input} onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress} rows={3} disabled={loading}
          className={isListening ? 'listening' : ''}
          placeholder={isListening ? 'Listening… speak now!'
            : `Ask about ${selectedDb === 'shared' ? 'shared team' : 'your personal'} documents…`}
        />

        {speechSupported && (
          <button onClick={toggleVoiceInput} disabled={loading}
            className={`voice-button ${isListening ? 'listening' : ''}`}
            title={isListening ? 'Stop' : 'Voice input'}>
            {isListening ? <MicOff size={20}/> : <Mic size={20}/>}
          </button>
        )}
        <button onClick={sendMessage} disabled={loading || !input.trim()} className="send-button">
          <Send size={20}/>
        </button>
      </div>
    </div>
  )
}

export default ChatPage