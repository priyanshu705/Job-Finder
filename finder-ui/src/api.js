// src/api.js — AutoApply AI API client
// Production-hardened: timeout detection, cold-start messaging, JSON error normalisation
import axios from 'axios'

// ── Base URL ─────────────────────────────────────────────────────────────────
// Dev: Vite proxy rewrites /api → localhost:5000 (via vite.config.js)
// Prod: VITE_API_BASE_URL is set to https://autoapply-ai-backend.onrender.com/api
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// ── Timeout constants ─────────────────────────────────────────────────────────
const TIMEOUT_DEFAULT  = 15_000   // 15 s  — normal requests
const TIMEOUT_MUTATION = 20_000   // 20 s  — POST/DELETE that trigger work
const TIMEOUT_CYCLE    = 30_000   // 30 s  — Run Cycle (Render cold-start can be slow)

// ── Axios instance ───────────────────────────────────────────────────────────
const http = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT_DEFAULT,
  headers: { 'Content-Type': 'application/json' },
})

// ── Response interceptor: normalise all errors to { message } ────────────────
http.interceptors.response.use(
  res => res.data,
  err => {
    // Axios timeout → ECONNABORTED code
    const isTimeout = (
      err.code === 'ECONNABORTED' ||
      err.message?.toLowerCase().includes('timeout')
    )
    // Network failure (backend offline / Render sleeping)
    const isNetwork = !err.response && !isTimeout

    let msg
    if (isTimeout) {
      msg = 'Server is waking up — please wait a moment and try again'
    } else if (isNetwork) {
      msg = 'Backend unavailable — check your connection'
    } else {
      // Prefer the JSON error field from our Flask handlers
      msg = err.response?.data?.error
         || err.response?.data?.message
         || err.message
         || 'Unknown error'
    }

    // Tag the error so callers can branch on type if needed
    const error    = new Error(msg)
    error.isTimeout = isTimeout
    error.isNetwork = isNetwork
    error.status   = err.response?.status
    return Promise.reject(error)
  }
)

// ── Tiny helper: create a per-request timeout config ─────────────────────────
const t = (ms) => ({ timeout: ms })

// ── API surface ───────────────────────────────────────────────────────────────
export const api = {
  // ── Core status
  status:      () => http.get('/status'),
  health:      () => http.get('/health', t(8_000)),   // health should be fast
  agentStatus: () => http.get('/agent/status'),

  // ── Agent lifecycle (longer timeout — Render free tier cold-starts)
  runCycle:    () => http.post('/agent/run',  null, t(TIMEOUT_CYCLE)),

  // ── Queue
  queue: (p = {}) => http.get('/queue', {
    params: {
      status:    p.status    || '',
      limit:     p.limit     || 100,
      offset:    p.offset    || 0,
      sort:      p.sort      || 'priority',
      q:         p.q         || '',
      min_score: p.min_score || '',
      company:   p.company   || '',
    },
  }),

  // ── Stats
  statsDaily:   (days = 30) => http.get('/stats/daily',   { params: { days } }),
  statsSummary: ()           => http.get('/stats/summary'),
  statsOverview:()           => http.get('/stats/overview'),

  // ── Goals
  goals:      ()  => http.get('/goals'),
  addGoal:    (g) => http.post('/goals', g, t(TIMEOUT_MUTATION)),
  deleteGoal: (id)=> http.delete(`/goals/${id}`, t(TIMEOUT_MUTATION)),

  // ── Intelligence
  companies: () => http.get('/companies'),
  insights:  () => http.get('/insights'),

  // ── Agent controls
  controls:   ()           => http.get('/controls'),
  setControl: (key, value) => http.post('/controls', { key, value }, t(TIMEOUT_MUTATION)),

  // ── Activity
  activity: (limit = 30) => http.get('/activity', { params: { limit } }),

  // ── Actions (mutations — longer timeout)
  pause:  () => http.post('/actions/pause',  null, t(TIMEOUT_MUTATION)),
  resume: () => http.post('/actions/resume', null, t(TIMEOUT_MUTATION)),
  reset:  () => http.post('/actions/reset',  null, t(TIMEOUT_MUTATION)),
  scrape: () => http.post('/actions/scrape', null, t(TIMEOUT_MUTATION)),
  match:  () => http.post('/actions/match',  null, t(TIMEOUT_MUTATION)),
  rank:   () => http.post('/actions/rank',   null, t(TIMEOUT_MUTATION)),

  // ── Job management
  updateJobStatus: (id, status) => http.post(`/jobs/${id}/status`,   { status },          t(TIMEOUT_MUTATION)),
  updateFeedback:  (id, fb)     => http.post(`/jobs/${id}/feedback`, { feedback: fb },    t(TIMEOUT_MUTATION)),

  // ── Demo
  seedDemo: () => http.post('/demo/seed', null, t(TIMEOUT_MUTATION)),

  // ── Outcomes
  recordOutcome: (d) => http.post('/outcomes', d, t(TIMEOUT_MUTATION)),
}
