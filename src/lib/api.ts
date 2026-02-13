import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL as string | undefined

export const api = axios.create({
  baseURL: baseURL || 'http://localhost:8000',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fd_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
