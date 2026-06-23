<!-- 📄 src/components/common/OptionsBox.vue -->
<script setup>
import { computed } from 'vue'
import InlineTex from './InlineTex.vue'

// question_with_options(보기)는 OCR 원문이라 형태가 제각각 — 설명문, 단일 수식, ㄱ/ㄴ/ㄷ 나열형,
// ㉮/㉯/㉠/㉡/㉢ 같은 원문자 라벨(나열형 또는 같은 라벨을 여러 번 참조하는 식 전개형) 등이 섞여 있다.
//  1) ㄱ.ㄴ.ㄷ.ㄹ.ㅁ.ㅂ.(자모 풀어쓴 ᄀᄂᄃᄅᄆᄇ 변형 포함) 마커가 2개 이상이면 줄 단위 목록으로 분리.
//  2) 등장하는 모든 마커(ㄱ-ㅂ 계열 + ㉮㉯㉠㉡㉢)를 처음 나온 순서대로 1., 2., 3. ...으로 통일.
//     같은 마커가 다시 나오면(식 전개에서 ㉠을 두 번 참조하는 경우 등) 같은 번호를 그대로 재사용한다.
const props = defineProps({
  text: { type: String, default: '' },
})

const LIST_MARKER = /[ㄱㄴㄷㄹㅁㅂᄀᄂᄃᄅᄆᄇ]\s*\./g
const ANY_MARKER = /[ㄱㄴㄷㄹㅁㅂᄀᄂᄃᄅᄆᄇ]\s*\.|[㉮㉯㉠㉡㉢]/g

// 마커를 처음 등장 순서대로 1., 2., 3. ...로 치환. map을 공유하면 intro/items 전체에서 번호가 이어진다.
function unifyMarkers(text, map) {
  return text.replace(ANY_MARKER, (m) => {
    const key = m.replace(/[.\s]/g, '')
    if (!map.has(key)) map.set(key, map.size + 1)
    return `${map.get(key)}.`
  })
}

const parsed = computed(() => {
  const text = props.text || ''
  const markers = [...text.matchAll(LIST_MARKER)]
  const map = new Map()
  if (markers.length < 2) return { intro: unifyMarkers(text, map), items: [] }
  const intro = unifyMarkers(text.slice(0, markers[0].index).trim(), map)
  const items = markers.map((m, i) => {
    const start = m.index
    const end = i + 1 < markers.length ? markers[i + 1].index : text.length
    return unifyMarkers(text.slice(start, end).trim(), map)
  })
  return { intro, items }
})
</script>

<template>
  <div class="options-box">
    <p v-if="parsed.intro" class="options-intro"><InlineTex :text="parsed.intro" /></p>
    <ol v-if="parsed.items.length" class="options-list">
      <li v-for="(item, i) in parsed.items" :key="i"><InlineTex :text="item" /></li>
    </ol>
  </div>
</template>

<style scoped>
.options-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.options-intro {
  margin: 0;
}
.options-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
