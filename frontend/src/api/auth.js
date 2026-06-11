import api, { getCsrfToken } from './axios'

export const register = async ({ username, password, name }) => {
  await getCsrfToken()

  const response = await api.post('/auth/register', {
    username,
    password,
    name,
  })

  return response.data.data
}

export const login = async ({ username, password }) => {
  await getCsrfToken()

  const response = await api.post('/auth/login', {
    username,
    password,
  })

  return response.data.data
}

export const logout = async () => {
  await getCsrfToken()

  const response = await api.post('/auth/logout')
  return response.data
}

export const fetchMe = async () => {
  const response = await api.get('/auth/me')
  return response.data.data
}