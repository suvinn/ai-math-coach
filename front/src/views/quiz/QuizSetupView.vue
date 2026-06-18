<!-- 📄 src/views/quiz/QuizSetupView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const route = useRoute()
const router = useRouter()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

// mode: diag(빠른 진단) | today(오늘의 추천) | undefined(학습 탭)
const mode = route.query.mode

const chapters = ref([])          // [{ chapter_major, chapter_middles: [{ chapter_middle, chapter_minors }] }]
const counts = ref([])            // [{ chapter_major, chapter_middle, chapter_minor, count }]
const loading = ref(true)
const creating = ref(false)

const selectedMajor = ref(null)
const selectedMiddle = ref(null)
const problemCount = ref(10)

onMounted(async () => {
  try {
    const [chData, cntData] = await Promise.all([
      api.get('/chapters').then(unwrap),
      api.get('/chapters/problem-counts').then(unwrap),
    ])
    chapters.value = chData || []
    counts.value = cntData || []

    // today 모드: 추천 prefill로 대단원/중단원 자동 선택
    if (mode === 'today') {
      try {
        const rec = unwrap(await api.get('/users/me/today-recommendation'))
        if (rec?.has_recommendation && rec.prefill) {
          selectedMajor.value = rec.prefill.chapter_major
          selectedMiddle.value = rec.prefill.chapter_middle
          problemCount.value = rec.prefill.suggested_count || 10
        }
      } catch {
        // 추천 없으면 그냥 수동 선택
      }
    }
  } catch {
    showToast('단원 정보를 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
})

// 현재 선택된 대단원의 중단원 목록
const middles = computed(() => {
  const major = chapters.value.find((c) => c.chapter_major === selectedMajor.value)
  return major ? major.chapter_middles : []
})

// 선택된 중단원의 문제 수 (소단원 합산)
const selectedCount = computed(() => {
  if (!selectedMajor.value || !selectedMiddle.value) return 0
  return counts.value
    .filter(
      (r) =>
        r.chapter_major === selectedMajor.value &&
        r.chapter_middle === selectedMiddle.value,
    )
    .reduce((sum, r) => sum + r.count, 0)
})

function selectMajor(major) {
  selectedMajor.value = major
  selectedMiddle.value = null // 대단원 바뀌면 중단원 초기화
}

const canStart = computed(
  () => selectedMajor.value && selectedMiddle.value && !creating.value,
)

const title = computed(() => (mode === 'diag' ? '빠른 진단' : '퀴즈 설정'))

async function start() {
  if (!canStart.value) return
  creating.value = true
  try {
    const res = await quiz.createAndLoad({
      chapter_major: selectedMajor.value,
      chapter_middle: selectedMiddle.value,
      problem_count: problemCount.value,
    })
    if (!res.problems.length) {
      showToast('이 범위에 풀 수 있는 문제가 없어요', 'negative', 'circle-exclamation')
      creating.value = false
      return
    }
    router.push('/quiz/play')
  } catch (e) {
    const msg = e?.response?.data?.message || '퀴즈를 시작하지 못했어요'
    showToast(msg, 'negative', 'circle-exclamation')
    creating.value = false
  }
}
</script>

<template>
  <FocusShell :title="title" :toast="toast" @back="router.push('/')">
    <div class="setup-body">
      <div v-if="loading" class="setup-loading">
        <p class="assistive">단원을 불러오는 중…</p>
      </div>

      <template v-else>
        <!-- 대단원 -->
        <div class="setup-section">
          <div class="field-label">대단원</div>
          <div class="chiprow setup-chips">
            <button
              v-for="c in chapters"
              :key="c.chapter_major"
              class="setup-chip"
              :data-on="selectedMajor === c.chapter_major"
              @click="selectMajor(c.chapter_major)"
            >
              {{ c.chapter_major }}
            </button>
          </div>
        </div>

        <!-- 중단원 -->
        <div v-if="selectedMajor" class="setup-section">
          <div class="field-label">중단원</div>
          <div class="stack-8">
            <button
              v-for="m in middles"
              :key="m.chapter_middle"
              class="middle-row tap-row"
              :data-on="selectedMiddle === m.chapter_middle"
              @click="selectedMiddle = m.chapter_middle"
            >
              <span class="middle-name">{{ m.chapter_middle }}</span>
              <WdsIcon
                v-if="selectedMiddle === m.chapter_middle"
                name="circle-check"
                :size="20"
                color="var(--suql-accent)"
              />
            </button>
          </div>
        </div>

        <!-- 문제 수 -->
        <div v-if="selectedMiddle" class="setup-section">
          <div class="field-label">
            문제 수
            <span class="assistive" style="font-weight: 400">· 이 범위 {{ selectedCount }}문제</span>
          </div>
          <div class="count-row">
            <button
              v-for="n in [10, 20, 30]"
              :key="n"
              class="count-chip"
              :data-on="problemCount === n"
              @click="problemCount = n"
            >
              {{ n }}문제
            </button>
          </div>
        </div>
      </template>
    </div>

    <template #foot>
      <WdsButton
        variant="primary"
        size="large"
        block
        icon-right="arrow-right"
        :disabled="!canStart"
        @click="start"
      >
        {{ creating ? '준비 중…' : '시작하기' }}
      </WdsButton>
    </template>
  </FocusShell>
</template>

<style scoped>
.setup-body {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.setup-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.setup-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-label {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-alternative);
  letter-spacing: -0.01em;
}

/* 대단원 칩 */
.setup-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.setup-chip {
  border: none;
  cursor: pointer;
  padding: 9px 14px;
  border-radius: var(--radius-full);
  background: var(--fill-normal);
  color: var(--label-alternative);
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  transition: background 0.12s, color 0.12s;
}
.setup-chip[data-on='true'] {
  background: var(--suql-accent);
  color: #fff;
}

/* 중단원 행 */
.middle-row {
  padding: 14px;
  margin: 0;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
  justify-content: space-between;
}
.middle-row[data-on='true'] {
  box-shadow: inset 0 0 0 1.5px var(--suql-accent);
  background: var(--blue-99);
}
.middle-name {
  font: var(--weight-semibold) 15px/1.3 var(--font-sans);
  color: var(--label-normal);
}

/* 문제 수 */
.count-row {
  display: flex;
  gap: 8px;
}
.count-chip {
  flex: 1;
  border: none;
  cursor: pointer;
  height: 52px;
  border-radius: 13px;
  background: var(--fill-normal);
  color: var(--label-alternative);
  font: var(--weight-bold) 15px/1 var(--font-sans);
  transition: background 0.12s, color 0.12s;
}
.count-chip[data-on='true'] {
  background: var(--suql-accent);
  color: #fff;
}
</style>