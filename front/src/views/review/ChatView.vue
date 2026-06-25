<!-- 📄 src/views/review/ChatView.vue -->
<!-- 해설 AI 챗봇 (B5b): ExplainView의 "AI에게 질문하기"에서 진입.
     quiz.chatContext = { sessionId, problem } 이 설정돼 있어야 한다. -->
<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import api, { unwrap } from '@/api'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import InlineTex from '@/components/common/InlineTex.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

const ctx = quiz.chatContext  // { sessionId, problem }
if (!ctx) router.replace('/review/play')

const messages      = ref([])    // [{ who: 'ai'|'user', text: string }]
const inputText     = ref('')
const sending       = ref(false)
const chatBottom    = ref(null)
const inputBlocked  = ref(false) // 토큰 초과 시 입력창 비활성화

// 첫 AI 인사말
onMounted(() => {
  messages.value.push({
    who: 'ai',
    text: `"${ctx.problem.question_text?.slice(0, 30)}…" 해설 중 어디가 막혔는지 편하게 물어보세요.`,
  })
})

async function send() {
  const q = inputText.value.trim()
  if (!q || sending.value || inputBlocked.value) return

  messages.value.push({ who: 'user', text: q })
  inputText.value = ''
  sending.value = true
  await scrollBottom()

  // 백엔드에 전달할 누적 대화 이력 (현재 질문 제외한 이전 메시지들)
  const history = messages.value
    .slice(0, -1)  // 방금 push한 현재 질문은 제외 (백엔드가 question으로 받음)
    .map(m => ({ role: m.who, text: m.text }))

  try {
    const data = unwrap(await api.post(
      `/quiz/sessions/${ctx.sessionId}/chat`,
      {
        problem_id: ctx.problem.problem_id,
        question:   q,
        history,               // 누적 대화 이력 전달
      }
    ))

    messages.value.push({ who: 'ai', text: data.answer })

    // 토큰 초과로 차단된 경우 입력창 비활성화
    if (data.is_blocked && data.block_reason === 'token_exceeded') {
      inputBlocked.value = true
    }
  } catch {
    showToast('답변을 받지 못했어요', 'negative', 'circle-exclamation')
    messages.value.push({ who: 'ai', text: '죄송해요, 잠시 후 다시 시도해주세요.' })
  } finally {
    sending.value = false
    await scrollBottom()
  }
}

async function scrollBottom() {
  await nextTick()
  chatBottom.value?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<template>
  <FocusShell title="해설 챗봇" :toast="toast" @back="router.push('/review/play')">
    <div class="chat-wrap">
      <!-- 메시지 목록 -->
      <div class="chat-messages">
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="chat-row"
          :class="m.who"
        >
          <div v-if="m.who === 'ai'" class="ai-head">
            <WdsIcon name="sparkle" :size="14" color="var(--suql-accent)" />
            <span class="wds-caption-2" style="font-weight:700; color:var(--suql-accent)">수학 해설 튜터</span>
          </div>
          <div class="chat-bubble">
            <InlineTex :text="m.text" />
          </div>
        </div>

        <!-- 입력 중 인디케이터 -->
        <div v-if="sending" class="chat-row ai">
          <div class="ai-head">
            <WdsIcon name="sparkle" :size="14" color="var(--suql-accent)" />
            <span class="wds-caption-2" style="font-weight:700; color:var(--suql-accent)">수학 해설 튜터</span>
          </div>
          <div class="chat-bubble typing">
            <span /><span /><span />
          </div>
        </div>

        <div ref="chatBottom" />
      </div>
    </div>

    <template #foot>
      <!-- 토큰 초과 안내 배너 -->
      <div v-if="inputBlocked" class="blocked-banner">
        <WdsIcon name="circle-exclamation" :size="14" color="var(--label-assistive)" />
        <span>대화가 너무 길어졌어요. 뒤로 가서 새로 시작해주세요.</span>
      </div>

      <div class="chat-input-row">
        <input
          v-model="inputText"
          class="chat-input"
          placeholder="질문을 입력하세요…"
          :disabled="sending || inputBlocked"
          @keyup.enter="send"
        />
        <button
          class="send-btn"
          :disabled="!inputText.trim() || sending || inputBlocked"
          @click="send"
        >
          <WdsIcon name="arrow-right" :size="20" color="#fff" />
        </button>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.chat-wrap { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.chat-messages {
  display: flex; flex-direction: column; gap: 16px;
  padding-bottom: 12px;
}
.chat-row { display: flex; flex-direction: column; gap: 4px; }
.chat-row.user { align-items: flex-end; }
.chat-row.ai   { align-items: flex-start; }

.ai-head { display: flex; align-items: center; gap: 5px; margin-bottom: 2px; }

.chat-bubble {
  max-width: 80%; padding: 12px 14px; border-radius: 16px;
  font: var(--weight-regular) 14px/1.6 var(--font-sans);
  word-break: break-word;
}
.chat-row.ai   .chat-bubble { background: var(--fill-normal); border-bottom-left-radius: 4px; color: var(--label-normal); }
.chat-row.user .chat-bubble { background: var(--suql-accent); border-bottom-right-radius: 4px; color: #fff; }

/* 입력 중 애니메이션 */
.typing { display: flex; align-items: center; gap: 4px; padding: 14px 16px; }
.typing span {
  width: 6px; height: 6px; border-radius: 50%; background: var(--label-assistive);
  animation: bounce 1s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.30s; }
@keyframes bounce { 0%,80%,100% { transform: translateY(0); } 40% { transform: translateY(-5px); } }

/* 토큰 초과 배너 */
.blocked-banner {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 14px; margin-bottom: 8px;
  border-radius: 10px; background: var(--fill-normal);
  font: var(--weight-regular) 13px/1.4 var(--font-sans);
  color: var(--label-assistive);
}

/* 하단 입력 */
.chat-input-row { display: flex; gap: 10px; align-items: center; }
.chat-input {
  flex: 1; height: 48px; padding: 0 16px;
  border-radius: 13px; border: none; background: var(--fill-normal);
  font: var(--weight-medium) 15px/1 var(--font-sans); color: var(--label-normal);
  outline: none;
}
.chat-input:focus { box-shadow: inset 0 0 0 1.5px var(--suql-accent); background: var(--background-normal-normal); }
.chat-input:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn {
  width: 48px; height: 48px; border-radius: 13px; border: none; flex: none;
  background: var(--suql-accent); cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: opacity 0.15s;
}
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>