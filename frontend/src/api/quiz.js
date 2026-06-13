import api, { getCsrfToken } from './axios'

export const createQuizSession = async ({
  chapter_major,
  chapter_middle,
  chapter_minor,
  problem_count,
}) => {
  await getCsrfToken()

  const payload = {
    chapter_major,
    chapter_middle,
    problem_count,
  }

  if (chapter_minor) {
    payload.chapter_minor = chapter_minor
  }

  const response = await api.post('/quiz/sessions', payload)
  return response.data.data
}

export const fetchQuizProblems = async (sessionId) => {
  const response = await api.get(`/quiz/sessions/${sessionId}/problems`)
  return response.data.data
}

export const submitQuizAnswers = async (sessionId, answers) => {
  await getCsrfToken()

  const response = await api.post(`/quiz/sessions/${sessionId}/submit`, {
    answers,
  })

  return response.data.data
}