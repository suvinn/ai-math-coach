import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true,
})

export const getCsrfToken = async () => {
  const response = await api.get('/auth/csrf')

  const csrfToken =
    response.data.csrfToken ||
    response.data.data?.csrfToken ||
    response.data.csrf_token ||
    response.data.data?.csrf_token

  if (csrfToken) {
    api.defaults.headers.common['X-CSRFToken'] = csrfToken
  }

  return csrfToken
}

export default api