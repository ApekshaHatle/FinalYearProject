import { useState, useEffect, useRef } from 'react'
import { Send, Code, FileText, Check, X, RefreshCw, Download} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Editing states
  const [editingIndex, setEditingIndex] = useState(null)
  const [editingText, setEditingText] = useState("")
  const [isRegenerating, setIsRegenerating] = useState(false)

  const messagesEndRef = useRef(null)
  const previousSessionRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Monitor sessionId changes from localStorage (when sidebar switches chats)
  useEffect(() => {
    const checkSessionChange = () => {
      const savedSessionId = localStorage.getItem('lastSessionId')
      
      // If session changed from outside (sidebar click)
      if (savedSessionId !== previousSessionRef.current) {
        previousSessionRef.current = savedSessionId
        setSessionId(savedSessionId)
        setMessages([])
        setEditingIndex(null)
        setEditingText("")
      }
    }

    // Check immediately
    checkSessionChange()

    // Also check periodically for changes
    const interval = setInterval(checkSessionChange, 500)

    return () => clearInterval(interval)
  }, [])

  // LOAD CHAT HISTORY when session changes
  useEffect(() => {
    const loadChatHistory = async () => {
      if (!sessionId) {
        setMessages([])
        return
      }

      setLoadingHistory(true)
      try {
        const response = await fetch(
          `http://localhost:8000/api/chat/sessions/${sessionId}/messages`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        )

        if (response.ok) {
          const data = await response.json()
          const loadedMessages = data.map(msg => ({
            role: msg.role,
            content: msg.content,
            sources: msg.sources || [],
            responseTime: msg.response_time_ms
          }))
          setMessages(loadedMessages)
        }
      } catch (error) {
        console.error('❌ Failed to load chat history:', error)
      } finally {
        setLoadingHistory(false)
      }
    }

    loadChatHistory()
  }, [sessionId])

  // SEND NEW MESSAGE
  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          query: input,
          session_id: sessionId,
          use_rag: true
        })
      })

      const data = await response.json()
      
      // If this is a new session, save it
      if (!sessionId) {
        setSessionId(data.session_id)
        localStorage.setItem('lastSessionId', data.session_id)
        previousSessionRef.current = data.session_id
        
        // Trigger sidebar refresh by dispatching event
        window.dispatchEvent(new CustomEvent('newChatSession'))
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        responseTime: data.response_time_ms
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // EDIT MESSAGE — Re-run updated user query with NEW edited text
  const saveEditedMessage = async () => {
    if (!editingText.trim()) return

    // Store the edited text before we clear state
    const newQuery = editingText
    const editIdx = editingIndex

    setIsRegenerating(true)
    
    // Update the user message with edited text
    const updated = [...messages]
    updated[editIdx].content = newQuery  // Save edited message

    // Remove old assistant response to prepare for new one
    if (updated[editIdx + 1] && updated[editIdx + 1].role === 'assistant') {
      updated.splice(editIdx + 1, 1)
    }
    
    setMessages(updated)
    setEditingIndex(null)
    setEditingText("")

    try {
      // Re-run with the NEW EDITED query text
      const response = await fetch('http://localhost:8000/api/chat/query', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          query: newQuery,  // Using the edited text here!
          session_id: sessionId,
          use_rag: true
        })
      })

      const data = await response.json()

      // Add NEW assistant response based on edited query
      const newAssistantMessage = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        responseTime: data.response_time_ms
      }

      setMessages(prev => [...prev, newAssistantMessage])
    } catch (error) {
      console.error('Error regenerating response:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error regenerating the response. Please try again.'
      }])
    } finally {
      setIsRegenerating(false)
    }
  }

  const startNewChat = () => {
    setMessages([])
    setSessionId(null)
    localStorage.removeItem('lastSessionId')
    previousSessionRef.current = null
    
    // Trigger sidebar refresh
    window.dispatchEvent(new CustomEvent('newChatSession'))
  }

  // Function to export chat as Markdown
const exportChatAsMarkdown = () => {
  if (messages.length === 0) {
    alert('No messages to export!')
    return
  }

  // Create markdown content
  let markdown = `# Chat Export\n\n`
  markdown += `**Exported on:** ${new Date().toLocaleString()}\n\n`
  markdown += `**Total Messages:** ${messages.length}\n\n`
  markdown += `---\n\n`

  // Add each message
  messages.forEach((msg, index) => {
    const role = msg.role === 'user' ? '👤 User' : '🤖 Assistant'
    markdown += `## ${role}\n\n`
    markdown += `${msg.content}\n\n`
    
    // Add sources if available
    if (msg.sources && msg.sources.length > 0) {
      markdown += `**Sources:**\n`
      msg.sources.forEach(source => {
        markdown += `- ${source.source}\n`
      })
      markdown += `\n`
    }
    
    // Add response time if available
    if (msg.responseTime) {
      markdown += `*Response time: ${msg.responseTime}ms*\n\n`
    }
    
    markdown += `---\n\n`
  })

  // Create blob and download
  const blob = new Blob([markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chat-export-${new Date().toISOString().split('T')[0]}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  console.log('✅ Chat exported as Markdown')
}
  return (
    <div className="chat-page">
      <div className="chat-header">
        <div>
          <h2>Code Assistant Chat</h2>
          <p>Ask questions about your codebase</p>
        </div>
        <div className="chat-header-buttons">
          <button 
            onClick={exportChatAsMarkdown} 
            className="export-button" 
            disabled={messages.length === 0}
          >
            <Download size={16} />
            Export
          </button>
          <button onClick={startNewChat} className="new-chat-button">
            + New Chat
          </button>
        </div>
      </div>

      <div className="messages-container">
        {loadingHistory ? (
          <div className="empty-state">
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
            <p>Loading chat history...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="empty-state">
            <Code size={64} />
            <h3>Start a conversation</h3>
            <p>Ask me anything about your company's code or documentation</p>
          </div>
        ) : null}

        {/* RENDER MESSAGES */}
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">

              {/* If user is EDITING this message */}
              {editingIndex === idx && msg.role === "user" ? (
                <>
                  <textarea
                    className="edit-box"
                    value={editingText}
                    onChange={(e) => setEditingText(e.target.value)}
                    autoFocus
                  />

                  <div className="edit-buttons">
                    <button 
                      onClick={saveEditedMessage} 
                      className="save-btn"
                      disabled={isRegenerating || !editingText.trim()}
                    >
                      {isRegenerating ? (
                        <>
                          <RefreshCw size={16} className="spinning" />
                          Regenerating...
                        </>
                      ) : (
                        <>
                          <Check size={16} />
                          Submit
                        </>
                      )}
                    </button>
                    <button 
                      onClick={() => { setEditingIndex(null); setEditingText("") }}
                      className="cancel-btn"
                      disabled={isRegenerating}
                    >
                      <X size={16} />
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* Normal Display */}
                  <ReactMarkdown
                    components={{
                      code({node, inline, className, children, ...props}) {
                        const match = /language-(\w+)/.exec(className || '')
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>

                  {/* EDIT BUTTON FOR USER MESSAGES */}
                  {msg.role === "user" && (
                    <button
                      className="inline-edit-btn"
                      onClick={() => {
                        setEditingIndex(idx)
                        setEditingText(msg.content)
                      }}
                    >
                      Edit
                    </button>
                  )}
                </>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources">
                  <FileText size={16} />
                  <span>Sources:</span>
                  {msg.sources.map((source, i) => (
                    <span key={i} className="source-tag">
                      {source.source}
                    </span>
                  ))}
                </div>
              )}

              {msg.responseTime && (
                <div className="response-time">
                  Response time: {msg.responseTime}ms
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        {isRegenerating && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
              <p style={{ marginTop: '8px', fontSize: '14px', color: '#94a3b8' }}>
                Regenerating response...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* INPUT AREA */}
      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question..."
          rows={3}
          disabled={loading}
        />
        <button 
          onClick={sendMessage} 
          disabled={loading || !input.trim()}
          className="send-button"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}

export default ChatPage