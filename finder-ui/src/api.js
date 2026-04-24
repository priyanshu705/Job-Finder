// src/api.js — Finder V6 enhanced API client (Axios)
import axios from 'axios'

const http = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  r => r.data,
  err => {
    const msg = err.response?.data?.error || err.message || 'Network error'
    return Promise.reject(new Error(msg))
  }
)

export const api = {
  // Core
  status:       ()           => http.get('/status'),
  health:       ()           => http.get('/health'),
  // Queue
  queue:        (p = {})    => http.get('/queue', { params: { status: p.status || '', limit: p.limit || 100, offset: p.offset || 0, sort: p.sort || 'priority', q: p.q || '', min_score: p.min_score || '', company: p.company || '' } }),
  jobs:         (p = {})    => http.get('/jobs', { params: { limit: p.limit || 50, offset: p.offset || 0, q: p.q || '' } }),
  // Stats
  statsDaily:   (days = 30) => http.get('/stats/daily',   { params: { days } }),
  statsSummary: ()           => http.get('/stats/summary'),
  statsOverview:()           => http.get('/stats/overview'),
  // Goals
  goals:        ()           => http.get('/goals'),
  addGoal:      (g)          => http.post('/goals', g),
  deleteGoal:   (id)         => http.delete(`/goals/${id}`),
  // Intelligence
  companies:    ()           => http.get('/companies'),
  insights:     ()           => http.get('/insights'),
  // Controls
  controls:     ()           => http.get('/controls'),
  setControl:   (key, value) => http.post('/controls', { key, value }),
  // Activity
  activity:     (limit = 30) => http.get('/activity', { params: { limit } }),
  cycleStatus:  ()           => http.get('/cycle-status'),
  actionStatus: ()           => http.get('/actions/status'),
  // Actions
  pause:        ()           => http.post('/actions/pause'),
  resume:       ()           => http.post('/actions/resume'),
  reset:        ()           => http.post('/actions/reset'),
  scrape:       ()           => http.post('/actions/scrape'),
  match:        ()           => http.post('/actions/match'),
  rank:         ()           => http.post('/actions/rank'),
  cycle:        (params = {})=> http.post('/actions/cycle', params),
  // Outcomes
  recordOutcome:(d)          => http.post('/outcomes', d),
  // Assistant
  updateJobStatus: (id, status) => http.post(`/jobs/${id}/status`, { status }),
  updateFeedback:  (id, fb)     => http.post(`/jobs/${id}/feedback`, { feedback: fb }),
  seedDemo:        ()           => http.post('/demo/seed'),
  runCycle:        ()           => http.post('/agent/run'),
  agentStatus:     ()           => http.get('/agent/status'),
}
