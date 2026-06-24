<!-- 📄 src/views/community/CommentView.vue -->
<!-- 문제별 공개 Q&A 댓글 페이지 (커뮤니티) -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'
import InlineTex from '@/components/common/InlineTex.vue'
import Toast from '@/components/common/Toast.vue'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const { toast, showToast } = useToast()

const problemId = route.params.problem_id
const loading   = ref(true)
const data      = ref(null)   // { problem_id, comment_count, comments }
const newComment = ref('')
const submitting  = ref(false)

onMounted(async () => {
  try {
    data.value = unwrap(await api.get(`/problems/${problemId}/comments`))
  } catch {
    showToast('댓글을 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
})

async function submitComment() {
  if (!newComment.value.trim()) {
    showToast('댓글을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  submitting.value = true
  try {
    const created = unwrap(
      await api.post(`/problems/${problemId}/comments`, { content: newComment.value.trim() })
    )
    data.value.comments.push(created)
    data.value.comment_count += 1
    newComment.value = ''
  } catch (e) {
    const msg = e?.response?.data?.message || '댓글 작성에 실패했어요'
    showToast(msg, 'negative', 'circle-exclamation')
  } finally {
    submitting.value = false
  }
}

async function deleteComment(commentId) {
  if (!confirm('댓글을 삭제할까요?')) return
  try {
    await api.delete(`/problems/${problemId}/comments/${commentId}`)
    data.value.comments = data.value.comments.filter(c => c.id !== commentId)
    data.value.comment_count -= 1
    showToast('댓글이 삭제됐어요', 'positive', 'circle-check')
  } catch (e) {
    const msg = e?.response?.data?.message || '삭제에 실패했어요'
    showToast(msg, 'negative', 'circle-exclamation')
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10) + ' ' + iso.slice(11, 16)
}
</script>

<template>
  <FocusShell title="문제 Q&A" :toast="toast" @back="router.back()">
    <Toast :toast="toast" />

    <div v-if="loading" class="center-msg assistive">불러오는 중…</div>

    <template v-else-if="data">
      <div class="comment-head">
        <span class="wds-label-1" style="font-weight: 700">
          댓글 {{ data.comment_count }}개
        </span>
        <span class="wds-caption-1 assistive">문제 ID: {{ problemId }}</span>
      </div>

      <!-- 댓글 목록 -->
      <div v-if="data.comments.length" class="stack-12">
        <div
          v-for="c in data.comments"
          :key="c.id"
          class="comment-card"
        >
          <div class="comment-meta">
            <span class="comment-author">{{ c.name || c.username }}</span>
            <span class="wds-caption-1 assistive">{{ formatDate(c.created_at) }}</span>
            <button
              v-if="auth.user?.username === c.username"
              class="delete-btn"
              @click="deleteComment(c.id)"
            >삭제</button>
          </div>
          <div class="comment-content wds-body-2">
            <InlineTex :text="c.content" />
          </div>
        </div>
      </div>
      <div v-else class="center-msg assistive">
        아직 댓글이 없어요. 첫 번째로 질문해보세요!
      </div>

      <!-- 댓글 작성 -->
      <div v-if="auth.isLoggedIn" class="write-box">
        <div class="wds-label-1" style="font-weight: 700; margin-bottom: 8px">댓글 쓰기</div>
        <WdsField
          v-model="newComment"
          placeholder="질문이나 풀이 팁을 남겨보세요"
          @enter="submitComment"
        />
        <WdsButton
          variant="primary"
          size="large"
          block
          :disabled="submitting"
          @click="submitComment"
        >
          {{ submitting ? '등록 중…' : '댓글 등록' }}
        </WdsButton>
      </div>
      <div v-else class="login-nudge wds-body-2">
        댓글을 작성하려면
        <button class="nudge-link" @click="router.push('/login')">로그인</button>
        이 필요해요.
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.center-msg {
  display: flex; align-items: center; justify-content: center;
  padding: 60px 0; text-align: center;
}
.comment-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 4px;
}
.comment-card {
  padding: 14px 16px;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.comment-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.comment-author {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-normal);
}
.comment-content {
  color: var(--label-normal);
  line-height: 1.6;
  white-space: pre-wrap;
}
.delete-btn {
  margin-left: auto;
  background: none;
  border: none;
  font: var(--weight-medium) 12px/1 var(--font-sans);
  color: var(--label-assistive);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
}
.delete-btn:hover { color: var(--status-negative); background: var(--red-99); }
.write-box {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  background: var(--fill-alternative);
}
.login-nudge {
  margin-top: 8px;
  text-align: center;
  color: var(--label-assistive);
}
.nudge-link {
  background: none;
  border: none;
  color: var(--suql-accent);
  font: inherit;
  font-weight: var(--weight-semibold);
  cursor: pointer;
  text-decoration: underline;
}
</style>