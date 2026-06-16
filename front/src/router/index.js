// 📄 src/api/index.js
import axios from 'axios'

// 세션 쿠키 기반 인증 → withCredentials 필수
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true,
})

// 쿠키에서 값 읽기 (Django csrftoken 쿠키용)
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[2]) : null
}

// 변경 요청(POST/PUT/PATCH/DELETE)에 CSRF 토큰 헤더 부착.
// Django가 발급한 csrftoken 쿠키를 그대로 헤더로 넘긴다.
api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    const token = getCookie('csrftoken')
    if (token) config.headers['X-CSRFToken'] = token
  }
  return config
})

// 응답은 모두 { status, data } 형태 → data만 꺼내 쓰기 편하게 unwrap 헬퍼 제공
export function unwrap(res) {
  return res.data?.data ?? res.data
}

export default api