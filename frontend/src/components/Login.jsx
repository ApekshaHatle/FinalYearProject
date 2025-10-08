import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css'; // Assuming we create a separate CSS file for login styles

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // For now, just navigate to dashboard on submit
    navigate('/dashboard');
  };

  return (
    <div className="login-container wd-100%">
      <div className="login-card">
        <h2 className="login-title">Sign in to Your Account</h2>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label htmlFor="email">Email or Username</label>
            <input
              type="text"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="login-input"
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="login-input"
            />
          </div>
          <button type="submit" className="login-button">Sign in</button>
        </form>
        <div className="login-links">
          <a href="#" className="login-link">Forgot password?</a>
          <span className="separator">|</span>
          <a href="#" className="login-link">Create an account</a>
        </div>
      </div>
    </div>
  );
};

export default Login;
