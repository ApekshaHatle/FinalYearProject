import { useState } from 'react'
import { Code } from 'lucide-react'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google'

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

  // NEW: Handle Google Sign-In Success
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setLoading(true)
      setError('')

      // Send Google credential to backend
      const response = await fetch('http://localhost:8000/api/auth/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          credential: credentialResponse.credential
        })
      })

      const data = await response.json()

      if (response.ok) {
        // Login successful
        onLogin(data.access_token, data.user)
      } else {
        setError(data.detail || 'Google authentication failed')
      }
    } catch (err) {
      setError('Network error during Google login')
    } finally {
      setLoading(false)
    }
  }

  // NEW: Handle Google Sign-In Error
  const handleGoogleError = () => {
    console.log('Google Login Failed')
    setError('Google login failed. Please try again.')
  }

  return (
    <GoogleOAuthProvider clientId="407552316232-7lrqod27isrqmp18nnvcce38r68mgcob.apps.googleusercontent.com">
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
            <div className="divider">
              <span>OR</span>
            </div>
          {/* NEW: Google Sign-In Section */}
          <div className="google-signin-container">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap={false}
              text={isRegister ? "signup_with" : "signin_with"}
              size="large"
              theme="filled_blue"
              shape="rectangular"
              width="360"
            />
            
            
          </div>
        </div>
      </div>
    </GoogleOAuthProvider>
  )
}

export default LoginPage