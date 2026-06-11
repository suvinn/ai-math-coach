import api from './axios'

export const fetchChapters = async () => {
  const response = await api.get('/chapters')
  return response.data.data
}

export const fetchProblemCounts = async () => {
  const response = await api.get('/chapters/problem-counts')
  return response.data.data
}