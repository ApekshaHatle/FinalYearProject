import { useState } from 'react'
import { Code } from 'lucide-react'

function LoginPage({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    full_name: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        // Register
        const registerResponse = await fetch('http://localhost:8000/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        })

        if (!registerResponse.ok) {
          const errorData = await registerResponse.json()
          throw new Error(errorData.detail || 'Registration failed')
        }
      }

      // Login
      const loginFormData = new FormData()
      loginFormData.append('username', formData.username)
      loginFormData.append('password', formData.password)

      const loginResponse = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        body: loginFormData
      })

      if (!loginResponse.ok) {
        throw new Error('Invalid credentials')
      }

      const data = await loginResponse.json()
      
      // Fetch user info
      const userResponse = await fetch('http://localhost:8000/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      })

      const userData = await userResponse.json()
      onLogin(data.access_token, userData)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <Code size={48} />
          <h1>Code Assistant</h1>
          <p>Enterprise AI-Powered Development Tool</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {isRegister && (
            <>
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
              <input
                type="text"
                placeholder="Full Name"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
              />
            </>
          )}

          <input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({...formData, username: e.target.value})}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
          />

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Please wait...' : (isRegister ? 'Register' : 'Login')}
          </button>

          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister)
              setError('')
            }}
            className="toggle-btn"
          >
            {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage