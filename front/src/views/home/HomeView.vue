<!-- 📄 src/views/home/HomeView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import Toast from '@/components/common/Toast.vue'
import { resumeKey } from '@/utils/reviewResume'
import widnBearMain from '@/assets/images/widn-bear-main.png'

const router = useRouter()
const auth = useAuthStore()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

const userName = ref(auth.user?.name || '')
const streak = ref(0)
const totalSolved = ref(0)
const solvingCount = ref(0)
const diagnosing = ref(false)

const chapters = ref([])
const recommendedUnit = ref(null)

const tips = [
  '매일 30분, 꾸준한 학습이 성적 향상의 지름길이에요!',
  '오답 유형을 반복 풀면 실수가 확 줄어들어요.',
  '취약 유형부터 집중 공략하면 점수가 빠르게 올라요.',
  '퀴즈 후 틀린 문제를 꼭 다시 확인해 보세요.',
]

const todayTip = computed(() => {
  const dayOfWeek = new Date().getDay()
  const idx = dayOfWeek === 0 ? 6 : dayOfWeek - 1
  return tips[idx % tips.length]
})

const heroTitle = computed(() => {
  if (streak.value === 0) return '오늘도 힘내볼까요?'
  if (streak.value === 1) return '오늘도 좋은 흐름으로 시작해볼까요?'
  return `${streak.value}일째 이어온 흐름, 오늘도 같이 가볼까요?`
})

const heroSubtitle = computed(() => {
  if (totalSolved.value > 0) {
    return `지금까지 ${totalSolved.value}문제를 풀었고, 풀이 중인 유형은 ${solvingCount.value}개예요.`
  }
  return '위든이가 오늘 학습도 옆에서 함께할게요.'
})

const resumeData = computed(() => {
  if (!auth.user?.id) return null

  try {
    const raw = localStorage.getItem(resumeKey(auth.user.id))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
})

const resumeProgress = computed(() => {
  if (!resumeData.value) return null

  const total = resumeData.value.reviewSubtypes?.length || 0
  const done = resumeData.value.resumeFromIdx || 0

  if (!total) return null
  return { done, total }
})

function pickRecommendedUnit(chapterList) {
  if (!chapterList?.length) return null

  const major = chapterList[Math.floor(Math.random() * chapterList.length)]
  if (!major?.chapter_middles?.length) return null

  const middle = major.chapter_middles[Math.floor(Math.random() * major.chapter_middles.length)]

  return {
    chapter_major: major.chapter_major,
    chapter_middle: middle.chapter_middle,
  }
}

onMounted(async () => {
  try {
    const [dashData, chData] = await Promise.all([
      api.get('/users/me/dashboard').then(unwrap),
      api.get('/chapters').then(unwrap),
    ])

    userName.value = dashData?.user?.name || userName.value
    streak.value = dashData?.streak ?? 0
    totalSolved.value = dashData?.total_solved ?? 0
    solvingCount.value = dashData?.solving_count ?? 0
    chapters.value = chData || []
    recommendedUnit.value = pickRecommendedUnit(chData || [])
  } catch {
    // 대시보드 호출에 실패해도 홈 화면 기본 UI는 유지
  }
})

async function startDiagnosis() {
  if (diagnosing.value) return

  diagnosing.value = true

  try {
    const res = await quiz.createAndLoad({ mode: 'diagnosis', problem_count: 10 })

    if (!res.problems.length) {
      showToast('출제 가능한 문제가 없어요', 'negative', 'circle-exclamation')
      diagnosing.value = false
      return
    }

    router.push('/quiz/play')
  } catch {
    showToast('진단을 시작하지 못했어요', 'negative', 'circle-exclamation')
    diagnosing.value = false
  }
}

function goTodayRec() {
  const rec = recommendedUnit.value

  router.push({
    path: '/quiz/setup',
    query: {
      mode: 'today',
      t: Date.now(),
      ...(rec && {
        major: rec.chapter_major,
        middle: rec.chapter_middle,
      }),
    },
  })
}

function goResume() {
  if (!resumeData.value) return

  quiz.parentSessionId = resumeData.value.parentSessionId
  quiz.reviewSubtypes = resumeData.value.reviewSubtypes
  quiz.reviewSubtypeIdx = resumeData.value.resumeFromIdx

  router.push('/review/play')
}
</script>

<template>
  <SidebarShell tab="home">
    <Toast :toast="toast" />

    <div class="page home-page">
      <section class="home-hero">
        <div class="hero-copy">
          <p class="hero-greeting">안녕하세요, {{ userName || '학생' }}님</p>

          <h1 class="hero-title">
            {{ heroTitle }}
          </h1>

          <p class="hero-subtitle">
            {{ heroSubtitle }}
          </p>
        </div>

        <div class="hero-mascot" aria-hidden="true">
          <img :src="widnBearMain" alt="" />
        </div>
      </section>

      <section class="home-main-grid">
        <article class="diagnosis-card">
          <div class="diagnosis-main">
            <div class="diagnosis-content">
              <h2>AI 빠른 진단</h2>

              <p>
                10문제로 내 취약 유형을 찾고,<br />
                전체 단원에서 골고루 출제해 약점을 분석해요.
              </p>

              <WdsButton
                class="diagnosis-button"
                variant="primary"
                size="medium"
                icon-right="arrow-right"
                :disabled="diagnosing"
                @click="startDiagnosis"
              >
                {{ diagnosing ? '준비 중…' : '진단 시작하기' }}
              </WdsButton>
            </div>

            <div class="diagnosis-visual" aria-hidden="true">
              <div class="chart-card">
                <div class="chart-line line-short"></div>
                <div class="chart-line"></div>
                <div class="chart-bars">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
              <div class="magnifier"></div>
            </div>
          </div>

          <div class="diagnosis-meta">
            <span>
              <WdsIcon name="file-text" :size="14" />
              10문제
            </span>
            <i></i>
            <span>
              <WdsIcon name="clock" :size="14" />
              약 15분 소요
            </span>
            <i></i>
            <span>
              <WdsIcon name="check" :size="14" />
              즉시 결과 확인
            </span>
          </div>
        </article>

        <div class="side-stack">
          <article class="action-card action-card-primary">
            <div class="action-content">
              <h3>오늘의 추천 학습</h3>
              <p>
                풀이 중인 유형을 기준으로<br />
                바로 퀴즈를 시작해 보세요.
              </p>
            </div>

            <WdsButton
              class="action-button"
              variant="primary"
              size="medium"
              icon-right="arrow-right"
              @click="goTodayRec"
            >
              퀴즈 설정하기
            </WdsButton>

            <div v-if="recommendedUnit" class="recommend-box">
              <span>추천 단원</span>
              <strong>
                {{ recommendedUnit.chapter_major }} &rsaquo; {{ recommendedUnit.chapter_middle }}
              </strong>
            </div>
          </article>

          <article v-if="resumeData" class="action-card">
            <div class="action-content">
              <h3>오답 이어풀기</h3>
              <p>
                {{ resumeData.reviewSubtypes[resumeData.resumeFromIdx]?.problemSubtype }}
                외 {{ resumeData.reviewSubtypes.length - resumeData.resumeFromIdx }}개 남음
              </p>

              <div v-if="resumeProgress" class="resume-progress">
                <div class="resume-track">
                  <div
                    class="resume-fill"
                    :style="{ width: (resumeProgress.done / resumeProgress.total * 100) + '%' }"
                  />
                </div>
                <span>{{ resumeProgress.done }}/{{ resumeProgress.total }} 세트</span>
              </div>
            </div>

            <WdsButton
              class="action-button"
              variant="primary"
              size="medium"
              icon-right="arrow-right"
              @click="goResume"
            >
              이어서 풀기
            </WdsButton>
          </article>

          <article v-else class="action-card action-card-muted">
            <div class="action-content">
              <h3>오답 이어풀기</h3>
              <p>진행 중인 오답 루프가 없어요.</p>
            </div>
          </article>
        </div>
      </section>

      <div class="tip-row">
        <div class="tip-icon">
          <WdsIcon name="bulb" :size="16" />
        </div>
        <span class="tip-text">
          <strong>학습 팁</strong>
          {{ todayTip }}
        </span>
      </div>
    </div>
  </SidebarShell>
</template>

<style scoped>
.home-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 0 48px;
}

.home-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: center;
  min-height: 230px;
  padding: 24px 42px;
  overflow: hidden;
  border: 1px solid #dbeafe;
  border-radius: 28px;
  background:
    radial-gradient(circle at 92% 18%, rgba(99, 102, 241, 0.14), transparent 28%),
    linear-gradient(135deg, #eff6ff 0%, #f8fbff 58%, #eef2ff 100%);
  box-shadow: 0 20px 45px rgba(37, 99, 235, 0.08);
}

.hero-greeting {
  margin: 0;
  font: var(--weight-medium) 16px/1.45 var(--font-sans);
  color: var(--label-assistive);
}

.hero-title {
  margin: 8px 0 0;
  font: var(--weight-bold) 31px/1.35 var(--font-sans);
  letter-spacing: -0.035em;
  color: #172554;
}

.hero-subtitle {
  margin: 14px 0 0;
  font: var(--weight-medium) 16px/1.6 var(--font-sans);
  color: #64748b;
}

.hero-mascot {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 180px;
}

.hero-mascot img {
  width: 260px;
  filter: drop-shadow(0 18px 24px rgba(37, 99, 235, 0.16));
}

.home-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
  gap: 20px;
  margin-top: 22px;
}

.diagnosis-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 300px;
  overflow: hidden;
  padding: 30px;
  border-radius: 24px;
  color: #fff;
  background:
    radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.24), transparent 26%),
    linear-gradient(145deg, #2563eb 0%, #60a5fa 100%);
  box-shadow: 0 22px 42px rgba(37, 99, 235, 0.18);
}

.diagnosis-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 26px;
  flex: 1;
}

.diagnosis-content {
  position: relative;
  z-index: 2;
  flex: 1;
  min-width: 0;
}

.diagnosis-card h2 {
  margin: 0;
  font: var(--weight-bold) 30px/1.35 var(--font-sans);
  letter-spacing: -0.035em;
}

.diagnosis-card p {
  margin: 14px 0 0;
  font: var(--weight-medium) 17px/1.7 var(--font-sans);
  color: rgba(255, 255, 255, 0.86);
}

.diagnosis-button {
  margin-top: 28px;
  background: #fff !important;
  color: #2563eb !important;
  border-color: #fff !important;
}

.diagnosis-visual {
  position: relative;
  flex: 0 0 170px;
  width: 170px;
  height: 170px;
  opacity: 0.9;
}

.chart-card {
  position: absolute;
  inset: 6px 38px 22px 6px;
  padding: 24px 18px;
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.18);
}

.chart-line {
  width: 70%;
  height: 5px;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.38);
}

.line-short {
  width: 48%;
  margin-top: 0;
  background: rgba(255, 255, 255, 0.55);
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 9px;
  height: 60px;
  margin-top: 24px;
}

.chart-bars span {
  width: 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.chart-bars span:nth-child(1) {
  height: 28px;
}

.chart-bars span:nth-child(2) {
  height: 48px;
}

.chart-bars span:nth-child(3) {
  height: 36px;
}

.magnifier {
  position: absolute;
  right: 2px;
  bottom: 12px;
  width: 66px;
  height: 66px;
  border: 4px solid rgba(255, 255, 255, 0.72);
  border-radius: 50%;
}

.magnifier::after {
  content: '';
  position: absolute;
  right: -16px;
  bottom: -10px;
  width: 30px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  transform: rotate(45deg);
}

.diagnosis-meta {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.9);
  font: var(--weight-bold) 14px/1 var(--font-sans);
}

.diagnosis-meta span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.diagnosis-meta i {
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.28);
}

.side-stack {
  display: grid;
  gap: 20px;
}

.action-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  min-height: 140px;
  padding: 24px;
  border: 1px solid #dbeafe;
  border-radius: 22px;
  background: rgba(239, 246, 255, 0.72);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
  text-align: left;
}

.action-card-primary {
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    'content button'
    'recommend recommend';
  column-gap: 18px;
  row-gap: 10px;
  align-items: center;
  min-height: 132px;
  padding: 22px 24px;
  background: linear-gradient(135deg, #eff6ff 0%, #f8fbff 100%);
}

.action-card-primary .action-content {
  grid-area: content;
}

.action-card-primary .action-button {
  grid-area: button;
  align-self: start;
  transform: translateY(-2px);
}

.action-card-primary .recommend-box {
  grid-area: recommend;
  justify-self: stretch;
  width: auto;
  max-width: none;
  margin-top: 0;
  box-sizing: border-box;
}

.action-card-muted {
  grid-template-columns: 1fr;
  align-items: flex-start;
  opacity: 0.68;
}

.action-content {
  min-width: 0;
  text-align: left;
}

.action-content h3 {
  margin: 0;
  font: var(--weight-bold) 20px/1.35 var(--font-sans);
  letter-spacing: -0.02em;
  color: #1e3a8a;
  text-align: left;
}

.action-content p {
  margin: 6px 0 0;
  font: var(--weight-medium) 14px/1.5 var(--font-sans);
  color: #64748b;
  text-align: left;
}

.action-button {
  flex-shrink: 0;
  white-space: nowrap;
}

.recommend-box {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: #fff;
}

.recommend-box span {
  flex-shrink: 0;
  font: var(--weight-medium) 12px/1.2 var(--font-sans);
  color: #94a3b8;
  white-space: nowrap;
}

.recommend-box strong {
  min-width: 0;
  overflow: hidden;
  color: #2563eb;
  font: var(--weight-bold) 13px/1.35 var(--font-sans);
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: keep-all;
}

.resume-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.resume-track {
  flex: 1;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #dbeafe;
}

.resume-fill {
  height: 100%;
  border-radius: inherit;
  background: #2563eb;
}

.resume-progress span {
  font: var(--weight-medium) 12px/1 var(--font-sans);
  color: #64748b;
}

.tip-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 22px;
  padding: 16px 20px;
  border: 1px solid #bfdbfe;
  border-radius: 18px;
  background: #eff6ff;
}

.tip-icon {
  display: flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #2563eb;
  background: #dbeafe;
}

.tip-text {
  color: #64748b;
  font: var(--weight-medium) 15px/1.5 var(--font-sans);
}

.tip-text strong {
  margin-right: 8px;
  color: #1e40af;
}

@media (max-width: 1180px) {
  .home-page {
    max-width: 920px;
  }

  .home-hero {
    grid-template-columns: 1fr 280px;
  }

  .home-main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .home-page {
    padding: 22px 0 36px;
  }

  .home-hero {
    grid-template-columns: 1fr;
    padding: 28px 24px;
  }

  .hero-mascot {
    display: none;
  }

  .hero-title {
    font-size: 24px;
  }

  .diagnosis-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .diagnosis-card {
    min-height: auto;
  }

  .diagnosis-visual {
    display: none;
  }

  .diagnosis-meta {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .action-card {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .action-card-primary {
    grid-template-columns: 1fr;
    grid-template-areas:
      'content'
      'button'
      'recommend';
  }

  .action-card-primary .action-button {
    transform: none;
  }

  .action-button {
    width: 100%;
  }

  .recommend-box {
    grid-template-columns: 1fr;
    gap: 5px;
  }

  .recommend-box strong {
    white-space: normal;
  }
}
</style>