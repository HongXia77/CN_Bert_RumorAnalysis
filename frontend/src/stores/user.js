import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api from '@/api/client'

const STORAGE_KEYS = {
  token: 'access_token',
  profile: 'user_info',
  history: 'prediction_history',
}

const readJson = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

const writeJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
}

const buildPredictionSummary = (rumorProbability) => {
  const safeProbability = Number.isFinite(Number(rumorProbability))
    ? Math.min(Math.max(Number(rumorProbability), 0), 1)
    : 0

  if (safeProbability >= 0.75) {
    return {
      verdict: '高度疑似谣言',
      risk_level: 'high',
      rumor_probability: safeProbability,
      credible_probability: 1 - safeProbability,
      label: 'rumor',
    }
  }

  if (safeProbability >= 0.45) {
    return {
      verdict: '存在较高风险，建议继续核查',
      risk_level: 'medium',
      rumor_probability: safeProbability,
      credible_probability: 1 - safeProbability,
      label: safeProbability >= 0.5 ? 'rumor' : 'normal',
    }
  }

  return {
    verdict: '当前更接近真实或中性信息',
    risk_level: 'low',
    rumor_probability: safeProbability,
    credible_probability: 1 - safeProbability,
    label: 'normal',
  }
}

const normalizeHistoryRecord = (record = {}) => {
  const fallbackProbability = record.predicted_label === 1 ? 1 : 0
  const summary = buildPredictionSummary(record.rumor_probability ?? fallbackProbability)

  return {
    id: record.id ?? record.upload_id ?? `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    upload_id: record.upload_id ?? record.id ?? null,
    text: record.text ?? record.upload_content ?? '',
    createdAt: record.createdAt ?? record.upload_time ?? new Date().toISOString(),
    label: record.label ?? summary.label,
    verdict: record.verdict ?? summary.verdict,
    risk_level: record.risk_level ?? summary.risk_level,
    rumor_probability: Number(record.rumor_probability ?? summary.rumor_probability),
    credible_probability: Number(record.credible_probability ?? summary.credible_probability),
    base_model_probability: Number(record.base_model_probability ?? 0),
    event_match_probability: Number(record.event_match_probability ?? 0),
    predicted_label: record.predicted_label ?? (summary.label === 'rumor' ? 1 : 0),
    upload_status: record.upload_status ?? record.status ?? '已合并',
    merge_strategy: record.merge_strategy ?? null,
    merge_confidence: record.merge_confidence ?? null,
    merge_reason: record.merge_reason ?? null,
    merged_rumor_id: record.merged_rumor_id ?? null,
    candidate_rumor_id: record.candidate_rumor_id ?? null,
    related_rumors: Array.isArray(record.related_rumors) ? record.related_rumors : [],
  }
}

const clearLegacyHistoryCache = () => {
  localStorage.removeItem(STORAGE_KEYS.history)
}

export const useUserStore = defineStore('user', () => {
  const token = ref('')
  const profile = ref(null)
  const predictionHistory = ref([])
  const initialized = ref(false)
  const historyLoaded = ref(false)
  const historyLoading = ref(false)

  const role = computed(() => profile.value?.role || 'guest')
  const isAdmin = computed(() => role.value === 'admin')
  const isLoggedIn = computed(() => Boolean(token.value && profile.value?.user_id))

  const persistSession = () => {
    if (token.value) {
      localStorage.setItem(STORAGE_KEYS.token, token.value)
    } else {
      localStorage.removeItem(STORAGE_KEYS.token)
    }

    if (profile.value) {
      writeJson(STORAGE_KEYS.profile, profile.value)
    } else {
      localStorage.removeItem(STORAGE_KEYS.profile)
    }
  }

  const resetHistoryState = () => {
    predictionHistory.value = []
    historyLoaded.value = false
    historyLoading.value = false
  }

  const bootstrap = () => {
    if (initialized.value) return

    token.value = localStorage.getItem(STORAGE_KEYS.token) || ''
    profile.value = readJson(STORAGE_KEYS.profile, null)
    resetHistoryState()
    clearLegacyHistoryCache()
    initialized.value = true
  }

  const setSession = ({ access_token, data }) => {
    token.value = access_token || ''
    profile.value = data || null
    persistSession()
    resetHistoryState()
    clearLegacyHistoryCache()
  }

  const updateProfile = (nextProfile) => {
    profile.value = nextProfile ? { ...(profile.value || {}), ...nextProfile } : null
    persistSession()
  }

  const clearSession = () => {
    token.value = ''
    profile.value = null
    persistSession()
    resetHistoryState()
    clearLegacyHistoryCache()
  }

  const fetchCurrentUser = async () => {
    bootstrap()

    if (!token.value) return null

    const response = await api.get('/me')
    updateProfile(response.data.data)
    return response.data.data
  }

  const fetchPredictionHistory = async ({ force = false, limit = 100 } = {}) => {
    bootstrap()

    if (!token.value) {
      resetHistoryState()
      return []
    }

    if (historyLoaded.value && !force) {
      return predictionHistory.value
    }

    historyLoading.value = true
    try {
      const response = await api.get('/history', { params: { limit } })
      predictionHistory.value = (response.data.data || []).map(normalizeHistoryRecord)
      historyLoaded.value = true
      return predictionHistory.value
    } finally {
      historyLoading.value = false
    }
  }

  const recordPrediction = (payload) => {
    const storage = payload?.storage || {}
    const nextRecord = normalizeHistoryRecord({
      ...payload,
      id: storage.upload_id ?? payload?.id,
      upload_id: storage.upload_id ?? payload?.upload_id,
      createdAt: storage.upload_time ?? payload?.createdAt,
      upload_status: storage.upload_status ?? payload?.upload_status,
      merge_strategy: storage.merge_strategy ?? payload?.merge_strategy,
      merge_confidence: storage.merge_confidence ?? payload?.merge_confidence,
      merge_reason: storage.merge_reason ?? payload?.merge_reason,
      merged_rumor_id: storage.rumor_id ?? payload?.merged_rumor_id,
      candidate_rumor_id: storage.candidate_rumor_id ?? payload?.candidate_rumor_id,
    })

    predictionHistory.value = [
      nextRecord,
      ...predictionHistory.value.filter((item) => item.id !== nextRecord.id),
    ].slice(0, 100)
    historyLoaded.value = true
    return nextRecord
  }

  const deletePredictionRecord = async (recordId) => {
    await api.delete(`/history/${recordId}`)
    predictionHistory.value = predictionHistory.value.filter((item) => item.id !== recordId)
  }

  const clearPredictionHistory = async () => {
    await api.delete('/history')
    predictionHistory.value = []
    historyLoaded.value = true
  }

  return {
    token,
    profile,
    predictionHistory,
    role,
    isAdmin,
    isLoggedIn,
    historyLoaded,
    historyLoading,
    bootstrap,
    setSession,
    updateProfile,
    clearSession,
    fetchCurrentUser,
    fetchPredictionHistory,
    recordPrediction,
    deletePredictionRecord,
    clearPredictionHistory,
  }
})
