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
import ReviewResumeBanner from '@/components/review/ReviewResumeBanner.vue'

const router = useRouter()
const auth = useAuthStore()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

const userName = ref(auth.user?.name || '')
const streak = ref(0)
const weeklyActivity = ref([false, false, false, false, false, false, false])
const subtypeMastery = ref([])
const diagnosing = ref(false)

const weekLabels = ['월', '화', '수', '목', '금', '토', '일']
const chapters = ref([])  // [{ chapter_major, chapter_middles: [...] }]

// 학습 팁 — 요일 인덱스(0=월)로 순환
const tips = [
  '매일 30분, 꾸준한 학습이 성적 향상의 지름길이에요!',
  '오답 유형을 반복 풀면 실수가 확 줄어들어요.',
  '취약 유형부터 집중 공략하면 점수가 빠르게 올라요.',
  '퀴즈 후 틀린 문제를 꼭 다시 확인해 보세요.',
]
const todayTip = computed(() => {
  const dayOfWeek = new Date().getDay() // 0=일,1=월,...
  const idx = dayOfWeek === 0 ? 6 : dayOfWeek - 1 // 월=0 기준으로
  return tips[idx % tips.length]
})

// 추천 단원: chapters에서 랜덤 대단원+중단원 뽑기
const recommendedSubtype = computed(() => {
  if (!chapters.value.length) return null
  const major = chapters.value[Math.floor(Math.random() * chapters.value.length)]
  if (!major.chapter_middles?.length) return null
  const middle = major.chapter_middles[Math.floor(Math.random() * major.chapter_middles.length)]
  return {
    chapter_major: major.chapter_major,
    chapter_middle: middle.chapter_middle,
  }
})

// 오답 이어풀기 진행률
const resumeData = computed(() => {
  try {
    const raw = localStorage.getItem('reviewLoop_resume')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
})
const resumeProgress = computed(() => {
  if (!resumeData.value) return null
  const total = resumeData.value.reviewSubtypes.length
  const done = resumeData.value.resumeFromIdx
  return { done, total }
})

onMounted(async () => {
  try {
    const [dashData, chData] = await Promise.all([
      api.get('/users/me/dashboard').then(unwrap),
      api.get('/chapters').then(unwrap),
    ])
    userName.value = dashData?.user?.name || userName.value
    streak.value = dashData?.streak ?? 0
    weeklyActivity.value = dashData?.weekly_activity ?? weeklyActivity.value
    subtypeMastery.value = dashData?.subtype_mastery ?? []
    chapters.value = chData || []
  } catch {
    // 실패해도 화면은 그대로
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
  router.push({ path: '/quiz/setup', query: { mode: 'today' } })
}

function goResume() {
  if (!resumeData.value) return
  quiz.parentSessionId  = resumeData.value.parentSessionId
  quiz.reviewSubtypes   = resumeData.value.reviewSubtypes
  quiz.reviewSubtypeIdx = resumeData.value.resumeFromIdx
  router.push('/review/play')
}
</script>

<template>
  <SidebarShell tab="home">
    <Toast :toast="toast" />

    <div class="page">
      <!-- 헤드 -->
      <div class="page-head">
        <div class="wds-body-2 assistive head-greeting">안녕하세요, {{ userName || '학생' }}님</div>
        <div class="title home-headline">
          <template v-if="streak === 0">오늘 <span class="accent">첫 학습</span>을 시작해볼까요!</template>
          <template v-else-if="streak === 1">오늘 <span class="accent">첫 번째</span> 연속 학습 중이에요!</template>
          <template v-else>오늘은 <span class="accent">{{ streak }}일째</span> 연속 학습 중이에요!</template>
        </div>
      </div>

      <!-- 카드 그리드 -->
      <div class="card-grid-home">
        <!-- AI 빠른 진단 — 왼쪽 큰 카드 -->
        <div class="diag-card">
          <div class="diag-top">
            <div class="diag-inner">
              <div class="diag-title">AI 빠른 진단</div>
              <div class="diag-body">
                10문제로 내 취약 유형 찾기<br>
                전체 단원에서 골고루 출제해 약점을 분석해요.
              </div>
              <WdsButton class="diag-btn" variant="outlined" size="medium" icon-right="arrow-right" :style="{ width: '135px', background: '#fff', color: '#2563eb', borderColor: '#fff' }" :disabled="diagnosing" @click="startDiagnosis">
                {{ diagnosing ? '준비 중…' : '진단 시작하기' }}
              </WdsButton>
            </div>
            <!-- SVG 일러스트 -->
            <svg class="diag-illust" viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg">
              <!-- 문서 배경 -->
              <rect x="30" y="20" width="90" height="112" rx="12" fill="white" fill-opacity="0.25"/>
              <rect x="30" y="20" width="90" height="112" rx="12" stroke="white" stroke-opacity="0.4" stroke-width="1.5"/>
              <!-- 문서 줄 -->
              <rect x="46" y="42" width="38" height="5" rx="2.5" fill="white" fill-opacity="0.5"/>
              <rect x="46" y="54" width="52" height="4" rx="2" fill="white" fill-opacity="0.35"/>
              <rect x="46" y="64" width="44" height="4" rx="2" fill="white" fill-opacity="0.35"/>
              <!-- 막대 차트 -->
              <rect x="46" y="95" width="10" height="22" rx="3" fill="white" fill-opacity="0.55"/>
              <rect x="61" y="82" width="10" height="35" rx="3" fill="white" fill-opacity="0.75"/>
              <rect x="76" y="88" width="10" height="29" rx="3" fill="white" fill-opacity="0.6"/>
              <rect x="91" y="75" width="10" height="42" rx="3" fill="white" fill-opacity="0.85"/>
              <!-- 돋보기 원 -->
              <circle cx="116" cy="108" r="26" fill="white" fill-opacity="0.15" stroke="white" stroke-opacity="0.6" stroke-width="2.5"/>
              <circle cx="116" cy="108" r="17" fill="white" fill-opacity="0.2"/>
              <!-- 돋보기 손잡이 -->
              <line x1="128" y1="120" x2="142" y2="136" stroke="white" stroke-opacity="0.7" stroke-width="4" stroke-linecap="round"/>
              <!-- 체크 -->
              <circle cx="54" cy="118" r="9" fill="white" fill-opacity="0.25" stroke="white" stroke-opacity="0.5" stroke-width="1.5"/>
              <polyline points="50,118 53,121 59,115" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            </svg>
          </div>
          <!-- 하단 3가지 특징 -->
          <div class="diag-meta">
            <span class="diag-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              10문제
            </span>
            <span class="diag-meta-sep">|</span>
            <span class="diag-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              약 15분 소요
            </span>
            <span class="diag-meta-sep">|</span>
            <span class="diag-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              즉시 결과 확인
            </span>
          </div>
        </div>

        <!-- 오른쪽 2개 카드 -->
        <div class="side-cards">
          <!-- 오늘의 추천 학습 -->
          <div class="side-card">
            <div class="side-card-head">
              <div class="side-card-texts">
                <div class="side-title">오늘의 추천 학습</div>
                <div class="side-sub">단원을 골라 바로 퀴즈를 시작해요.</div>
              </div>
              <WdsButton class="side-btn" variant="primary" size="medium" icon-right="arrow-right" :style="{ width: '135px' }" @click="goTodayRec">
                퀴즈 설정하기
              </WdsButton>
            </div>
            <div v-if="recommendedSubtype" class="rec-unit-row">
              <span class="wds-caption-1 assistive rec-label">추천 단원</span>
              <span class="rec-name">
                <span class="rec-chapter">{{ recommendedSubtype.chapter_major }}</span>
                &rsaquo; {{ recommendedSubtype.chapter_middle }}
              </span>
            </div>
          </div>

          <!-- 오답 이어풀기 -->
          <div v-if="resumeData" class="side-card">
            <div class="side-card-head">
              <div class="side-card-texts">
                <div class="side-title">오답 이어풀기</div>
                <div class="side-sub">
                  {{ resumeData.reviewSubtypes[resumeData.resumeFromIdx]?.problemSubtype }} 외 {{ resumeData.reviewSubtypes.length - resumeData.resumeFromIdx }}개 남음
                </div>
              </div>
              <WdsButton class="side-btn" variant="primary" size="medium" icon-right="arrow-right" :style="{ width: '135px' }" @click="goResume">
                이어서 풀기
              </WdsButton>
            </div>
            <div v-if="resumeProgress" class="progress-row">
              <div class="progress-bar-wrap">
                <div class="progress-bar-fill" :style="{ width: (resumeProgress.done / resumeProgress.total * 100) + '%' }" />
              </div>
              <span class="wds-caption-1 assistive">{{ resumeProgress.done }}/{{ resumeProgress.total }} 세트</span>
            </div>
          </div>
          <!-- 오답 데이터 없을 때 빈 상태 -->
          <div v-else class="side-card side-card-empty">
            <div class="empty-text">
              <div class="side-title">오답 이어풀기</div>
              <div class="wds-caption-1 assistive">진행 중인 오답 루프가 없어요.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 학습 팁 -->
      <div class="tip-row">
        <WdsIcon name="sparkle" :size="16" color="var(--suql-accent)" />
        <span class="wds-caption-1 tip-text"><strong>학습 팁</strong>&nbsp;&nbsp;{{ todayTip }}</span>
      </div>
    </div>
  </SidebarShell>
</template>

<style scoped>
.head-greeting {
  font-size: 20px;
}
.home-headline {
  font: var(--weight-bold) 34px/1.3 var(--font-sans);
  letter-spacing: -0.025em;
  margin-top: 4px;
}
.accent { color: var(--suql-accent); }



/* ── 카드 그리드 ── */
.card-grid-home {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* AI 진단 카드 */
.diag-card {
  background: linear-gradient(150deg, #3b82f6 0%, #93c5fd 100%);
  border-radius: 20px;
  padding: 28px 28px 20px;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 260px;
}
.diag-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.diag-inner {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1;
}
.diag-illust {
  width: 150px;
  height: 150px;
  flex-shrink: 0;
  opacity: 0.92;
}
.diag-inner { flex: 1; }
.diag-title {
  font: var(--weight-bold) 28px/1.3 var(--font-sans);
  letter-spacing: -0.02em;
  margin-bottom: 10px;
}
.diag-body {
  font-size: 17px;
  opacity: 0.88;
  line-height: 1.6;
  margin-bottom: 20px;
}

.diag-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.25);
  font-size: 14px;
  opacity: 0.88;
}
.diag-meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 16px;
}
.diag-meta-sep {
  opacity: 0.4;
  font-size: 13px;
}

/* 오른쪽 카드들 */
.side-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.side-card {
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  padding: 20px 22px;
  background: #eff6ff;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}
.side-card-empty {
  display: flex;
  align-items: center;
  gap: 14px;
  opacity: 0.55;
}
.side-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.side-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #dbeafe;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.side-title {
  font: var(--weight-bold) 17px/1.4 var(--font-sans);
  color: #1e3a8a;
  margin-bottom: 3px;
}
.side-btn {
  margin-left: auto;
  flex-shrink: 0;
  white-space: nowrap;
}

/* 추천 단원 행 */
.rec-unit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #bfdbfe;
}
.rec-label { white-space: nowrap; }
.rec-name {
  font: var(--weight-bold) 13px/1.4 var(--font-sans);
  color: #3b82f6;
  flex: 1;
}
.rec-chapter {
  font-weight: var(--weight-bold);
  color: #1e40af;
}
.side-card-texts {
  flex: 1;
  min-width: 0;
}
.side-sub {
  font-size: 14px;
  color: var(--label-assistive);
  margin-top: 2px;
}

/* 진행률 바 */
.progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}
.progress-bar-wrap {
  flex: 1;
  height: 6px;
  border-radius: 99px;
  background: #bfdbfe;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  border-radius: 99px;
  background: #2563eb;
  transition: width 0.3s ease;
}

/* 학습 팁 */
.tip-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border-radius: 12px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  margin-top: 20px;
}
.tip-text {
  color: #1e40af;
  font-size: 13px;
  line-height: 1.5;
}
</style>