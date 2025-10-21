import React, { useState, useEffect } from 'react';
import './GmailClient.css';

const API_BASE_URL = 'http://localhost:8000';

// API Client class
class GmailClientAPI {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  // Health & Status
  async getHealth() {
    return this.request('/health');
  }

  async getStatus() {
    return this.request('/api/status');
  }

  // Initialization
  async initialize() {
    return this.request('/api/init', { method: 'POST' });
  }

  // Labels
  async getLabels() {
    return this.request('/api/labels');
  }

  async ensureLabels() {
    return this.request('/api/labels/ensure', { method: 'POST' });
  }

  // Email Operations
  async syncEmails(query = null, limit = 100) {
    return this.request('/api/sync', {
      method: 'POST',
      body: { query, limit }
    });
  }

  async getPredictions(limit = 50) {
    return this.request(`/api/predictions?limit=${limit}`);
  }

  async reviewMessage(messageId, label) {
    return this.request('/api/review', {
      method: 'POST',
      body: { message_id: messageId, label }
    });
  }

  // Training
  async getTrainingStats() {
    return this.request('/api/training/stats');
  }

  async trainModel(epochs = 6) {
    return this.request('/api/train', {
      method: 'POST',
      body: { epochs }
    });
  }

  // Actions
  async applyActions(dryRun = true, limit = 100) {
    return this.request('/api/apply', {
      method: 'POST',
      body: { dry_run: dryRun, limit }
    });
  }
}

// Main React Component
const GmailClientApp = () => {
  const [api] = useState(() => new GmailClientAPI());
  const [status, setStatus] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [trainingStats, setTrainingStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('dashboard');

  // Load initial data
  useEffect(() => {
    loadStatus();
    loadTrainingStats();
  }, []);

  const loadStatus = async () => {
    try {
      const statusData = await api.getStatus();
      setStatus(statusData);
    } catch (error) {
      setMessage(`Error loading status: ${error.message}`);
    }
  };

  const loadPredictions = async () => {
    try {
      setLoading(true);
      const data = await api.getPredictions(50);
      setPredictions(data.actions);
      setMessage(`Loaded ${data.total_count} predictions`);
    } catch (error) {
      setMessage(`Error loading predictions: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadTrainingStats = async () => {
    try {
      const stats = await api.getTrainingStats();
      setTrainingStats(stats);
    } catch (error) {
      setMessage(`Error loading training stats: ${error.message}`);
    }
  };

  const handleInitialize = async () => {
    try {
      setLoading(true);
      await api.initialize();
      setMessage('Gmail ML Client initialized successfully');
      loadStatus();
    } catch (error) {
      setMessage(`Initialization failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setLoading(true);
      const result = await api.syncEmails(null, 100);
      setMessage(`Synced ${result.processed_messages}/${result.total_messages} messages`);
      loadStatus();
    } catch (error) {
      setMessage(`Sync failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    try {
      setLoading(true);
      const result = await api.trainModel(6);
      if (result.success) {
        setMessage(`Training completed successfully`);
        loadTrainingStats();
      } else {
        setMessage(`Training failed: ${result.error}`);
      }
    } catch (error) {
      setMessage(`Training failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (messageId, label) => {
    try {
      await api.reviewMessage(messageId, label);
      setMessage(`Message reviewed with label: ${label}`);
      loadTrainingStats();
      loadPredictions(); // Reload predictions
    } catch (error) {
      setMessage(`Review failed: ${error.message}`);
    }
  };

  const handleApply = async (dryRun = true) => {
    try {
      setLoading(true);
      const result = await api.applyActions(dryRun, 100);
      const action = dryRun ? 'simulated' : 'applied';
      setMessage(`${action} ${result.applied_actions}/${result.total_actions} actions`);
    } catch (error) {
      setMessage(`Apply failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'trash': return '#ff4444';
      case 'route': return '#44ff44';
      case 'review': return '#ffaa44';
      default: return '#888888';
    }
  };

  return (
    <div className="gmail-client-app">
      <header className="app-header">
        <h1>📧 Gmail ML Client</h1>
        <div className="status-indicator">
          {status ? (
            <span className={`status ${status.status}`}>
              {status.status.toUpperCase()}
            </span>
          ) : (
            <span className="status unknown">UNKNOWN</span>
          )}
        </div>
      </header>

      <nav className="tab-nav">
        {['dashboard', 'predictions', 'training', 'actions'].map(tab => (
          <button
            key={tab}
            className={`tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </nav>

      {message && (
        <div className="message-bar">
          <span>{message}</span>
          <button onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <main className="app-content">
        {activeTab === 'dashboard' && (
          <div className="dashboard-tab">
            <div className="quick-actions">
              <h2>Quick Actions</h2>
              <div className="action-buttons">
                <button onClick={handleInitialize} disabled={loading}>
                  🔧 Initialize
                </button>
                <button onClick={handleSync} disabled={loading}>
                  📥 Sync Emails
                </button>
                <button onClick={loadPredictions} disabled={loading}>
                  🔮 Load Predictions
                </button>
                <button onClick={handleTrain} disabled={loading}>
                  🧠 Train Model
                </button>
              </div>
            </div>

            {status && (
              <div className="status-panel">
                <h2>System Status</h2>
                <div className="status-grid">
                  <div className="status-item">
                    <label>Status:</label>
                    <span className={status.status}>{status.status}</span>
                  </div>
                  <div className="status-item">
                    <label>Version:</label>
                    <span>{status.version}</span>
                  </div>
                  <div className="status-item">
                    <label>Last Update:</label>
                    <span>{new Date(status.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            )}

            {trainingStats && (
              <div className="training-overview">
                <h2>Training Data Overview</h2>
                <div className="stats-grid">
                  <div className="stat-item">
                    <span className="stat-value">{trainingStats.total_samples}</span>
                    <span className="stat-label">Total Samples</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{trainingStats.unique_labels}</span>
                    <span className="stat-label">Unique Labels</span>
                  </div>
                </div>
                <div className="label-distribution">
                  <h3>Label Distribution</h3>
                  {Object.entries(trainingStats.label_counts).map(([label, count]) => (
                    <div key={label} className="label-bar">
                      <span className="label-name">{label}</span>
                      <div className="bar-container">
                        <div 
                          className="bar-fill" 
                          style={{ 
                            width: `${(count / trainingStats.total_samples) * 100}%` 
                          }}
                        />
                      </div>
                      <span className="label-count">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'predictions' && (
          <div className="predictions-tab">
            <div className="predictions-header">
              <h2>Email Predictions</h2>
              <button onClick={loadPredictions} disabled={loading}>
                🔄 Refresh
              </button>
            </div>

            {predictions.length > 0 ? (
              <div className="predictions-list">
                {predictions.map((prediction, index) => (
                  <div key={prediction.id} className="prediction-card">
                    <div className="prediction-header">
                      <span className="message-id">#{prediction.id.slice(-8)}</span>
                      <span 
                        className="action-badge"
                        style={{ backgroundColor: getActionColor(prediction.action) }}
                      >
                        {prediction.action.toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="prediction-content">
                      <p className="snippet">{prediction.snippet}</p>
                      
                      <div className="prediction-details">
                        <div className="detail-item">
                          <label>Spam Score:</label>
                          <span className={prediction.spam_score > 0.8 ? 'high-risk' : 'low-risk'}>
                            {(prediction.spam_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="detail-item">
                          <label>Confidence:</label>
                          <span>{(prediction.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div className="detail-item">
                          <label>Predicted Label:</label>
                          <span>{prediction.predicted_label || 'N/A'}</span>
                        </div>
                        <div className="detail-item">
                          <label>Target Label:</label>
                          <span>{prediction.target_label || 'N/A'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="review-actions">
                      <select 
                        onChange={(e) => e.target.value && handleReview(prediction.id, e.target.value)}
                        defaultValue=""
                      >
                        <option value="">Review as...</option>
                        <option value="SPAM">SPAM</option>
                        <option value="Work">Work</option>
                        <option value="Personal">Personal</option>
                        <option value="Receipts">Receipts</option>
                        <option value="Finance">Finance</option>
                        <option value="Newsletters">Newsletters</option>
                        <option value="Social">Social</option>
                        <option value="Updates">Updates</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No predictions available. Try syncing emails first.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'training' && (
          <div className="training-tab">
            <h2>Model Training</h2>
            
            {trainingStats && (
              <div className="training-status">
                <h3>Training Data Status</h3>
                <p>
                  You have <strong>{trainingStats.total_samples}</strong> labeled samples 
                  across <strong>{trainingStats.unique_labels}</strong> different labels.
                </p>
                
                {trainingStats.total_samples < 50 && (
                  <div className="warning">
                    ⚠️ Consider adding more training data for better accuracy (recommended: 50+ samples per label)
                  </div>
                )}
              </div>
            )}

            <div className="training-actions">
              <button 
                onClick={handleTrain} 
                disabled={loading || !trainingStats || trainingStats.total_samples < 10}
                className="primary-button"
              >
                {loading ? '🧠 Training...' : '🧠 Train Model'}
              </button>
              
              <button onClick={loadTrainingStats} disabled={loading}>
                📊 Refresh Stats
              </button>
            </div>

            <div className="training-tips">
              <h3>Training Tips</h3>
              <ul>
                <li>Review at least 10 emails per label before training</li>
                <li>Include both positive and negative examples</li>
                <li>Training typically takes 30-60 seconds</li>
                <li>Re-train periodically as you review more emails</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'actions' && (
          <div className="actions-tab">
            <h2>Apply Actions</h2>
            
            <div className="action-controls">
              <div className="dry-run-section">
                <h3>Test Run (Safe)</h3>
                <p>Preview what actions would be taken without actually modifying emails.</p>
                <button onClick={() => handleApply(true)} disabled={loading}>
                  🔍 Dry Run
                </button>
              </div>

              <div className="live-run-section">
                <h3>Live Run (Careful!)</h3>
                <p>Actually apply actions to your Gmail account. This will move/delete emails.</p>
                <button 
                  onClick={() => handleApply(false)} 
                  disabled={loading}
                  className="danger-button"
                >
                  ⚡ Apply Actions
                </button>
              </div>
            </div>

            <div className="action-safety">
              <h3>Safety Notes</h3>
              <ul>
                <li>✅ Always run dry-run first to preview actions</li>
                <li>✅ Emails are moved to Trash, not permanently deleted</li>
                <li>✅ You can recover emails from Gmail Trash</li>
                <li>⚠️ Actions are applied immediately when using Live Run</li>
              </ul>
            </div>
          </div>
        )}
      </main>

      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner">⏳ Processing...</div>
        </div>
      )}
    </div>
  );
};

export default GmailClientApp;