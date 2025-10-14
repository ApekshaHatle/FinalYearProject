import { useState, useEffect } from 'react'
import { Users, FileText, MessageSquare, Activity } from 'lucide-react'

function AdminPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/admin/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      const data = await response.json()
      setStats(data)
    } catch (error) {
      console.error('Error fetching stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading statistics...</div>
  }

  if (!stats) {
    return <div className="error">Failed to load statistics</div>
  }

  return (
    <div className="admin-page">
      <div className="page-header">
        <h2>Admin Dashboard</h2>
        <p>System statistics and monitoring</p>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon users">
            <Users size={32} />
          </div>
          <div className="stat-content">
            <h3>Users</h3>
            <p className="stat-number">{stats.users.total}</p>
            <p className="stat-detail">{stats.users.active} active</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon documents">
            <FileText size={32} />
          </div>
          <div className="stat-content">
            <h3>Documents</h3>
            <p className="stat-number">{stats.documents.total}</p>
            <p className="stat-detail">{stats.documents.completed} completed</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon messages">
            <MessageSquare size={32} />
          </div>
          <div className="stat-content">
            <h3>Chat Sessions</h3>
            <p className="stat-number">{stats.chat.total_sessions}</p>
            <p className="stat-detail">
              {stats.chat.total_messages} total messages
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon activity">
            <Activity size={32} />
          </div>
          <div className="stat-content">
            <h3>Avg Messages</h3>
            <p className="stat-number">{stats.chat.avg_messages_per_session}</p>
            <p className="stat-detail">per session</p>
          </div>
        </div>
      </div>

      {/* Services Status */}
      <div className="services-section">
        <h3>Services Status</h3>
        <div className="services-grid">
          <div className={`service-card ${stats.services.ollama ? 'online' : 'offline'}`}>
            <div className="service-status"></div>
            <div>
              <h4>Ollama (Code Llama)</h4>
              <p>{stats.services.ollama ? 'Connected' : 'Disconnected'}</p>
            </div>
          </div>

          <div className={`service-card ${stats.services.rag ? 'online' : 'offline'}`}>
            <div className="service-status"></div>
            <div>
              <h4>RAG Service</h4>
              <p>{stats.services.rag ? 'Initialized' : 'Not Ready'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* RAG Statistics */}
      {stats.rag && stats.rag.total_chunks !== undefined && (
        <div className="rag-section">
          <h3>Vector Database</h3>
          <div className="rag-stats">
            <div className="rag-stat">
              <strong>Total Chunks:</strong>
              <span>{stats.rag.total_chunks}</span>
            </div>
            <div className="rag-stat">
              <strong>Storage:</strong>
              <span>{stats.rag.persist_directory}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminPage