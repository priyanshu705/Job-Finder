// src/hooks.js — Real-time polling hooks with fetch-lock and debounce
import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from './api'

// ── Toast ────────────────────────────────────────────────────────────────────
export function useToast() {
  const [toasts, setToasts] = useState([])
  const toast = useCallback((msg, type = 'info') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }, [])
  return { toasts, toast }
}

// ── Live polling hook — prevents concurrent fetches, tracks last-updated ─────
export function useLive(fetcher, intervalMs = 4000) {
  const [data,       setData]       = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const fetchingRef  = useRef(false)
  const intervalRef  = useRef(null)
  const mountedRef   = useRef(true)

  const load = useCallback(async () => {
    if (fetchingRef.current) return   // ← prevent concurrent fetches
    fetchingRef.current = true
    try {
      const d = await fetcher()
      if (!mountedRef.current) return
      setData(d)
      setError(null)
      setLastUpdate(Date.now())
    } catch (e) {
      if (mountedRef.current) setError(e.message)
    } finally {
      fetchingRef.current = false
      if (mountedRef.current) setLoading(false)
    }
  }, [fetcher])

  useEffect(() => {
    mountedRef.current = true
    load()
    intervalRef.current = setInterval(load, intervalMs)
    return () => {
      mountedRef.current = false
      clearInterval(intervalRef.current)
    }
  }, [load, intervalMs])

  return { data, loading, error, lastUpdate, reload: load }
}

// ── "Last updated X ago" formatter ───────────────────────────────────────────
export function useRelativeTime(ts) {
  const [label, setLabel] = useState('')
  useEffect(() => {
    if (!ts) return
    const update = () => {
      const sec = Math.floor((Date.now() - ts) / 1000)
      if      (sec < 5)  setLabel('just now')
      else if (sec < 60) setLabel(`${sec}s ago`)
      else               setLabel(`${Math.floor(sec / 60)}m ago`)
    }
    update()
    const t = setInterval(update, 2000)
    return () => clearInterval(t)
  }, [ts])
  return label
}

// ── API action with optimistic UI ────────────────────────────────────────────
export function useAction(toast) {
  const [running, setRunning] = useState({})
  const run = useCallback(async (key, fn, label) => {
    // Optimistic — show running immediately
    setRunning(r => ({...r, [key]: true}))
    try {
      const res = await fn()
      toast(res?.status === 'already_running'
        ? `${label} already running`
        : `${label} started ✓`, 'success')
    } catch(e) {
      toast(`${label} failed: ${e.message}`, 'error')
    } finally {
      setRunning(r => ({...r, [key]: false}))
    }
  }, [toast])
  return { running, run }
}

// ── isNewJob: created in last N minutes ─────────────────────────────────────
export function isNewJob(queuedAt, minutes = 5) {
  if (!queuedAt) return false
  try {
    const d    = new Date(queuedAt.replace(' ', 'T') + (queuedAt.includes('+') ? '' : 'Z'))
    const age  = (Date.now() - d.getTime()) / 60000
    return age <= minutes
  } catch { return false }
}
