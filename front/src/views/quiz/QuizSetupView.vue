<!-- 📄 src/views/quiz/QuizSetupView.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const route = useRoute()
const router = useRouter()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

const chapters = ref([])
const counts = ref([])
const subtypeCounts = ref([])
const loading = ref(true)
const creating = ref(false)

const selectedMajor = ref(null)
const selectedMiddle = ref(null)
const selectedSubtype = ref(null)
const problemCount = ref(10)
const subtypeOpen = ref(false)

async function init() {
  loading.value = true
  selectedMajor.value = null
  selectedMiddle.value = null
  selectedSubtype.value = null
  problemCount.value = 10
  subtypeOpen.value = false

  const mode = route.query.mode

  try {
    const [chData, cntData, subData] = await Promise.all([
      api.get('/chapters').then(unwrap),
      api.get('/chapters/problem-counts').then(unwrap),
      api.get('/chapters/subtype-counts').then(unwrap),
    ])
    chapters.value = chData || []
    counts.value = cntData || []
    subtypeCounts.value = subData || []

    if (mode === 'today') {
      // 홈화면에서 넘겨준 추천 단원 우선 사용
      const qMajor = route.query.major
      const qMiddle = route.query.middle
      if (qMajor && qMiddle) {
        selectedMajor.value = qMajor
        selectedMiddle.value = qMiddle
      } else {
        try {
          const rec = unwrap(await api.get('/users/me/today-recommendation'))
          if (rec?.has_recommendation && rec.prefill) {
            selectedMajor.value = rec.prefill.chapter_major
            selectedMiddle.value = rec.prefill.chapter_middle
            problemCount.value = rec.prefill.suggested_count || 10
          }
        } catch {
          // 추천 실패 시 첫 번째 대단원으로 폴백
        }
      }
    }

    if (!selectedMajor.value && chapters.value.length) {
      selectedMajor.value = chapters.value[0].chapter_major
    }
    if (!selectedMiddle.value && chapters.value[0]?.chapter_middles?.length) {
      selectedMiddle.value = chapters.value[0].chapter_middles[0].chapter_middle
    }

  } catch {
    showToast('단원 정보를 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
}

onMounted(init)
watch(() => route.query.mode, init)

const middles = computed(() => {
  const major = chapters.value.find((c) => c.chapter_major === selectedMajor.value)
  return major ? major.chapter_middles : []
})

const subtypes = computed(() => {
  if (!selectedMajor.value || !selectedMiddle.value) return []
  const set = new Set(
    subtypeCounts.value
      .filter(
        (r) =>
          r.chapter_major === selectedMajor.value &&
          r.chapter_middle === selectedMiddle.value,
      )
      .map((r) => r.problem_subtype),
  )
  return [...set]
})

const selectedCount = computed(() => {
  if (!selectedMajor.value || !selectedMiddle.value) return 0
  if (selectedSubtype.value) {
    return subtypeCounts.value
      .filter(
        (r) =>
          r.chapter_major === selectedMajor.value &&
          r.chapter_middle === selectedMiddle.value &&
          r.problem_subtype === selectedSubtype.value,
      )
      .reduce((sum, r) => sum + r.count, 0)
  }
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
  const m = chapters.value.find((c) => c.chapter_major === major)
  selectedMiddle.value = m?.chapter_middles?.[0]?.chapter_middle ?? null
  selectedSubtype.value = null
  subtypeOpen.value = false
}

function selectMiddle(middle) {
  selectedMiddle.value = middle
  selectedSubtype.value = null
  subtypeOpen.value = false
}

function pickSubtype(s) {
  selectedSubtype.value = s
  subtypeOpen.value = false
}

const canStart = computed(
  () => selectedMajor.value && selectedMiddle.value && !creating.value,
)

const title = '퀴즈 설정'

async function start() {
  if (!canStart.value) return
  creating.value = true
  try {
    const res = await quiz.createAndLoad({
      chapter_major: selectedMajor.value,
      chapter_middle: selectedMiddle.value,
      problem_subtype: selectedSubtype.value || undefined,
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
          <div class="opt-grid">
            <button
              v-for="c in chapters"
              :key="c.chapter_major"
              class="middle-row opt-cell tap-row"
              :data-on="selectedMajor === c.chapter_major"
              @click="selectMajor(c.chapter_major)"
            >
              <span class="middle-name">{{ c.chapter_major }}</span>
            </button>
          </div>
        </div>

        <!-- 중단원 -->
        <div v-if="selectedMajor" class="setup-section">
          <div class="field-label">중단원</div>
          <div class="opt-grid">
            <button
              v-for="m in middles"
              :key="m.chapter_middle"
              class="middle-row opt-cell tap-row"
              :data-on="selectedMiddle === m.chapter_middle"
              @click="selectMiddle(m.chapter_middle)"
            >
              <span class="middle-name">{{ m.chapter_middle }}</span>
            </button>
          </div>
        </div>

        <!-- 유형 -->
        <div v-if="selectedMiddle && subtypes.length" class="setup-section">
          <div class="field-label">
            유형
            <span class="assistive field-hint">전체 선택 시 모든 유형에서 골고루 출제돼요.</span>
          </div>

          <!-- 토글바: 기본 전체, 누르면 전체 유형 펼침 -->
          <button
            class="middle-row type-toggle tap-row"
            :data-on="subtypeOpen"
            @click="subtypeOpen = !subtypeOpen"
          >
            <span class="middle-name">{{ selectedSubtype || (subtypeOpen ? '접기' : '전체 유형 보기') }}</span>
            <span class="chev" :data-open="subtypeOpen" />
          </button>

          <!-- 펼친 목록 -->
          <div v-if="subtypeOpen" class="opt-grid">
            <button
              class="middle-row opt-cell tap-row"
              :data-on="selectedSubtype === null"
              @click="pickSubtype(null)"
            >
              <span class="middle-name">전체</span>
            </button>
            <button
              v-for="s in subtypes"
              :key="s"
              class="middle-row opt-cell tap-row"
              :data-on="selectedSubtype === s"
              @click="pickSubtype(s)"
            >
              <span class="middle-name">{{ s }}</span>
            </button>
          </div>
        </div>

        <!-- 문제 수 -->
        <div v-if="selectedMiddle" class="setup-section">
          <div class="field-label">
            문제 수
            <span class="assistive" style="font-weight: 400; font-size: 18px">· 이 범위 {{ selectedCount }}문제</span>
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
          <p class="assistive count-hint">선택한 범위의 문제가 부족하면 가능한 문제 수만큼 출제돼요.</p>
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
  gap: 30px;
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
  font: var(--weight-semibold) 20px/1 var(--font-sans);
  color: var(--label-normal);
  letter-spacing: -0.01em;
}
.field-hint {
  font-weight: 400;
  font-size: 14px;
  letter-spacing: -0.01em;
}
.middle-row {
  padding: 14px;
  margin: 0;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
  justify-content: space-between;
}
.middle-row[data-on='true'] {
  box-shadow: inset 0 0 0 1.5px #bfdbfe;
  background: var(--blue-99);
}
.middle-name {
  font: var(--weight-semibold) 15px/1.3 var(--font-sans);
  color: var(--label-normal);
}
/* 대단원·중단원: 한 줄에 3개 균등 폭, 높이는 padding 기준으로 동일 */
.opt-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.opt-cell {
  justify-content: center;
  align-items: center;
  text-align: center;
}
.opt-cell .middle-name {
  word-break: keep-all;
}
/* 유형 토글바: 대단원·중단원 박스와 동일한 .middle-row 크기 */
.type-toggle {
  width: 100%;
}
.chev {
  width: 8px;
  height: 8px;
  flex: none;
  border-right: 2px solid var(--label-alternative);
  border-bottom: 2px solid var(--label-alternative);
  transform: rotate(45deg);
  margin-bottom: 4px;
  transition: transform 0.18s, margin-bottom 0.18s;
}
.chev[data-open='true'] {
  transform: rotate(-135deg);
  margin-bottom: -2px;
}
.count-row {
  display: flex;
  gap: 8px;
}
/* 변경 후 */
.count-chip {
  flex: 1;
  cursor: pointer;
  height: 52px;
  border: none;
  border-radius: 14px;                                  /* 13 → 14, middle-row랑 통일 */
  background: transparent;                              /* fill 제거 */
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);/* 기본 테두리 */
  color: var(--label-normal);                          /* 회색 → 일반 텍스트 */
  font: var(--weight-bold) 15px/1 var(--font-sans);
  transition: background 0.12s, box-shadow 0.12s, color 0.12s;
}
.count-chip[data-on='true'] {
  box-shadow: inset 0 0 0 1.5px #bfdbfe;     /* accent 테두리 */
  background: var(--blue-99);                           /* 연파랑 배경 */
  color: var(--label-normal);
}
.count-hint {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.4;
}
</style>