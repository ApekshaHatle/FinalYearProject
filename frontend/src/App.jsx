import './App.css'
import {BrowserRouter as Router, Routes, Route} from "react-router-dom"
import Login from "./components/Login"
import Dashboard from "./components/Dashboard"

function App() {
  return (
    <Router>
      <div className="app-container">
        <header>
          <h1 className="title">Company Assistant</h1>
        </header>
        <main>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/" element={<Login />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
