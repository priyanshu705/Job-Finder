// src/api.js - AutoApply AI API client
import axios from 'axios'

const DEFAULT_PROD_API_URL = 'https://autoapply-ai-backend.onrender.com/api'
const configuredApiUrl =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  ''

const BASE_URL = (configuredApiUrl || (import.meta.env.PROD ? DEFAULT_PROD_API_URL : '/api'))
  .replace(/\/+$/, '')

const TIMEOUT_DEFAULT = 15_000
const TIMEOUT_MUTATION = 20_000
const TIMEOUT_CYCLE = 30_000

const http = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT_DEFAULT,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  res => res.data,
  err => {
    const isTimeout = (
      err.code === 'ECONNABORTED' ||
      err.message?.toLowerCase().includes('timeout')
    )
    const isNetwork = !err.response && !isTimeout

    let msg
    if (isTimeout) {
      msg = 'Server is waking up - please wait a moment and try again'
    } else if (isNetwork) {
      msg = 'Backend unavailable — check your connection'
    } else {
      // Prefer the JSON error field from our Flask handlers
      msg = err.response?.data?.error
         || err.response?.data?.message
         || err.message
         || 'Unknown error'
    }

    const error = new Error(msg)
    error.isTimeout = isTimeout
    error.isNetwork = isNetwork
    error.status = err.response?.status
    return Promise.reject(error)
  }
)

const t = (ms) => ({ timeout: ms })

export const api = {
  status: () => http.get('/status'),
  health: () => http.get('/health', t(8_000)),
  agentStatus: () => http.get('/agent/status'),

  runCycle: () => http.post('/agent/run', null, t(TIMEOUT_CYCLE)),

  queue: (p = {}) => http.get('/queue', {
    params: {
      status: p.status || '',
      limit: p.limit || 100,
      offset: p.offset || 0,
      sort: p.sort || 'priority',
      q: p.q || '',
      min_score: p.min_score || '',
      company: p.company || '',
    },
  }),

  statsDaily: (days = 30) => http.get('/stats/daily', { params: { days } }),
  statsSummary: () => http.get('/stats/summary'),
  statsOverview: () => http.get('/stats/overview'),

  goals: () => http.get('/goals'),
  addGoal: (g) => http.post('/goals', g, t(TIMEOUT_MUTATION)),
  deleteGoal: (id) => http.delete(`/goals/${id}`, t(TIMEOUT_MUTATION)),

  companies: () => http.get('/companies'),
  insights: () => http.get('/insights'),

  controls: () => http.get('/controls'),
  setControl: (key, value) => http.post('/controls', { key, value }, t(TIMEOUT_MUTATION)),

  activity: (limit = 30) => http.get('/activity', { params: { limit } }),

  pause: () => http.post('/actions/pause', null, t(TIMEOUT_MUTATION)),
  resume: () => http.post('/actions/resume', null, t(TIMEOUT_MUTATION)),
  reset: () => http.post('/actions/reset', null, t(TIMEOUT_MUTATION)),
  scrape: () => http.post('/actions/scrape', null, t(TIMEOUT_MUTATION)),
  match: () => http.post('/actions/match', null, t(TIMEOUT_MUTATION)),
  rank: () => http.post('/actions/rank', null, t(TIMEOUT_MUTATION)),

  updateJobStatus: (id, status) => http.post(`/jobs/${id}/status`, { status }, t(TIMEOUT_MUTATION)),
  updateFeedback: (id, fb) => http.post(`/jobs/${id}/feedback`, { feedback: fb }, t(TIMEOUT_MUTATION)),

  seedDemo: () => http.post('/demo/seed', null, t(TIMEOUT_MUTATION)),

  recordOutcome: (d) => http.post('/outcomes', d, t(TIMEOUT_MUTATION)),

  // Resume management
  getResume: () => http.get('/resume'),
  uploadResume: (formData) => http.post('/resume', formData, {
    ...t(30_000),
    headers: { 'Content-Type': 'multipart/form-data' },
  }),

  // Assistant data & queue repair
  generateAssistant: () => http.post('/actions/generate-assistant', null, t(TIMEOUT_MUTATION)),
  resetPending:      () => http.post('/actions/reset-pending',      null, t(TIMEOUT_MUTATION)),
}

