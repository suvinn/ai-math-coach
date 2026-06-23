<!-- 📄 src/views/my/HistoryView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const loading = ref(true)
const data = ref(null)

const SESSION_TYPE_LABEL = {
  normal: '1차 풀이',
  review_1: '보완 1차',
  review_2: '보완 2차',
}

// created_at은 ISO datetime 문자열로 내려오므로 날짜만 잘라서 표시
function formatDate(iso) {
  return iso ? iso.slice(0, 10) : ''
}

onMounted(async () => {
  try {
    data.value = unwrap(await api.get('/users/me/history'))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <SidebarShell tab="report">
    <div class="page">
      <div class="page-head"><div class="title">학습 이력</div></div>

      <div v-if="loading" class="hist-loading">
        <p class="assistive">불러오는 중…</p>
      </div>

      <template v-else-if="data">
        <div class="stack-12" style="margin-bottom: 32px">
          <div class="wds-label-1" style="font-weight: 700">유형별 마스터 현황</div>
          <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2">아직 학습 기록이 없어요.</div>
          <div v-else class="card-grid cols-3">
            <div v-for="m in data.subtype_mastery" :key="m.problem_subtype" class="mastery-card">
              <span class="master-badge" :data-on="m.mastered">
                <WdsIcon v-if="m.mastered" name="crown" :size="13" color="#fff" />
                {{ m.level }}
              </span>
              <div class="wds-label-1" style="font-weight: 700; margin-top: 10px">{{ m.problem_subtype }}</div>
              <div class="row" style="margin-top: 6px; gap: 8px">
                <template v-if="m.accuracy_before != null && m.accuracy_after != null">
                  <span class="rate-jump">
                    <span class="was">{{ m.accuracy_before }}%</span>
                    <WdsIcon name="arrow-right" :size="14" color="var(--label-assistive)" />
                    <span class="now">{{ m.accuracy_after }}%</span>
                  </span>
                </template>
                <span v-else class="wds-body-2 assistive">정답률 {{ m.accuracy }}%</span>
              </div>
              <div class="wds-caption-2 assistive" style="margin-top: 6px">{{ m.total_attempts }}문제 시도</div>
            </div>
          </div>
        </div>

        <div class="stack-12">
          <div class="wds-label-1" style="font-weight: 700">퀴즈 기록</div>
          <div v-if="!data.sessions.length" class="assistive wds-body-2">아직 풀어본 퀴즈가 없어요.</div>
          <div v-else class="stack-8">
            <div v-for="s in data.sessions" :key="s.session_id" class="session-row">
              <span class="play-badge play-badge--type">{{ SESSION_TYPE_LABEL[s.session_type] || s.session_type }}</span>
              <div style="flex: 1; min-width: 0">
                <div class="wds-label-1" style="font-weight: 600">
                  {{ s.chapter_middle }}<template v-if="s.chapter_minor"> · {{ s.chapter_minor }}</template>
                </div>
                <div class="wds-caption-1 assistive" style="margin-top: 2px">{{ formatDate(s.created_at) }}</div>
              </div>
              <div class="session-score">{{ s.score }} / {{ s.total }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </SidebarShell>
</template>

<style scoped>
.hist-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}
.mastery-card {
  padding: 18px;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.session-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.session-score {
  font: var(--weight-bold) 15px/1 var(--font-sans);
  color: var(--suql-accent);
  flex: none;
}
</style>
