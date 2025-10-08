import React from 'react';
import './Dashboard.css';

const Dashboard = () => {
  return (
    <div className="dashboard-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Company Assistant</h2>
        </div>
        <nav className="sidebar-nav">
          <ul>
            <li><a href="#" className="nav-link">New Query</a></li>
            <li><a href="#" className="nav-link">History</a></li>
            <li><a href="#" className="nav-link">Settings</a></li>
            <li><a href="#" className="nav-link">Help</a></li>
          </ul>
        </nav>
      </aside>
      <main className="main-content">
        <h1>Welcome to the Dashboard</h1>
        <p>This is your main dashboard page for the company assistant.</p>
        {/* Add more dashboard content here */}
      </main>
    </div>
  );
};

export default Dashboard;
