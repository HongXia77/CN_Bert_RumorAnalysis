import axios from 'axios'

const apiBaseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/user'

const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 15000,
})

const getApiOrigin = () => {
  const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000'
  return new URL(apiBaseURL, fallbackOrigin).origin
}

export const resolveAssetUrl = (assetPath, version = '') => {
  if (!assetPath) {
    return ''
  }

  if (assetPath.startsWith('data:') || assetPath.startsWith('blob:')) {
    return assetPath
  }

  const origin = getApiOrigin()
  const targetUrl = /^(https?:)?\/\//i.test(assetPath)
    ? new URL(assetPath, origin)
    : new URL(assetPath.startsWith('/') ? `${origin}${assetPath}` : `${origin}/${assetPath}`)

  if (version) {
    targetUrl.searchParams.set('v', String(version))
  }

  return targetUrl.toString()
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export default api
