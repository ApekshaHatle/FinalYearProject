import { useNavigate } from 'react-router-dom'
import { 
  MessageSquare, 
  FileText, 
  Settings, 
  ArrowRight,
  Sparkles,
  Database,
  Brain,
  Shield,
  Zap,
  BookOpen
} from 'lucide-react'

function DashboardPage({ user }) {
  const navigate = useNavigate()

  const features = [
    {
      icon: <Brain className="feature-icon" />,
      title: "AI-Powered Conversations",
      description: "Chat with an intelligent assistant powered by Code Llama, trained to understand context and provide accurate responses.",
      color: "#D97706"
    },
    {
      icon: <Database className="feature-icon" />,
      title: "Document Intelligence",
      description: "Upload and query your documents using advanced RAG technology for context-aware answers from your knowledge base.",
      color: "#EA580C"
    },
    {
      icon: <Shield className="feature-icon" />,
      title: "Secure & Private",
      description: "Your data stays private with local processing through Ollama. Full control over your information and conversations.",
      color: "#DC2626"
    },
    {
      icon: <Sparkles className="feature-icon" />,
      title: "Real-time Streaming",
      description: "Experience instant responses with token-by-token streaming for a smooth, interactive conversation flow.",
      color: "#F59E0B"
    }
  ]

  const navigationCards = [
    {
      title: "Start Chatting",
      description: "Begin a new conversation with your AI assistant and get instant answers",
      icon: <MessageSquare size={28} />,
      path: "/chat",
      gradient: "linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
      badge: "Popular"
    },
    {
      title: "Manage Documents",
      description: "Upload, organize, and search through your document library with AI",
      icon: <FileText size={28} />,
      path: "/documents",
      gradient: "linear-gradient(135deg, #D97706 0%, #B45309 100%)",
      badge: "Smart Search"
    },
    {
      title: "Admin Console",
      description: "Configure settings, monitor usage, and manage your workspace",
      icon: <Settings size={28} />,
      path: "/admin",
      gradient: "linear-gradient(135deg, #EA580C 0%, #DC2626 100%)",
      badge: "Control"
    }
  ]

  return (
    <div className="dashboard-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <Zap size={14} />
            <span>Powered by Ollama & Code Llama</span>
          </div>
          
          <h1 className="hero-title">
            Welcome back, <span className="gradient-text">{user?.username || 'User'}</span>
          </h1>
          
          <p className="hero-subtitle">
            Your intelligent RAG assistant is ready to help you explore documents, 
            generate insights, and answer questions with AI-powered precision.
          </p>

          <div className="hero-actions">
            <button 
              className="btn-primary"
              onClick={() => navigate('/chat')}
            >
              <MessageSquare size={20} />
              Start New Chat
              <ArrowRight size={18} />
            </button>
            <button 
              className="btn-secondary"
              onClick={() => navigate('/documents')}
            >
              <BookOpen size={20} />
              Browse Documents
            </button>
          </div>

          <div className="quick-stats">
            <div className="stat-item">
              <div className="stat-value">∞</div>
              <div className="stat-label">Conversations</div>
            </div>
            <div className="stat-divider"></div>
            <div className="stat-item">
              <div className="stat-value">100%</div>
              <div className="stat-label">Private</div>
            </div>
            <div className="stat-divider"></div>
            <div className="stat-item">
              <div className="stat-value">Fast</div>
              <div className="stat-label">Responses</div>
            </div>
          </div>
        </div>

        <div className="hero-visual">
          <div className="floating-orb orb-1"></div>
          <div className="floating-orb orb-2"></div>
          <div className="floating-orb orb-3"></div>
        </div>
      </section>

      {/* Navigation Cards */}
      <section className="navigation-section">
        <h2 className="section-title">Quick Access</h2>
        <div className="nav-cards-grid">
          {navigationCards.map((card, index) => (
            <div 
              key={index}
              className="nav-card"
              onClick={() => navigate(card.path)}
            >
              <div className="nav-card-badge">{card.badge}</div>
              <div 
                className="nav-card-icon"
                style={{ background: card.gradient }}
              >
                {card.icon}
              </div>
              <div className="nav-card-content">
                <h3>{card.title}</h3>
                <p>{card.description}</p>
              </div>
              <div className="nav-card-arrow">
                <ArrowRight size={20} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="features-section">
        <h2 className="section-title">Powerful Features</h2>
        <p className="section-subtitle">Everything you need for intelligent document interaction</p>
        
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div 
                className="feature-icon-wrapper"
                style={{ backgroundColor: `${feature.color}15`, color: feature.color }}
              >
                {feature.icon}
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* About Section */}
      <section className="about-section">
        <div className="about-container">
          <div className="about-content">
            <h2>About This Platform</h2>
            <p className="about-intro">
              This platform combines Retrieval-Augmented Generation (RAG) with 
              Code Llama to deliver contextually aware responses based on your 
              document library. It's designed to make your documents searchable, 
              queryable, and actionable.
            </p>
            
            <div className="about-features-list">
              <div className="about-feature-item">
                <div className="check-mark">✓</div>
                <div>
                  <h4>Local AI Processing</h4>
                  <p>Run entirely on your machine with Ollama for complete privacy</p>
                </div>
              </div>
              
              <div className="about-feature-item">
                <div className="check-mark">✓</div>
                <div>
                  <h4>Vector-Based Search</h4>
                  <p>Lightning-fast semantic search powered by ChromaDB embeddings</p>
                </div>
              </div>
              
              <div className="about-feature-item">
                <div className="check-mark">✓</div>
                <div>
                  <h4>Context-Aware Responses</h4>
                  <p>Get accurate answers grounded in your uploaded documents</p>
                </div>
              </div>
              
              <div className="about-feature-item">
                <div className="check-mark">✓</div>
                <div>
                  <h4>Session Management</h4>
                  <p>Organize conversations with persistent chat history</p>
                </div>
              </div>
            </div>
          </div>

          <div className="about-tech">
            <h3>Built With Modern Technology</h3>
            <div className="tech-stack">
              <div className="tech-category">
                <h4>Frontend</h4>
                <div className="tech-tags">
                  <span className="tech-tag">React</span>
                  <span className="tech-tag">React Router</span>
                </div>
              </div>
              
              <div className="tech-category">
                <h4>Backend</h4>
                <div className="tech-tags">
                  <span className="tech-tag">FastAPI</span>
                  <span className="tech-tag">Python</span>
                </div>
              </div>
              
              <div className="tech-category">
                <h4>AI & ML</h4>
                <div className="tech-tags">
                  <span className="tech-tag">Ollama</span>
                  <span className="tech-tag">Code Llama</span>
                  <span className="tech-tag">ChromaDB</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2>Ready to get started?</h2>
          <p>Start chatting with your AI assistant or upload your first document</p>
          <div className="cta-buttons">
            <button 
              className="btn-primary"
              onClick={() => navigate('/chat')}
            >
              <MessageSquare size={20} />
              Start Chatting
            </button>
            <button 
              className="btn-secondary"
              onClick={() => navigate('/documents')}
            >
              <FileText size={20} />
              Upload Documents
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default DashboardPage