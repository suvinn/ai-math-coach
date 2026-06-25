<!-- 📄 src/views/quiz/QuizSetupView.vue -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
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

const chapters = ref([])
const counts = ref([])
const subtypeCounts = ref([])
const loading = ref(true)
const creating = ref(false)

const selectedMajor = ref(null)
const selectedMiddle = ref(null)
const selectedSubtype = ref(null)
const problemCount = ref(10)

async function init() {
  loading.value = true
  selectedMajor.value = null
  selectedMiddle.value = null
  selectedSubtype.value = null
  problemCount.value = 10

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
  selectedMiddle.value = null
  selectedSubtype.value = null
}

function selectMiddle(middle) {
  selectedMiddle.value = middle
  selectedSubtype.value = null
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
          <div class="stack-8">
            <button
              v-for="c in chapters"
              :key="c.chapter_major"
              class="middle-row tap-row"
              :data-on="selectedMajor === c.chapter_major"
              @click="selectMajor(c.chapter_major)"
            >
              <span class="middle-name">{{ c.chapter_major }}</span>
              <WdsIcon
                v-if="selectedMajor === c.chapter_major"
                name="circle-check"
                :size="20"
                color="var(--suql-accent)"
              />
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
              @click="selectMiddle(m.chapter_middle)"
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

        <!-- 유형 -->
        <div v-if="selectedMiddle && subtypes.length" class="setup-section">
          <div class="field-label">유형</div>
          <div class="stack-8">
            <button
              class="middle-row tap-row"
              :data-on="selectedSubtype === null"
              @click="selectedSubtype = null"
            >
              <span class="middle-name">전체</span>
              <WdsIcon
                v-if="selectedSubtype === null"
                name="circle-check"
                :size="20"
                color="var(--suql-accent)"
              />
            </button>
            <button
              v-for="s in subtypes"
              :key="s"
              class="middle-row tap-row"
              :data-on="selectedSubtype === s"
              @click="selectedSubtype = s"
            >
              <span class="middle-name">{{ s }}</span>
              <WdsIcon
                v-if="selectedSubtype === s"
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
  color: var(--suql-accent);
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
  box-shadow: inset 0 0 0 1.5px var(--suql-accent);
  background: var(--blue-99);
}
.middle-name {
  font: var(--weight-semibold) 15px/1.3 var(--font-sans);
  color: var(--label-normal);
}
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