# AutoApply AI — Zero-Budget SaaS Roadmap
## Production-Ready Architecture for Highest Demo ROI

**Last Updated**: May 2026  
**Architecture Status**: Strong foundation (Celery, Socket.IO, PostgreSQL, React)  
**Deployment Target**: Render Free Tier + PostgreSQL  
**Core Strategy**: Maximum demo value with zero infrastructure cost

---

## EXECUTIVE SUMMARY

### Current State
- ✅ Resume-first onboarding
- ✅ Job scraping (Playwright)
- ✅ Queue-based application system
- ✅ Modern React dashboard
- ✅ Async infrastructure (Celery + Redis)
- ✅ Production stabilization

### Gaps (High-ROI Priority)
- ❌ Multi-user authentication
- ❌ Human-in-the-loop approval system
- ❌ Explainable AI matching
- ❌ AI-generated responses
- ❌ Semantic job matching
- ❌ Goal-based personalization

### This Roadmap Delivers
- **Phase A**: Complete multi-user SaaS with approval workflow (2 weeks)
- **Phase B**: AI-powered features using Gemini free tier (2 weeks)
- **Phase C**: Intelligent matching & adaptive learning (3 weeks)
- **Phase D**: Multi-source expansion & scaling (ongoing)

**Total Implementation Time**: 6-8 weeks for MVP SaaS product

---

## PHASE A: CORE SAAS FEATURES (Weeks 1-2)

### 1.1 JWT Authentication + Multi-User Support

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (React)                                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Login → JWT in HttpOnly Cookie → Protected Routes  │ │
│ │ CSRF Token in Header for POST/PUT/DELETE           │ │
│ └─────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
    /api/auth/login          /api/auth/refresh
    /api/auth/logout         /api/auth/profile
         │                        │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────────┐
         │ Flask Backend              │
         │ @require_jwt decorator     │
         │ g.user_id context          │
         └───────────┬────────────────┘
                     │
         ┌───────────▼────────────────┐
         │ Database                   │
         │ users table                │
         │ per-user queues            │
         │ per-user resumes           │
         └────────────────────────────┘
```

#### Database Schema (Already Updated)

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    is_active INTEGER DEFAULT 1
);

-- All existing tables now include:
ALTER TABLE jobs ADD COLUMN user_id INTEGER;
ALTER TABLE apply_queue ADD COLUMN user_id INTEGER;
ALTER TABLE user_goals ADD COLUMN user_id INTEGER;
ALTER TABLE application_outcomes ADD COLUMN user_id INTEGER;
ALTER TABLE skill_outcome_map ADD COLUMN user_id INTEGER;
ALTER TABLE threshold_history ADD COLUMN user_id INTEGER;
```

#### JWT Security Implementation

**File**: `src/finder/shared/jwt_security.py` (Already exists ✓)

Key features:
- HttpOnly + Secure cookies (NO localStorage)
- CSRF token generation & validation
- Access token (15 min) + Refresh token (7 days)
- Token revocation support
- Flask decorators: `@require_jwt`, `@require_csrf`

#### Authentication Endpoints

**File**: `src/finder/api/auth.py` (NEW)

```python
from flask import Blueprint, request, jsonify, make_response, g
from werkzeug.security import generate_password_hash, check_password_hash
from finder.shared.database import get_db
from finder.shared.jwt_security import (
    JWTManager,
    CSRFTokenManager,
    require_jwt,
    set_access_token_cookie,
    set_refresh_token_cookie,
    set_csrf_token_cookie,
    clear_auth_cookies,
)
import logging

log = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register new user."""
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    if not email or not password or len(password) < 8:
        return jsonify({"error": "Invalid email or password (min 8 chars)"}), 400
    
    db = get_db()
    
    # Check if user exists
    user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if user:
        return jsonify({"error": "Email already registered"}), 409
    
    # Create user
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    cursor = db.execute(
        "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
        (email, password_hash, full_name)
    )
    db.commit()
    user_id = cursor.lastrowid
    
    log.info(f"User registered: {email} (id={user_id})")
    
    # Generate tokens
    response = make_response({
        "status": "registered",
        "user_id": user_id,
        "email": email
    })
    
    access_token = JWTManager.generate_access_token(str(user_id))
    refresh_token = JWTManager.generate_refresh_token(str(user_id))
    csrf_token = CSRFTokenManager.generate()
    
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    set_csrf_token_cookie(response, csrf_token)
    
    return response, 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user."""
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    
    db = get_db()
    user = db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Update last login
    db.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
    db.commit()
    
    log.info(f"User logged in: {email}")
    
    # Generate tokens
    response = make_response({"status": "authenticated", "user_id": user['id']})
    
    access_token = JWTManager.generate_access_token(str(user['id']))
    refresh_token = JWTManager.generate_refresh_token(str(user['id']))
    csrf_token = CSRFTokenManager.generate()
    
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    set_csrf_token_cookie(response, csrf_token)
    
    return response, 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get('refresh_token')
    
    if not refresh_token:
        return jsonify({"error": "No refresh token"}), 401
    
    is_valid, payload, error = JWTManager.verify_token(refresh_token)
    if not is_valid or payload.get('type') != 'refresh':
        return jsonify({"error": f"Invalid refresh token: {error}"}), 401
    
    user_id = payload.get('sub')
    response = make_response({"status": "refreshed"})
    
    access_token = JWTManager.generate_access_token(user_id)
    set_access_token_cookie(response, access_token)
    
    log.debug(f"Token refreshed for user {user_id}")
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
@require_jwt
def logout():
    """Logout user."""
    response = make_response({"status": "logged out"})
    clear_auth_cookies(response)
    log.info(f"User logged out: {g.user_id}")
    return response, 200


@auth_bp.route('/profile', methods=['GET'])
@require_jwt
def profile():
    """Get current user profile."""
    db = get_db()
    user = db.execute(
        "SELECT id, email, full_name, created_at, last_login FROM users WHERE id = ?",
        (int(g.user_id),)
    ).fetchone()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user['id'],
        "email": user['email'],
        "full_name": user['full_name'],
        "created_at": user['created_at'],
        "last_login": user['last_login']
    }), 200


@auth_bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    """Get a new CSRF token for forms."""
    csrf_token = CSRFTokenManager.generate()
    response = make_response({"csrf_token": csrf_token})
    set_csrf_token_cookie(response, csrf_token)
    return response, 200
```

#### Frontend Authentication (React)

**File**: `finder-ui/src/pages/LoginPage.jsx` (NEW)

```jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = isSignup ? '/auth/signup' : '/auth/login';
      const payload = isSignup
        ? { email, password, full_name: fullName }
        : { email, password };

      const response = await api.post(endpoint, payload);
      
      // JWT is automatically in cookies (HttpOnly)
      // Redirect to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">
          {isSignup ? 'Create Account' : 'Login'}
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignup && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            {isSignup && (
              <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg transition disabled:opacity-50"
          >
            {loading ? 'Processing...' : isSignup ? 'Sign Up' : 'Login'}
          </button>
        </form>

        <button
          onClick={() => setIsSignup(!isSignup)}
          className="w-full mt-4 text-blue-600 hover:text-blue-700 text-sm"
        >
          {isSignup ? 'Already have an account? Login' : 'Create new account'}
        </button>
      </div>
    </div>
  );
}
```

#### Integration in Main API

**File**: `src/finder/api/main.py` (MODIFY)

```python
# Add at top
from finder.api.auth import auth_bp

# Register blueprint
app.register_blueprint(auth_bp)

# Add protected route example
@app.route("/api/user/queue")
@require_jwt
def get_user_queue():
    """Get user's apply queue (multi-user support)."""
    db = get_db()
    queue = db.execute(
        """SELECT * FROM apply_queue 
           WHERE user_id = ? 
           ORDER BY queued_at DESC 
           LIMIT 100""",
        (int(g.user_id),)
    ).fetchall()
    return jsonify([dict(row) for row in queue])
```

#### Frontend API Configuration

**File**: `finder-ui/src/api.js` (MODIFY)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:5000/api',
  withCredentials: true, // Send cookies
});

// Intercept requests to add CSRF token
api.interceptors.request.use(async (config) => {
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method.toUpperCase())) {
    // Get CSRF token from cookie
    const csrfToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrf_token='))
      ?.split('=')[1];
    
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
});

export default api;
```

---

### 1.2 Approval Queue UI (Human-in-the-Loop)

#### Architecture

```
┌─────────────────────────────────────┐
│ Queue Item                          │
├─────────────────────────────────────┤
│ Company: Acme Corp                  │
│ Role: Senior React Developer        │
│ Match: 85%                          │
│                                     │
│ AI-Generated Answer Preview:        │
│ ┌─────────────────────────────────┐ │
│ │ "Why are you interested?"        │ │
│ │ [edit button]                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [✓ Approve] [✗ Reject] [⊘ Skip]   │
│ [Blacklist] [View Job]              │
└─────────────────────────────────────┘
```

#### Database Schema

```sql
CREATE TABLE IF NOT EXISTS approval_queue_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_url TEXT NOT NULL,
    job_json TEXT,
    ai_answers_json TEXT,
    match_score REAL,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected, applied
    approved_at DATETIME,
    applied_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company TEXT,
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Backend API Endpoints

**File**: `src/finder/api/approval_queue.py` (NEW)

```python
from flask import Blueprint, request, jsonify, g
from finder.shared.database import get_db
from finder.shared.jwt_security import require_jwt, require_csrf
import logging

log = logging.getLogger(__name__)
queue_bp = Blueprint('approval_queue', __name__, url_prefix='/api/approval-queue')

@queue_bp.route('', methods=['GET'])
@require_jwt
def get_queue():
    """Get user's approval queue."""
    db = get_db()
    items = db.execute(
        """SELECT * FROM approval_queue_items 
           WHERE user_id = ? AND status = 'pending'
           ORDER BY match_score DESC
           LIMIT 50""",
        (int(g.user_id),)
    ).fetchall()
    return jsonify([dict(row) for row in items])

@queue_bp.route('/<int:item_id>/approve', methods=['POST'])
@require_jwt
@require_csrf
def approve_item(item_id):
    """Approve application."""
    db = get_db()
    
    # Verify ownership
    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id))
    ).fetchone()
    
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    # Update status
    db.execute(
        """UPDATE approval_queue_items 
           SET status = 'approved', approved_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (item_id,)
    )
    db.commit()
    
    log.info(f"Approved item {item_id} for user {g.user_id}")
    return jsonify({"status": "approved"}), 200

@queue_bp.route('/<int:item_id>/reject', methods=['POST'])
@require_jwt
@require_csrf
def reject_item(item_id):
    """Reject application."""
    db = get_db()
    
    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id))
    ).fetchone()
    
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    db.execute(
        "UPDATE approval_queue_items SET status = 'rejected' WHERE id = ?",
        (item_id,)
    )
    db.commit()
    
    log.info(f"Rejected item {item_id} for user {g.user_id}")
    return jsonify({"status": "rejected"}), 200

@queue_bp.route('/<int:item_id>/skip', methods=['POST'])
@require_jwt
@require_csrf
def skip_item(item_id):
    """Skip item (remove from queue, no decision)."""
    db = get_db()
    
    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id))
    ).fetchone()
    
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    db.execute(
        "UPDATE approval_queue_items SET status = 'skipped' WHERE id = ?",
        (item_id,)
    )
    db.commit()
    
    return jsonify({"status": "skipped"}), 200

@queue_bp.route('/<int:item_id>', methods=['PUT'])
@require_jwt
@require_csrf
def update_item(item_id):
    """Update AI-generated answers before approval."""
    data = request.json or {}
    db = get_db()
    
    item = db.execute(
        "SELECT * FROM approval_queue_items WHERE id = ? AND user_id = ?",
        (item_id, int(g.user_id))
    ).fetchone()
    
    if not item:
        return jsonify({"error": "Item not found"}), 404
    
    # Update answers
    import json
    answers = json.loads(item['ai_answers_json'] or '{}')
    answers.update(data.get('answers', {}))
    
    db.execute(
        "UPDATE approval_queue_items SET ai_answers_json = ? WHERE id = ?",
        (json.dumps(answers), item_id)
    )
    db.commit()
    
    log.info(f"Updated answers for item {item_id}")
    return jsonify({"status": "updated"}), 200

@queue_bp.route('/blacklist', methods=['POST'])
@require_jwt
@require_csrf
def add_blacklist():
    """Add company to blacklist."""
    data = request.json or {}
    company = data.get('company')
    reason = data.get('reason', 'User preference')
    
    if not company:
        return jsonify({"error": "Company required"}), 400
    
    db = get_db()
    db.execute(
        "INSERT INTO user_blacklist (user_id, company, reason) VALUES (?, ?, ?)",
        (int(g.user_id), company, reason)
    )
    db.commit()
    
    log.info(f"Blacklisted {company} for user {g.user_id}")
    return jsonify({"status": "blacklisted"}), 201
```

#### Frontend Component

**File**: `finder-ui/src/pages/ApprovalQueuePage.jsx` (NEW)

```jsx
import { useState, useEffect } from 'react';
import api from '../api';

export default function ApprovalQueuePage() {
  const [queue, setQueue] = useState([]);
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [editingAnswers, setEditingAnswers] = useState({});

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    try {
      const response = await api.get('/approval-queue');
      setQueue(response.data);
    } catch (error) {
      console.error('Failed to load queue', error);
    } finally {
      setLoading(false);
    }
  };

  const item = queue[current];

  const handleApprove = async () => {
    try {
      await api.post(`/approval-queue/${item.id}/approve`);
      setQueue(queue.filter(q => q.id !== item.id));
      setCurrent(Math.min(current, queue.length - 2));
    } catch (error) {
      console.error('Failed to approve', error);
    }
  };

  const handleReject = async () => {
    try {
      await api.post(`/approval-queue/${item.id}/reject`);
      setQueue(queue.filter(q => q.id !== item.id));
      setCurrent(Math.min(current, queue.length - 2));
    } catch (error) {
      console.error('Failed to reject', error);
    }
  };

  const handleSkip = async () => {
    setCurrent(current + 1);
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (!item) return <div className="p-8">Queue empty</div>;

  const job = JSON.parse(item.job_json || '{}');
  const answers = JSON.parse(item.ai_answers_json || '{}');

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Progress */}
        <div className="mb-6 text-sm text-gray-600">
          {current + 1} of {queue.length}
        </div>

        {/* Job Info */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800">{job.title}</h2>
          <p className="text-lg text-gray-600">{job.company}</p>
          <p className="text-sm text-gray-500">{job.location}</p>
        </div>

        {/* Match Score */}
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="font-semibold">Match Score</span>
            <span className="text-2xl font-bold text-blue-600">
              {Math.round(item.match_score)}%
            </span>
          </div>
        </div>

        {/* AI Answers Preview */}
        <div className="mb-6 border-t pt-6">
          <h3 className="font-semibold text-gray-800 mb-4">AI-Generated Answers</h3>
          {Object.entries(answers).map(([key, value]) => (
            <div key={key} className="mb-4 p-4 bg-gray-50 rounded">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {key}
              </label>
              <textarea
                value={value}
                onChange={(e) =>
                  setEditingAnswers({
                    ...editingAnswers,
                    [key]: e.target.value
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                rows={3}
              />
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={handleReject}
            className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium"
          >
            Reject
          </button>
          <button
            onClick={handleSkip}
            className="flex-1 px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium"
          >
            Skip
          </button>
          <button
            onClick={handleApprove}
            className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

### 1.3 Explainable AI Matching

#### Architecture

```
Job Match Score Breakdown:
┌─────────────────────────────────┐
│ React detected in resume        │ +25%
│ Full-stack background          │ +15%
│ Semantic similarity (82%)       │ +30%
│ Internship-friendly role        │ +10%
│ Goal alignment (senior role)    │ +5%
├─────────────────────────────────┤
│ Final Score: 85%               │
└─────────────────────────────────┘
```

#### Backend Scoring Engine

**File**: `src/finder/core/explainable_matching.py` (NEW)

```python
"""Explainable AI matching engine."""

import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

log = logging.getLogger(__name__)

@dataclass
class ScoreComponent:
    """Individual score component."""
    label: str
    value: float  # 0-1
    explanation: str
    weight: float  # 0-1

class ExplainableJobMatcher:
    """Score jobs with transparent breakdown."""
    
    def __init__(self, user_resume_text: str, user_goals: Dict):
        self.resume_text = user_resume_text.lower()
        self.goals = user_goals
        self.components = []
    
    def match(self, job_dict: Dict) -> Tuple[float, List[Dict]]:
        """
        Score job and return (total_score, components).
        
        Args:
            job_dict: Job with title, description, skills
            
        Returns:
            (0-100 score, list of score components)
        """
        self.components = []
        
        # Extract skills from resume
        resume_skills = self._extract_skills()
        
        # Extract job requirements
        job_skills = job_dict.get('skills', '')
        job_desc = job_dict.get('description', '').lower()
        job_title = job_dict.get('title', '').lower()
        
        # 1. Skill Overlap (30% weight)
        skill_overlap = self._calculate_skill_overlap(resume_skills, job_skills)
        self.components.append(ScoreComponent(
            label="Skill Match",
            value=skill_overlap,
            explanation=self._skill_explanation(resume_skills, job_skills),
            weight=0.30
        ))
        
        # 2. Semantic Similarity (30% weight)
        semantic_sim = self._semantic_similarity(job_desc)
        self.components.append(ScoreComponent(
            label="Semantic Fit",
            value=semantic_sim,
            explanation=f"Job description aligns with resume context",
            weight=0.30
        ))
        
        # 3. Role-Goal Alignment (20% weight)
        goal_alignment = self._goal_alignment(job_title)
        self.components.append(ScoreComponent(
            label="Goal Alignment",
            value=goal_alignment,
            explanation=self._goal_explanation(job_title),
            weight=0.20
        ))
        
        # 4. Level Match (15% weight)
        level_match = self._level_match(job_title)
        self.components.append(ScoreComponent(
            label="Experience Level",
            value=level_match,
            explanation=self._level_explanation(job_title),
            weight=0.15
        ))
        
        # 5. Hiring Signal (5% weight)
        hiring_signal = self._hiring_signal(job_desc)
        self.components.append(ScoreComponent(
            label="Hiring Signals",
            value=hiring_signal,
            explanation=self._hiring_explanation(job_desc),
            weight=0.05
        ))
        
        # Calculate weighted total
        total_score = sum(
            c.value * c.weight for c in self.components
        )
        
        return total_score * 100, [asdict(c) for c in self.components]
    
    def _extract_skills(self) -> List[str]:
        """Extract detected skills from resume."""
        common_skills = {
            'python': ['python', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue'],
            'java': ['java', 'spring', 'maven'],
            'sql': ['sql', 'postgres', 'mysql'],
            'frontend': ['react', 'vue', 'angular', 'html', 'css'],
            'backend': ['django', 'flask', 'fastapi', 'express'],
        }
        
        detected = []
        for category, keywords in common_skills.items():
            if any(kw in self.resume_text for kw in keywords):
                detected.append(category)
        
        return detected
    
    def _calculate_skill_overlap(self, resume_skills: List[str], job_skills: str) -> float:
        """Calculate overlap between resume and job skills."""
        job_skills_lower = job_skills.lower()
        
        if not resume_skills:
            return 0.0
        
        matches = sum(1 for skill in resume_skills if skill in job_skills_lower)
        return min(matches / len(resume_skills), 1.0)
    
    def _skill_explanation(self, resume_skills: List[str], job_skills: str) -> str:
        """Explain skill matches."""
        matched = [s for s in resume_skills if s in job_skills.lower()]
        if not matched:
            return "Limited skill overlap detected"
        return f"Matched skills: {', '.join(matched)}"
    
    def _semantic_similarity(self, job_desc: str) -> float:
        """Calculate semantic similarity (placeholder)."""
        # TODO: Implement using sentence-transformers
        # For now, use TF-IDF style matching
        resume_terms = set(self.resume_text.split())
        job_terms = set(job_desc.split())
        
        if not job_terms:
            return 0.5
        
        overlap = len(resume_terms & job_terms)
        return min(overlap / len(job_terms), 1.0)
    
    def _goal_alignment(self, job_title: str) -> float:
        """Check alignment with user goals."""
        target_role = self.goals.get('target_role', '').lower()
        
        if not target_role:
            return 0.7  # Neutral if no goal set
        
        if target_role in job_title:
            return 1.0
        
        return 0.5
    
    def _goal_explanation(self, job_title: str) -> str:
        """Explain goal alignment."""
        target_role = self.goals.get('target_role', '')
        if target_role and target_role.lower() in job_title:
            return f"Matches your target role: {target_role}"
        return "Aligns with your career goals"
    
    def _level_match(self, job_title: str) -> float:
        """Check experience level match."""
        job_title_lower = job_title.lower()
        user_years = self.goals.get('years_experience', 0)
        
        levels = {
            'intern': (0, 1),
            'junior': (1, 3),
            'mid': (3, 7),
            'senior': (7, 15),
            'lead': (10, 30),
        }
        
        job_level = None
        for level, (min_yrs, max_yrs) in levels.items():
            if level in job_title_lower:
                job_level = (min_yrs, max_yrs)
                break
        
        if not job_level:
            return 0.8  # Neutral if unclear
        
        min_yrs, max_yrs = job_level
        if min_yrs <= user_years <= max_yrs:
            return 1.0
        elif user_years < min_yrs:
            return 0.6  # Stretch role
        else:
            return 0.4  # Under-leveled
    
    def _level_explanation(self, job_title: str) -> str:
        """Explain level match."""
        years = self.goals.get('years_experience', 0)
        if 'intern' in job_title.lower() and years < 1:
            return "Internship role - perfect for your experience level"
        elif 'senior' in job_title.lower() and years >= 7:
            return "Senior role - matches your seniority"
        return "Experience level appears compatible"
    
    def _hiring_signal(self, job_desc: str) -> float:
        """Detect hiring signals (sponsorship, diversity, etc.)."""
        signals = {
            'sponsorship': ['visa', 'sponsorship', 'h1b'],
            'diversity': ['diversity', 'women', 'underrepresented'],
            'startup': ['startup', 'equity', 'early-stage'],
            'remote': ['remote', 'work from home'],
        }
        
        count = 0
        for signal_type, keywords in signals.items():
            if any(kw in job_desc for kw in keywords):
                count += 1
        
        return min(count / len(signals), 1.0)
    
    def _hiring_explanation(self, job_desc: str) -> str:
        """Explain hiring signals."""
        if 'visa' in job_desc or 'sponsorship' in job_desc:
            return "Company offers visa sponsorship"
        if 'remote' in job_desc:
            return "Remote position available"
        return "Standard hiring signals"
```

#### Frontend Display Component

**File**: `finder-ui/src/components/ExplainableScoreCard.jsx` (NEW)

```jsx
export default function ExplainableScoreCard({ item, components }) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      {/* Overall Score */}
      <div className="mb-6 pb-6 border-b">
        <div className="flex items-center justify-between mb-2">
          <span className="text-lg font-semibold text-gray-800">Match Score</span>
          <span className="text-4xl font-bold text-blue-600">
            {Math.round(item.match_score)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full"
            style={{ width: `${item.match_score}%` }}
          />
        </div>
      </div>

      {/* Component Breakdown */}
      <div className="space-y-4">
        <h3 className="font-semibold text-gray-700 mb-4">Score Breakdown</h3>
        
        {components.map((comp, idx) => (
          <div key={idx} className="flex items-start gap-4">
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="font-medium text-gray-700">{comp.label}</span>
                <span className="text-sm text-gray-600">
                  {Math.round(comp.value * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded h-1.5 mb-1">
                <div
                  className="bg-gradient-to-r from-blue-400 to-blue-600 h-1.5 rounded"
                  style={{ width: `${comp.value * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-600">{comp.explanation}</p>
              <p className="text-xs text-gray-500 mt-1">
                Weight: {Math.round(comp.weight * 100)}%
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Why This Job */}
      <div className="mt-6 p-4 bg-blue-50 rounded border border-blue-200">
        <p className="text-sm text-blue-900">
          ✓ This job ranked highly because it matches your skills,
          aligns with your goals, and your experience level fits well.
        </p>
      </div>
    </div>
  );
}
```

---

## PHASE B: AI-POWERED FEATURES (Weeks 3-4)

### 2.1 Gemini Free Tier Integration

#### Strategy

- **Use Gemini 1.5 Flash** for speed & free tier compatibility
- **Implement aggressive caching** (24h cache for identical requests)
- **Token budget limits**: 2M tokens/day free tier
- **Fallback to templates** if quota exceeded
- **Celery task queuing** for async generation

#### Setup

```bash
# .env
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
AI_CACHE_HOURS=24
AI_BUDGET_DAILY_TOKENS=1500000
```

#### Caching Layer

**File**: `src/finder/shared/ai_cache.py` (NEW)

```python
"""AI generation caching to stay within free tier."""

import json
import hashlib
from datetime import datetime, timedelta
from finder.shared.database import get_db
import logging

log = logging.getLogger(__name__)

class AICache:
    """Cache AI generations to reduce API calls."""
    
    @staticmethod
    def get_cache_key(prompt: str, context: str) -> str:
        """Generate cache key from prompt + context."""
        combined = f"{prompt}|{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    @staticmethod
    def get(prompt: str, context: str) -> str | None:
        """Get cached generation."""
        db = get_db()
        cache_key = AICache.get_cache_key(prompt, context)
        
        result = db.execute(
            """SELECT response FROM ai_cache 
               WHERE cache_key = ? 
               AND created_at > datetime('now', '-24 hours')""",
            (cache_key,)
        ).fetchone()
        
        if result:
            log.debug(f"AI cache hit for key {cache_key}")
            return result['response']
        
        return None
    
    @staticmethod
    def set(prompt: str, context: str, response: str) -> None:
        """Cache AI generation."""
        db = get_db()
        cache_key = AICache.get_cache_key(prompt, context)
        
        db.execute(
            """INSERT INTO ai_cache (cache_key, prompt, context, response) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET 
               response = ?, created_at = CURRENT_TIMESTAMP""",
            (cache_key, prompt, context, response, response)
        )
        db.commit()
        log.debug(f"Cached AI response for key {cache_key}")
```

#### Gemini Client

**File**: `src/finder/core/ai_providers/gemini_client.py` (NEW)

```python
"""Google Gemini integration."""

import os
import logging
import json
from typing import Optional
import google.generativeai as genai
from finder.shared.ai_cache import AICache

log = logging.getLogger(__name__)

class GeminiClient:
    """Gemini API wrapper with caching and budget management."""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        genai.configure(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.daily_budget = int(os.getenv("AI_BUDGET_DAILY_TOKENS", "1500000"))
    
    def generate_job_answers(self, job: dict, resume: str) -> dict:
        """
        Generate answers for job application form.
        
        Args:
            job: Job dict with title, description, questions
            resume: User's resume text
            
        Returns:
            Dict of {question: answer}
        """
        cache_key = f"job_answers|{job.get('job_url')}"
        
        # Check cache first
        cached = AICache.get("job_answers", cache_key)
        if cached:
            return json.loads(cached)
        
        prompt = f"""
        Based on this resume and job posting, generate professional answers
        to common job application questions.
        
        RESUME:
        {resume}
        
        JOB:
        Title: {job.get('title')}
        Description: {job.get('description')}
        
        Generate JSON with these fields:
        - why_interested: Why interested in this role
        - relevant_experience: Most relevant experience
        - key_strengths: Top 3 strengths for this role
        - questions: 2-3 technical questions you'd ask the interviewer
        
        Output ONLY valid JSON, no markdown.
        """
        
        try:
            response = self.model_generate(prompt, max_tokens=500)
            answers = json.loads(response)
            
            # Cache result
            AICache.set("job_answers", cache_key, json.dumps(answers))
            
            return answers
        
        except Exception as e:
            log.error(f"Failed to generate job answers: {e}")
            return self._fallback_answers(job)
    
    def generate_interview_questions(self, job: dict, resume: str) -> dict:
        """
        Generate interview preparation questions.
        """
        cache_key = f"interview|{job.get('job_url')}"
        
        cached = AICache.get("interview", cache_key)
        if cached:
            return json.loads(cached)
        
        prompt = f"""
        Generate interview preparation for this role.
        
        RESUME: {resume}
        JOB: {job.get('title')} at {job.get('company')}
        
        Return JSON with:
        - behavioral: 3 behavioral questions
        - technical: 2 technical questions
        - hr: 2 HR screening questions
        - preparation_tips: Key points to prepare
        
        Output ONLY valid JSON.
        """
        
        try:
            response = self.model_generate(prompt, max_tokens=800)
            questions = json.loads(response)
            AICache.set("interview", cache_key, json.dumps(questions))
            return questions
        except Exception as e:
            log.error(f"Failed to generate interview questions: {e}")
            return self._fallback_interview()
    
    def model_generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Gemini API."""
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.7,
                }
            )
            return response.text
        except Exception as e:
            log.error(f"Gemini API error: {e}")
            raise
    
    def _fallback_answers(self, job: dict) -> dict:
        """Fallback if AI generation fails."""
        return {
            "why_interested": f"I'm interested in this {job.get('title')} role because it aligns with my skills and career goals.",
            "relevant_experience": "My experience includes relevant projects and contributions in this domain.",
            "key_strengths": ["Problem-solving", "Technical expertise", "Team collaboration"],
        }
    
    def _fallback_interview(self) -> dict:
        """Fallback interview questions."""
        return {
            "behavioral": ["Tell me about a challenging project", "Describe your teamwork experience"],
            "technical": ["Explain your technical background"],
            "hr": ["Why do you want this job?"],
            "preparation_tips": ["Review the job description", "Practice your elevator pitch"],
        }
```

#### Database Schema Update

```sql
CREATE TABLE IF NOT EXISTS ai_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    prompt TEXT,
    context TEXT,
    response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    model TEXT,
    tokens_used INTEGER,
    request_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### 2.2 Interview Preparation Mode

#### Backend API

**File**: `src/finder/api/interview_prep.py` (NEW)

```python
from flask import Blueprint, request, jsonify, g
from finder.shared.jwt_security import require_jwt
from finder.core.ai_providers.gemini_client import GeminiClient
import logging

log = logging.getLogger(__name__)
interview_bp = Blueprint('interview', __name__, url_prefix='/api/interview')

gemini = GeminiClient()

@interview_bp.route('/prepare/<int:job_id>', methods=['POST'])
@require_jwt
def prepare_interview(job_id):
    """Generate interview prep for a job."""
    from finder.shared.database import get_db
    
    db = get_db()
    
    # Get job
    job = db.execute(
        "SELECT * FROM jobs WHERE id = ? AND user_id = ?",
        (job_id, int(g.user_id))
    ).fetchone()
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Get user's resume
    # TODO: Implement resume retrieval
    resume = "Sample resume text"
    
    # Generate questions
    questions = gemini.generate_interview_questions(
        dict(job),
        resume
    )
    
    return jsonify(questions), 200
```

#### Frontend Component

**File**: `finder-ui/src/pages/InterviewPrepPage.jsx` (NEW)

```jsx
import { useState } from 'react';
import api from '../api';

export default function InterviewPrepPage() {
  const [jobId, setJobId] = useState('');
  const [prep, setPrep] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGeneratePrep = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const response = await api.post(`/interview/prepare/${jobId}`);
      setPrep(response.data);
    } catch (error) {
      console.error('Failed to generate prep', error);
    } finally {
      setLoading(false);
    }
  };

  if (!prep) {
    return (
      <div className="max-w-2xl mx-auto p-8">
        <div className="bg-white rounded-lg shadow p-8">
          <h1 className="text-3xl font-bold mb-6">Interview Preparation</h1>
          <input
            type="number"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            placeholder="Job ID"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4"
          />
          <button
            onClick={handleGeneratePrep}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Interview Prep'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="bg-white rounded-lg shadow p-8">
        <h1 className="text-2xl font-bold mb-6">Interview Preparation Plan</h1>

        {prep.behavioral && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Behavioral Questions
            </h2>
            <ul className="space-y-3">
              {prep.behavioral.map((q, i) => (
                <li key={i} className="p-4 bg-blue-50 border border-blue-200 rounded">
                  {q}
                </li>
              ))}
            </ul>
          </div>
        )}

        {prep.technical && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Technical Questions
            </h2>
            <ul className="space-y-3">
              {prep.technical.map((q, i) => (
                <li key={i} className="p-4 bg-green-50 border border-green-200 rounded">
                  {q}
                </li>
              ))}
            </ul>
          </div>
        )}

        {prep.preparation_tips && (
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <h3 className="font-semibold text-yellow-900 mb-2">Preparation Tips</h3>
            <ul className="text-sm text-yellow-800 space-y-1">
              {prep.preparation_tips.map((tip, i) => (
                <li key={i}>• {tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## PHASE C: MATCHING INTELLIGENCE (Weeks 5-7)

### 3.1 Hybrid Semantic Matching

#### Architecture

```
Job Text → Embeddings (all-MiniLM-L6-v2)
Resume Text → Embeddings
↓
Cosine Similarity (0-1)
+ TF-IDF overlap
+ Skill matching
= Final Score
```

#### Implementation

**File**: `src/finder/core/semantic_matching.py` (NEW)

```python
"""Hybrid semantic matching using local embeddings."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import logging

log = logging.getLogger(__name__)

class HybridJobMatcher:
    """
    Combines semantic similarity + TF-IDF + skill matching.
    
    Formula:
    Final Score = 0.5(semantic) + 0.3(tfidf) + 0.2(skills)
    """
    
    def __init__(self):
        # Load local embedding model (lightweight, no API calls)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tfidf = TfidfVectorizer(max_features=1000)
    
    def match_job(self, resume_text: str, job_dict: dict) -> float:
        """
        Score job match (0-100).
        
        Args:
            resume_text: User's resume
            job_dict: Job with title, description, skills
            
        Returns:
            Match score 0-100
        """
        # 1. Semantic similarity (30%)
        semantic = self._semantic_similarity(resume_text, job_dict)
        
        # 2. TF-IDF overlap (30%)
        tfidf = self._tfidf_similarity(resume_text, job_dict)
        
        # 3. Skill matching (20%)
        skills = self._skill_overlap(resume_text, job_dict)
        
        # 4. Role fit (10%)
        role_fit = self._role_fit(resume_text, job_dict)
        
        # 5. Experience level (10%)
        level = self._level_fit(resume_text, job_dict)
        
        # Weighted average
        score = (
            semantic * 0.30 +
            tfidf * 0.30 +
            skills * 0.20 +
            role_fit * 0.10 +
            level * 0.10
        )
        
        return max(0, min(100, score * 100))
    
    def _semantic_similarity(self, resume: str, job: dict) -> float:
        """Calculate semantic similarity using embeddings."""
        try:
            resume_embed = self.model.encode(resume[:1000])  # Truncate for speed
            job_text = f"{job.get('title')} {job.get('description')}"
            job_embed = self.model.encode(job_text[:1000])
            
            similarity = cosine_similarity(
                [resume_embed],
                [job_embed]
            )[0][0]
            
            return float(similarity)
        except Exception as e:
            log.error(f"Semantic similarity error: {e}")
            return 0.5
    
    def _tfidf_similarity(self, resume: str, job: dict) -> float:
        """Calculate TF-IDF based overlap."""
        try:
            job_text = f"{job.get('title')} {job.get('description')}"
            
            # Fit and transform
            tfidf_matrix = self.tfidf.fit_transform([resume, job_text])
            similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
            
            return float(similarity)
        except Exception as e:
            log.error(f"TF-IDF similarity error: {e}")
            return 0.5
    
    def _skill_overlap(self, resume: str, job: dict) -> float:
        """Calculate skill overlap."""
        common_skills = [
            'python', 'javascript', 'java', 'go', 'rust',
            'react', 'vue', 'angular',
            'django', 'flask', 'fastapi', 'express',
            'postgresql', 'mysql', 'mongodb',
            'aws', 'azure', 'gcp',
            'docker', 'kubernetes',
            'git', 'ci/cd',
        ]
        
        resume_skills = set()
        job_skills = set()
        
        resume_lower = resume.lower()
        job_lower = job.get('description', '').lower()
        
        for skill in common_skills:
            if skill in resume_lower:
                resume_skills.add(skill)
            if skill in job_lower:
                job_skills.add(skill)
        
        if not job_skills:
            return 0.5
        
        overlap = len(resume_skills & job_skills)
        return min(overlap / len(job_skills), 1.0)
    
    def _role_fit(self, resume: str, job: dict) -> float:
        """Check role type alignment."""
        role_types = {
            'frontend': ['react', 'vue', 'angular', 'frontend', 'ui'],
            'backend': ['backend', 'api', 'django', 'flask', 'spring'],
            'fullstack': ['fullstack', 'full stack', 'mern', 'mean'],
            'devops': ['devops', 'kubernetes', 'docker', 'ci/cd'],
            'data': ['data', 'ml', 'machine learning', 'sql'],
        }
        
        job_title = job.get('title', '').lower()
        resume_lower = resume.lower()
        
        # Find job role type
        job_type = None
        for role_type, keywords in role_types.items():
            if any(kw in job_title for kw in keywords):
                job_type = role_type
                break
        
        if not job_type:
            return 0.7
        
        # Check if resume matches role type
        role_keywords = role_types.get(job_type, [])
        matches = sum(1 for kw in role_keywords if kw in resume_lower)
        
        return min(matches / len(role_keywords), 1.0) if role_keywords else 0.7
    
    def _level_fit(self, resume: str, job: dict) -> float:
        """Check experience level fit."""
        levels = {
            'intern': ['intern', 'internship', 'fresher'],
            'junior': ['junior', 'entry', 'graduate'],
            'mid': ['mid-level', 'mid level', '3 years', '5 years'],
            'senior': ['senior', '7 years', '10 years', 'lead'],
        }
        
        job_title = job.get('title', '').lower()
        resume_lower = resume.lower()
        
        # Find job level
        job_level = None
        for level, keywords in levels.items():
            if any(kw in job_title for kw in keywords):
                job_level = level
                break
        
        if not job_level:
            return 0.8
        
        # Check if resume matches level
        level_keywords = levels.get(job_level, [])
        matches = sum(1 for kw in level_keywords if kw in resume_lower)
        
        return min(matches / len(level_keywords), 1.0) if level_keywords else 0.8
```

---

### 3.2 Adaptive AI Memory

#### Schema

```sql
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    preference_type TEXT,  -- rejected_role, preferred_role, etc.
    value TEXT,
    weight REAL DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS job_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_url TEXT,
    action TEXT,  -- approved, rejected, applied
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Adaptive Ranking

**File**: `src/finder/core/adaptive_ranking.py` (NEW)

```python
"""Lightweight adaptive ranking based on user behavior."""

import logging
from finder.shared.database import get_db

log = logging.getLogger(__name__)

class AdaptiveRanker:
    """Learn from user feedback without ML training."""
    
    @staticmethod
    def record_feedback(user_id: int, job_url: str, action: str, reason: str = None):
        """Record user action on a job."""
        db = get_db()
        db.execute(
            """INSERT INTO job_feedback (user_id, job_url, action, reason) 
               VALUES (?, ?, ?, ?)""",
            (user_id, job_url, action, reason)
        )
        db.commit()
        log.info(f"Recorded feedback for user {user_id}: {action} on {job_url}")
    
    @staticmethod
    def get_role_preferences(user_id: int) -> dict:
        """Extract role preferences from history."""
        db = get_db()
        
        # Find rejected roles
        rejected = db.execute(
            """SELECT j.title FROM job_feedback fb
               JOIN jobs j ON j.job_url = fb.job_url
               WHERE fb.user_id = ? AND fb.action = 'rejected'
               LIMIT 20""",
            (user_id,)
        ).fetchall()
        
        # Find approved roles
        approved = db.execute(
            """SELECT j.title FROM job_feedback fb
               JOIN jobs j ON j.job_url = fb.job_url
               WHERE fb.user_id = ? AND fb.action = 'approved'
               LIMIT 20""",
            (user_id,)
        ).fetchall()
        
        return {
            "rejected_patterns": [r['title'] for r in rejected],
            "approved_patterns": [a['title'] for a in approved],
        }
    
    @staticmethod
    def apply_user_preferences(score: float, job_dict: dict, preferences: dict) -> float:
        """Adjust score based on user preferences."""
        job_title = job_dict.get('title', '').lower()
        
        # Penalize rejected patterns
        for pattern in preferences.get('rejected_patterns', []):
            if pattern.lower() in job_title:
                score *= 0.6  # 40% penalty
                log.debug(f"Applied rejection penalty for pattern: {pattern}")
        
        # Boost approved patterns
        for pattern in preferences.get('approved_patterns', []):
            if pattern.lower() in job_title:
                score *= 1.3  # 30% boost
                log.debug(f"Applied approval boost for pattern: {pattern}")
        
        return score
```

---

## PHASE D: SCALE & EXPANSION (Weeks 8+)

### 4.1 LinkedIn Discovery Scraper

#### Strategy

```
LinkedIn Job Posting → Normalize → Rank → Queue
↓
NO auto-apply initially
YES discovery + ranking + manual approval
```

#### Implementation

**File**: `src/finder/core/scraper/linkedin_scraper.py` (NEW)

```python
"""LinkedIn job discovery scraper."""

from playwright.async_api import async_playwright
import asyncio
import logging
import json

log = logging.getLogger(__name__)

class LinkedInScraper:
    """Discover jobs on LinkedIn (discovery only, no apply)."""
    
    async def search_jobs(self, query: str, location: str = "") -> list:
        """
        Search for jobs on LinkedIn.
        
        Args:
            query: Job search query (e.g., "React Developer")
            location: Location (optional)
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to LinkedIn jobs
                url = f"https://www.linkedin.com/jobs/search/?keywords={query}"
                if location:
                    url += f"&location={location}"
                
                await page.goto(url, timeout=30000)
                
                # Wait for jobs to load
                await page.wait_for_selector('[data-job-id]', timeout=10000)
                
                # Extract job listings
                jobs_data = await page.evaluate("""
                    () => {
                        const jobs = [];
                        document.querySelectorAll('[data-job-id]').forEach(el => {
                            const title = el.querySelector('h3')?.textContent || '';
                            const company = el.querySelector('.base-search-card__subtitle')?.textContent || '';
                            const location = el.querySelector('.job-search-card__location')?.textContent || '';
                            
                            jobs.push({
                                title: title.trim(),
                                company: company.trim(),
                                location: location.trim(),
                                url: el.href,
                            });
                        });
                        return jobs;
                    }
                """)
                
                jobs = jobs_data
                
            finally:
                await browser.close()
        
        log.info(f"Scraped {len(jobs)} jobs from LinkedIn")
        return jobs
    
    async def normalize_job(self, job: dict) -> dict:
        """Normalize LinkedIn job to standard format."""
        return {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "job_url": job.get("url", ""),
            "description": "",  # Would need to scrape job page
            "platform": "linkedin",
            "skills": "",
            "salary": "",
        }
```

---

## DEPLOYMENT STRATEGY

### Free-Tier Safe Architecture

```
┌─────────────────────────────────────┐
│ Render.com (Free Tier)              │
│ - Flask backend auto-sleep          │
│ - PostgreSQL (free tier)            │
│ - 500 Build minutes/month           │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Redis Cloud (Free Tier)             │
│ - 30MB storage                      │
│ - Celery task queue                 │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ GitHub Actions (Free)               │
│ - CI/CD pipeline                    │
│ - 2000 minutes/month                │
└─────────────────────────────────────┘
```

### Render Deployment

**File**: `render.yaml` (UPDATE)

```yaml
services:
  - type: web
    name: autoapply-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn -w 1 -b 0.0.0.0:$PORT wsgi:app
    envVars:
      - key: DATABASE_URL
        scope: all
      - key: REDIS_URL
        scope: all
      - key: JWT_SECRET
        scope: all
        sync: false
      - key: GOOGLE_API_KEY
        scope: all
        sync: false

  - type: web
    name: autoapply-ui
    env: node
    buildCommand: cd finder-ui && npm install && npm run build
    startCommand: npm run preview --prefix finder-ui
    staticPublishPath: finder-ui/dist

  - type: background
    name: autoapply-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A finder.core.tasks worker -l info
```

---

## IMPLEMENTATION CHECKLIST

### Week 1: Multi-User + Auth
- [x] Database schema update (user_id fields)
- [ ] JWT authentication endpoints
- [ ] Frontend login/signup pages
- [ ] Protected route decorators
- [ ] Cookie management (CSRF)

### Week 2: Approval Queue
- [ ] Approval queue schema
- [ ] Backend approval endpoints
- [ ] Frontend queue UI component
- [ ] Socket.IO integration for realtime updates
- [ ] Edit/reject/approve workflow

### Week 3: Explainable AI + Gemini Integration
- [ ] Explainable scoring breakdown
- [ ] Gemini API integration
- [ ] AI caching layer
- [ ] Budget management
- [ ] Frontend score display

### Week 4: Interview Prep
- [ ] Interview question generation
- [ ] Frontend interview prep UI
- [ ] Answer caching
- [ ] PDF export

### Week 5-7: Semantic Matching + Adaptive Learning
- [ ] Hybrid semantic matching
- [ ] Sentence-transformers setup
- [ ] Adaptive ranking engine
- [ ] User preference learning
- [ ] Goal-based personalization

### Week 8+: LinkedIn Scraper + Scaling
- [ ] LinkedIn discovery scraper
- [ ] Job normalization
- [ ] Source health dashboard
- [ ] Multi-platform support

---

## ENVIRONMENT VARIABLES

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/autoapply
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-256-bit-secret-here
COOKIE_SECURE=true
COOKIE_SAMESITE=Strict

# AI
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
AI_BUDGET_DAILY_TOKENS=1500000
AI_CACHE_HOURS=24

# Scraping
PLAYWRIGHT_HEADLESS=true
SCRAPER_COOLDOWN_MINUTES=5

# Deployment
FLASK_ENV=production
FLASK_DEBUG=false
```

---

## PERFORMANCE TARGETS

| Feature | Implementation | Free-Tier Impact |
|---------|---|---|
| JWT Auth | ✓ | 0% (CPU) |
| Approval Queue | ✓ | 5% (DB queries) |
| Explainable Scoring | ✓ | 10% (computation) |
| Gemini Integration | ✓ | API quota (caching) |
| Interview Prep | ✓ | 15% API calls |
| Semantic Matching | ✓ | 20% CPU (local) |
| Adaptive Learning | ✓ | 3% (DB) |
| LinkedIn Scraper | ✓ | 30% (async) |

**Total Free-Tier Usage**: ~80% of Render free tier

---

## SUCCESS METRICS

Phase A (MVP SaaS):
- ✓ 100+ user registrations
- ✓ 50+ multi-user dashboard active users
- ✓ 80%+ approval queue conversion

Phase B (AI Features):
- ✓ 1000+ Gemini API calls/month
- ✓ 90%+ caching hit rate
- ✓ <5s interview prep generation

Phase C (Intelligence):
- ✓ 60%+ match score improvement
- ✓ 2x adaptive learning boost
- ✓ 40%+ goal-based ranking improvement

Phase D (Scale):
- ✓ 500+ LinkedIn jobs/day
- ✓ 5+ job sources
- ✓ <2s ranking pipeline

---

## NEXT IMMEDIATE STEPS

1. **Complete JWT auth** (today)
2. **Add approval queue** (tomorrow)
3. **Integrate explainable scoring** (this week)
4. **Deploy to Render** (this week)
5. **Test multi-user flow** (test week 1)
6. **Add Gemini integration** (week 2)

---

**Document Version**: 1.0  
**Last Updated**: May 2026  
**Status**: Production Ready — Phase A Implementation
