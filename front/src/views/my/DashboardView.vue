<!-- 📄 src/views/my/DashboardView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import widnBearWave from '@/assets/images/widn-bear-wave.png'

const router = useRouter()
const loading = ref(true)
const data = ref(null)

const weekLabels = ['월', '화', '수', '목', '금', '토', '일']

const weeklyDoneCount = computed(() => {
  if (!data.value?.weekly_activity) return 0
  return data.value.weekly_activity.filter(Boolean).length
})

const solvedRate = computed(() => {
  if (!data.value?.total_problem_count) return 0
  return Math.round((data.value.total_solved / data.value.total_problem_count) * 100)
})

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

function goStudy() {
  router.push('/quiz/setup')
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

        <section class="hero-card">
          <div class="hero-copy">
            <h2>이번 주도 차근차근 잘 이어가고 있어요!</h2>
            <p>
              지금까지 {{ data.total_solved }}문제를 풀었고,
              풀이 중인 유형은 {{ data.solving_count }}개예요.
            </p>
            <button class="hero-button" type="button" @click="goHistory">
              학습 기록 확인하기
            </button>
          </div>

          <div class="hero-bear-area">
            <div class="speech-bubble">
              여러분의 학습에<br />
              위드너가 함께 할게요!
            </div>
            <img class="hero-bear" :src="widnBearWave" alt="인사하는 위드너" />
          </div>
        </section>

        <div class="card-grid cols-3 stat-grid">
          <div class="dash-stat">
            <WdsIcon name="calendar" :size="20" color="#8b5cf6" />
            <div class="dash-stat-num">
              {{ data.streak }}<span class="unit">일</span>
            </div>
            <div class="wds-caption-1 assistive">연속 학습</div>
            <div class="stat-desc">오늘도 한 걸음 성장했어요</div>
          </div>

          <div class="dash-stat">
            <WdsIcon name="document" :size="20" color="var(--suql-accent)" />
            <div class="dash-stat-num">
              {{ data.total_solved }}<span class="unit">개 / {{ data.total_problem_count }}개</span>
            </div>
            <div class="wds-caption-1 assistive">누적 푼 문제</div>
            <div class="stat-desc">전체 문제 중 {{ solvedRate }}% 풀이 완료</div>
          </div>

          <div class="dash-stat">
            <WdsIcon name="fire" :size="20" color="#d4700a" />
            <div class="dash-stat-num">
              {{ data.solving_count }}<span class="unit">개 / {{ data.total_subtype_count }}개</span>
            </div>
            <div class="wds-caption-1 assistive">풀이 중인 유형</div>
            <div class="stat-desc">다시 풀어볼 유형이 있어요</div>
          </div>

          <div class="dash-stat">
            <WdsIcon name="medal" :size="20" color="var(--status-positive)" />
            <div class="dash-stat-num">
              {{ data.mastered_count }}<span class="unit">개 / {{ data.total_subtype_count }}개</span>
            </div>
            <div class="wds-caption-1 assistive">숙달 완료한 유형</div>
            <div class="stat-desc">숙달 유형을 만들어볼까요?</div>
          </div>
        </div>

        <div class="dash-layout">
          <section class="panel-card week-panel">
            <div class="section-title">이번 주 학습</div>

            <div class="week-row">
              <div v-for="(active, i) in data.weekly_activity" :key="i" class="week-day">
                <span class="week-dot" :data-on="active">
                  <WdsIcon v-if="active" name="check" :size="15" color="#ffffff" />
                </span>
                <span class="wds-caption-2 assistive">{{ weekLabels[i] }}</span>
              </div>
            </div>

            <p class="week-message">
              이번 주 {{ weeklyDoneCount }}일 학습 완료!
              내일도 이어가면 더 좋은 학습 흐름을 만들 수 있어요.
            </p>
          </section>

          <section v-if="data.latest_session" class="panel-card latest-card">
            <div class="latest-content">
              <div>
                <div class="latest-label">최근 학습 이어하기</div>
                <div class="latest-title">{{ data.latest_session.chapter_middle }}</div>
                <div class="latest-meta">
                  {{ Math.round((data.latest_session.accuracy || 0) * 100) }}점 ·
                  {{ data.latest_session.created_at }}
                </div>
              </div>

              <button class="latest-cta" type="button" @click="goStudy">
                다시 풀기
                <WdsIcon name="chevron-right" :size="17" color="#ffffff" />
              </button>
            </div>
          </section>

          <section class="panel-card mastery-panel">
            <div class="section-title">유형별 진행 현황</div>

            <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2 empty-message">
              아직 학습 기록이 없어요. 퀴즈를 풀어보세요!
            </div>

            <div v-else class="stack-10">
              <div v-for="m in data.subtype_mastery" :key="m.problem_subtype" class="mastery-item">
                <div class="mastery-top">
                  <span class="master-badge" :data-on="m.mastered">
                    <WdsIcon v-if="m.mastered" name="crown" :size="13" color="#fff" />
                    {{ m.level }}
                  </span>
                  <span class="mastery-name">{{ m.problem_subtype }}</span>
                  <span class="mastery-pct">{{ m.pct }}%</span>
                </div>

                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: `${Math.min(m.pct, 100)}%` }" />
                </div>
              </div>
            </div>

            <div class="view-all-wrap">
              <button class="view-all-button" type="button" @click="goHistory">
                전체 보기
                <WdsIcon name="chevron-right" :size="16" color="var(--suql-accent)" />
              </button>
            </div>
          </section>

          <section class="panel-card recommend-card">
            <div class="recommend-content">
              <div>
                <div class="recommend-icon">
                  <WdsIcon name="fire" :size="20" color="var(--suql-accent)" />
                </div>
                <div class="recommend-title">오늘의 추천 학습</div>
                <p class="recommend-desc">
                  풀이 중인 유형 {{ data.solving_count }}개 중에서
                  진행률이 낮은 유형부터 다시 풀어보세요.
                </p>
              </div>

              <button class="recommend-button" type="button" @click="goHistory">
                추천 유형 보러가기
              </button>
            </div>
          </section>
        </div>
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

.page-head {
  margin-bottom: 24px;
}

.page-head .title {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.page-head .sub {
  font-size: 16px;
  margin-top: 6px;
  color: var(--label-alternative);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 28px;
  min-height: 190px;
  padding: 28px 32px;
  margin-bottom: 24px;
  border-radius: 28px;
  background:
    radial-gradient(circle at 86% 18%, rgba(59, 99, 246, 0.14), transparent 28%),
    linear-gradient(135deg, #eff6ff 0%, #f8fbff 54%, #ffffff 100%);
  box-shadow: inset 0 0 0 1px #dbeafe;
  overflow: hidden;
}

.hero-copy {
  min-width: 0;
}


.hero-copy h2 {
  margin: 0;
  font-size: 26px;
  line-height: 1.3;
  letter-spacing: -0.04em;
  color: var(--label-normal);
}

.hero-copy p {
  margin: 10px 0 0;
  font-size: 15px;
  line-height: 1.55;
  color: var(--label-alternative);
}

.hero-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 18px;
  margin-top: 18px;
  border: 0;
  border-radius: var(--radius-full);
  background: var(--suql-accent);
  color: #ffffff;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(59, 99, 246, 0.22);
}

.hero-bear-area {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  flex: 0 0 380px;
  min-height: 162px;
}

.speech-bubble {
  position: absolute;
  top: 4px;
  left: 0;
  max-width: 190px;
  padding: 13px 15px;
  border-radius: 18px 18px 18px 6px;
  background: #ffffff;
  color: var(--label-normal);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.45;
  letter-spacing: -0.02em;
  box-shadow:
    0 12px 28px rgba(15, 23, 42, 0.08),
    inset 0 0 0 1px rgba(59, 99, 246, 0.12);
}

.speech-bubble::after {
  content: '';
  position: absolute;
  right: -8px;
  bottom: 18px;
  width: 16px;
  height: 16px;
  background: #ffffff;
  transform: rotate(45deg);
  box-shadow: 1px -1px 0 rgba(59, 99, 246, 0.08);
}

.hero-bear {
  width: 180px;
  height: auto;
  object-fit: contain;
  margin-left: 148px;
  filter: drop-shadow(0 14px 18px rgba(15, 23, 42, 0.12));
}

.stat-grid {
  margin-bottom: 24px;
}

.dash-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-height: 122px;
  padding: 18px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}

.dash-stat .wds-caption-1 {
  font-size: 14px;
}

.dash-stat-num {
  font: var(--weight-bold) 23px/1 var(--font-sans);
  letter-spacing: -0.02em;
}

.dash-stat-num .unit {
  font-size: 14px;
  font-weight: var(--weight-medium);
  color: var(--label-alternative);
  margin-left: 2px;
}

.stat-desc {
  margin-top: auto;
  font-size: 13px;
  line-height: 1.35;
  color: var(--label-assistive);
}

.dash-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  grid-template-rows: 220px auto;
  gap: 24px;
  align-items: stretch;
}

.panel-card {
  box-sizing: border-box;
  padding: 22px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}

.section-title {
  margin-bottom: 18px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--label-normal);
}

.week-panel,
.latest-card,
.mastery-panel,
.recommend-card {
  min-width: 0;
  height: 100%;
}

.week-row {
  display: flex;
  gap: 12px;
}

.week-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
}

.week-day .wds-caption-2 {
  font-size: 13px;
}

.week-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--fill-normal);
}

.week-dot[data-on='true'] {
  background: var(--suql-accent);
  box-shadow: 0 8px 16px rgba(59, 99, 246, 0.24);
}

.week-message {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  color: var(--label-alternative);
  font-size: 14px;
  line-height: 1.45;
}

.latest-card {
  text-align: left;
}

.latest-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100%;
}

.latest-label {
  font-size: 14px;
  font-weight: 800;
  color: var(--label-alternative);
}

.latest-title {
  margin-top: 10px;
  color: var(--label-normal);
  font-size: 22px;
  font-weight: 900;
  line-height: 1.35;
  letter-spacing: -0.04em;
}

.latest-meta {
  margin-top: 6px;
  font-size: 13px;
  color: var(--label-alternative);
}

.latest-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: fit-content;
  height: 36px;
  padding: 0 13px;
  margin-top: 18px;
  border: 0;
  border-radius: var(--radius-full);
  background: var(--suql-accent);
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.empty-message {
  padding: 14px 0;
}

.stack-10 {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mastery-item {
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.mastery-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.master-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 0 0 auto;
  min-width: 70px;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-full);
  background: #ffffff;
  color: var(--label-alternative);
  font-size: 12px;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}

.master-badge[data-on='true'] {
  background: var(--suql-accent);
  color: #ffffff;
  box-shadow: none;
}

.mastery-name {
  flex: 1;
  min-width: 0;
  color: var(--label-normal);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
}

.mastery-pct {
  flex: 0 0 auto;
  color: var(--label-alternative);
  font-size: 14px;
  font-weight: 800;
}

.progress-track {
  height: 8px;
  margin-top: 12px;
  border-radius: var(--radius-full);
  background: #eef2f7;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--suql-accent);
}

.view-all-wrap {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}

.view-all-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 38px;
  padding: 0 16px;
  border: 0;
  border-radius: var(--radius-full);
  background: rgba(59, 99, 246, 0.08);
  color: var(--suql-accent);
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.recommend-content {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100%;
}

.recommend-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  margin-bottom: 14px;
  border-radius: var(--radius-full);
  background: rgba(59, 99, 246, 0.1);
}

.recommend-title {
  font-size: 18px;
  font-weight: 900;
  letter-spacing: -0.03em;
  color: var(--label-normal);
}

.recommend-desc {
  margin: 8px 0 0;
  color: var(--label-alternative);
  font-size: 14px;
  line-height: 1.55;
}

.recommend-button {
  width: 100%;
  height: 42px;
  margin-top: 16px;
  border: 0;
  border-radius: 14px;
  background: rgba(59, 99, 246, 0.08);
  color: var(--suql-accent);
  font-weight: 800;
  cursor: pointer;
}

@media (max-width: 1080px) {
  .dash-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .week-panel,
  .latest-card,
  .mastery-panel,
  .recommend-card {
    height: auto;
  }
}

@media (max-width: 860px) {
  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-bear-area {
    width: 100%;
    flex-basis: auto;
    justify-content: flex-end;
  }

  .speech-bubble {
    left: 8px;
  }
}

@media (max-width: 640px) {
  .hero-card {
    padding: 24px 20px;
    border-radius: 22px;
  }

  .hero-copy h2 {
    font-size: 22px;
  }

  .hero-bear-area {
    min-height: 150px;
  }

  .hero-bear {
    width: 140px;
    margin-left: 120px;
  }

  .speech-bubble {
    max-width: 170px;
    font-size: 13px;
  }

  .week-row {
    gap: 8px;
  }

  .week-dot {
    width: 32px;
    height: 32px;
  }

  .mastery-top {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .mastery-name {
    flex-basis: calc(100% - 90px);
  }

  .mastery-pct {
    margin-left: auto;
  }
}
</style>