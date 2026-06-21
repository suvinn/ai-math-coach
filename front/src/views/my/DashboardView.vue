<!-- 📄 src/views/my/DashboardView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const router = useRouter()
const loading = ref(true)
const data = ref(null)

const weekLabels = ['월', '화', '수', '목', '금', '토', '일']

onMounted(async () => {
  try {
    data.value = unwrap(await api.get('/users/me/dashboard'))
  } finally {
    loading.value = false
  }
})

function goHistory() {
  router.push('/my/history')
}
</script>

<template>
  <SidebarShell tab="my">
    <div class="page">
      <div v-if="loading" class="dash-loading">
        <p class="assistive">불러오는 중…</p>
      </div>

      <template v-else-if="data">
        <div class="page-head">
          <div class="title">{{ data.user.name }}님</div>
          <div class="sub">{{ data.user.grade }} · 가입 {{ data.user.joined_days }}일째</div>
        </div>

        <div class="card-grid cols-3" style="margin-bottom: 24px">
          <div class="dash-stat">
            <WdsIcon name="fire" :size="20" color="var(--status-cautionary)" />
            <div class="dash-stat-num">{{ data.streak }}<span class="unit">일</span></div>
            <div class="wds-caption-1 assistive">연속 학습</div>
          </div>
          <div class="dash-stat">
            <WdsIcon name="document" :size="20" color="var(--suql-accent)" />
            <div class="dash-stat-num">{{ data.total_solved }}<span class="unit">개</span></div>
            <div class="wds-caption-1 assistive">누적 푼 문제</div>
          </div>
          <div class="dash-stat">
            <WdsIcon name="medal" :size="20" color="var(--status-positive)" />
            <div class="dash-stat-num">{{ data.subtype_mastery.filter((m) => m.mastered).length }}<span class="unit">개</span></div>
            <div class="wds-caption-1 assistive">마스터한 유형</div>
          </div>
        </div>

        <div class="stack-12" style="margin-bottom: 24px">
          <div class="wds-label-1" style="font-weight: 700">이번 주 학습</div>
          <div class="week-row">
            <div v-for="(active, i) in data.weekly_activity" :key="i" class="week-day">
              <span class="week-dot" :data-on="active" />
              <span class="wds-caption-2 assistive">{{ weekLabels[i] }}</span>
            </div>
          </div>
        </div>

        <div class="stack-12" style="margin-bottom: 24px">
          <div class="between">
            <div class="wds-label-1" style="font-weight: 700">유형별 마스터 진척</div>
            <button class="wds-caption-1 assistive" style="border:0;background:transparent;cursor:pointer" @click="goHistory">
              전체 보기 ›
            </button>
          </div>
          <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2">아직 학습 기록이 없어요. 퀴즈를 풀어보세요!</div>
          <div v-else class="stack-8">
            <div v-for="m in data.subtype_mastery" :key="m.problem_subtype" class="tap-row mastery-row">
              <span class="master-badge" :data-on="m.mastered">
                <WdsIcon v-if="m.mastered" name="crown" :size="13" color="#fff" />
                {{ m.level }}
              </span>
              <span class="wds-label-1" style="flex: 1; font-weight: 600">{{ m.problem_subtype }}</span>
              <span class="wds-label-2 assistive">{{ m.pct }}%</span>
            </div>
          </div>
        </div>

        <button v-if="data.latest_session" class="tap-row latest-row" @click="goHistory">
          <div style="flex: 1">
            <div class="wds-label-1" style="font-weight: 700">최근 학습</div>
            <div class="wds-caption-1 assistive" style="margin-top: 2px">
              {{ data.latest_session.chapter_middle }} · {{ Math.round((data.latest_session.accuracy || 0) * 100) }}점 · {{ data.latest_session.created_at }}
            </div>
          </div>
          <WdsIcon name="chevron-right" :size="20" color="var(--label-assistive)" />
        </button>
      </template>
    </div>
  </SidebarShell>
</template>

<style scoped>
.dash-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}
.dash-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 18px;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.dash-stat-num {
  font: var(--weight-bold) 22px/1 var(--font-sans);
  letter-spacing: -0.02em;
}
.dash-stat-num .unit {
  font-size: 14px;
  font-weight: var(--weight-medium);
  color: var(--label-alternative);
  margin-left: 2px;
}
.week-row {
  display: flex;
  gap: 10px;
}
.week-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.week-dot {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--fill-normal);
  display: block;
}
.week-dot[data-on='true'] {
  background: var(--suql-accent);
}
.mastery-row {
  padding: 10px 12px;
  margin: 0;
  border-radius: 12px;
}
.latest-row {
  padding: 16px;
  margin: 0;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
  max-width: 560px;
}
</style>
