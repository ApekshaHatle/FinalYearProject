import { useState, useEffect, useRef } from 'react'
import { Send, Code, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

function ChatPage({ sessionId: propSessionId, onSessionChange }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(propSessionId)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  
useEffect(() => {
  const loadChatHistory = async () => {
    if (!sessionId) return 
    
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
        
        // Transform backend messages to frontend format
        const loadedMessages = data.map(msg => ({
          role: msg.role,
          content: msg.content,
          sources: msg.sources || [],
          responseTime: msg.response_time_ms
        }))
        
        setMessages(loadedMessages)
        console.log('✅ Loaded chat history:', loadedMessages.length, 'messages')
      }
    } catch (error) {
      console.error('❌ Failed to load chat history:', error)
    } finally {
      setLoadingHistory(false)
    }
  }

  loadChatHistory()
}, [sessionId])



useEffect(() => {
  const restoreLastSession = async () => {
    
    const savedSessionId = localStorage.getItem('lastSessionId')
    
    if (savedSessionId) {
      console.log('🔄 Restoring last session:', savedSessionId)
      setSessionId(savedSessionId)
    } else {
      
      try {
        const response = await fetch('http://localhost:8000/api/chat/sessions', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const sessions = await response.json()
          if (sessions.length > 0) {
            
            const mostRecentSession = sessions[0]
            console.log('🔄 Loading most recent session:', mostRecentSession.id)
            setSessionId(mostRecentSession.id)
            localStorage.setItem('lastSessionId', mostRecentSession.id)
          }
        }
      } catch (error) {
        console.error('Failed to load recent sessions:', error)
      }
    }
  }

  restoreLastSession()
}, [])


// Update when session changes from sidebar
useEffect(() => {
  if (propSessionId !== sessionId) {
    setSessionId(propSessionId)
  }
}, [propSessionId])

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
      
      if (!sessionId) {
        setSessionId(data.session_id)
        onSessionChange(data.session_id)
        localStorage.setItem('lastSessionId', data.session_id)
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

  
const startNewChat = () => {
  setMessages([])
  setSessionId(null)
  onSessionChange(null)
  localStorage.removeItem('lastSessionId')
  console.log('🆕 Started new chat')
}
  return (
    <div className="chat-page">
      <div className="chat-header">
        <h2>Code Assistant Chat</h2>
        <p>Ask questions about your codebase</p>
        <button onClick={startNewChat} className="new-chat-button">
          + New Chat
        </button>
      </div>

      <div className="messages-container">
        {loadingHistory ? (
          <div className="empty-state">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
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

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
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
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

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