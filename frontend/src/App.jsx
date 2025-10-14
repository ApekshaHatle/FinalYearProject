import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import ChatPage from './components/ChatPage'
import DocumentsPage from './components/DocumentsPage'
import AdminPage from './components/AdminPage'
import LoginPage from './components/LoginPage'
import { MessageSquare, FileText, BarChart3, LogOut } from 'lucide-react'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('token')
    if (token) {
      setIsAuthenticated(true)
      // Fetch user info
      fetchUserInfo(token)
    }
  }, [])

  const fetchUserInfo = async (token) => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setUser(data)
      }
    } catch (error) {
      console.error('Error fetching user:', error)
    }
  }

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token)
    setIsAuthenticated(true)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
    setUser(null)
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <BrowserRouter>
      <div className="app">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <h1>Code Assistant</h1>
            {user && <p className="user-name">{user.username}</p>}
          </div>

          <nav className="sidebar-nav">
            <Link to="/" className="nav-item">
              <MessageSquare size={20} />
              <span>Chat</span>
            </Link>
            <Link to="/documents" className="nav-item">
              <FileText size={20} />
              <span>Documents</span>
            </Link>
            <Link to="/admin" className="nav-item">
              <BarChart3 size={20} />
              <span>Admin</span>
            </Link>
          </nav>

          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App