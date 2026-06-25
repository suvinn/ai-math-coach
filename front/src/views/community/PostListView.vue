<!-- 📄 src/views/community/PostListView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import Toast from '@/components/common/Toast.vue'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()
const { toast, showToast } = useToast()

const problemId = route.params.problem_id
const loading   = ref(true)
const data      = ref(null)

const showForm   = ref(false)
const newTitle   = ref('')
const newContent = ref('')
const submitting = ref(false)

onMounted(async () => {
  await fetchPosts()
})

async function fetchPosts() {
  loading.value = true
  try {
    data.value = unwrap(await api.get(`/problems/${problemId}/posts`))
  } catch {
    showToast('게시글을 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
}

async function submitPost() {
  if (!newTitle.value.trim() || !newContent.value.trim()) {
    showToast('제목과 내용을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  submitting.value = true
  try {
    const created = unwrap(
      await api.post(`/problems/${problemId}/posts`, {
        title:   newTitle.value.trim(),
        content: newContent.value.trim(),
      })
    )
    data.value.posts.unshift(created)
    data.value.post_count += 1
    newTitle.value   = ''
    newContent.value = ''
    showForm.value   = false
    showToast('게시글이 등록됐어요', 'positive', 'circle-check')
  } catch (e) {
    const msg = e?.response?.data?.message || '게시글 작성에 실패했어요'
    showToast(msg, 'negative', 'circle-exclamation')
  } finally {
    submitting.value = false
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}
</script>

<template>
  <FocusShell title="토론" :toast="toast" @back="router.back()">
    <Toast :toast="toast" />

    <div v-if="loading" class="center-msg assistive">불러오는 중…</div>

    <template v-else-if="data">
      <div class="list-head">
        <span class="wds-label-1 head-count">게시글 {{ data.post_count }}개</span>
        <WdsButton
          v-if="auth.isLoggedIn && !showForm"
          variant="primary"
          size="medium"
          icon-left="plus"
          @click="showForm = true"
        >
          글쓰기
        </WdsButton>
      </div>

      <!-- 게시글 작성 폼 -->
      <div v-if="showForm" class="write-box">
        <div class="wds-label-1" style="font-weight:700; margin-bottom:4px">새 게시글</div>
        <WdsField v-model="newTitle" placeholder="제목을 입력해주세요" />
        <WdsField v-model="newContent" placeholder="내용을 입력해주세요" :multiline="true" />
        <div style="display:flex; gap:8px;">
          <WdsButton variant="secondary" size="large" block @click="showForm = false">
            취소
          </WdsButton>
          <WdsButton variant="primary" size="large" block :disabled="submitting" @click="submitPost">
            {{ submitting ? '등록 중…' : '등록하기' }}
          </WdsButton>
        </div>
      </div>

      <!-- 게시글 목록 -->
      <div v-if="data.posts.length" class="stack-12">
        <div
          v-for="p in data.posts"
          :key="p.id"
          class="post-card"
          @click="router.push(`/problems/${problemId}/posts/${p.id}`)"
        >
          <div class="post-title">{{ p.title }}</div>
          <div class="post-meta">
            <span class="post-author">{{ p.name || p.username }}</span>
            <span class="wds-caption-1 assistive">{{ formatDate(p.created_at) }}</span>
            <span class="comment-count">
              <WdsIcon name="bubble" :size="12" color="var(--label-assistive)" />
              {{ p.comment_count }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="center-msg assistive">
        아직 게시글이 없어요. 첫 번째로 질문해보세요!
      </div>

      <div v-if="!auth.isLoggedIn" class="login-nudge wds-body-2">
        게시글을 작성하려면
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
.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.head-count {
  font-size: 16px;
  font-weight: 700;
  color: var(--label-normal);
}
.post-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--line-normal-normal);
  background: var(--background-normal-normal, #fff);
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.post-card:hover {
  background: var(--fill-normal, #f7f7f7);
}
.post-title {
  font: var(--weight-semibold) 15px/1.4 var(--font-sans);
  color: var(--label-normal);
}
.post-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.post-author {
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  color: var(--label-alternative);
}
.comment-count {
  display: flex;
  align-items: center;
  gap: 3px;
  font: var(--weight-regular) 12px/1 var(--font-sans);
  color: var(--label-assistive);
  margin-left: auto;
}
.write-box {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--line-normal-normal);
  background: var(--background-normal-normal, #fff);
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