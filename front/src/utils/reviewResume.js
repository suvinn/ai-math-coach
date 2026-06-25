// 오답 이어풀기 localStorage 키 — 유저 id별로 분리해 계정 전환 시 데이터가 섞이지 않도록 한다.
export function resumeKey(userId) {
  return `reviewLoop_resume:${userId}`
}
