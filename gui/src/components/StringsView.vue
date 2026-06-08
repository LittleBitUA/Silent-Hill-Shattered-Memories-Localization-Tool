<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import logoUrl from '../assets/Logo.png'
import { t } from '../i18n'

type Platform = 'ps2' | 'psp' | 'wii'

const props = defineProps<{ platform: Platform }>()
const emit = defineEmits<{
  (e: 'stats', total: number, translated: number): void
  (e: 'dirty', dirty: boolean): void
}>()

interface Block { hash: string; en: string; ua: string }

const fileChoice = ref<'shared' | 'only'>('shared')
const search = ref('')
const blocks = ref<Block[]>([])
const activeIdx = ref(0)
const editingIdx = ref<number | null>(null)
const dirty = ref(false)

// Parse a .txt blocks file into [{hash, en, ua}] using the source EN map
// (we don't have a separate EN file — show EN from the entry text where it
// still equals English, otherwise fall back to the same text as both).
const ENGLISH_MAP = new Map<string, string>()      // hash -> EN

function parseTxt(text: string): Block[] {
  const out: Block[] = []
  let curId: string | null = null
  let body: string[] = []
  const flush = () => {
    if (curId !== null) {
      const ua_or_en = body.join('\n').replace(/\n+$/, '')
      const en = ENGLISH_MAP.get(curId) ?? ''
      const hasUa = /[Ѐ-ӿ]/.test(ua_or_en)
      out.push({ hash: curId, en: en || (hasUa ? '' : ua_or_en), ua: hasUa ? ua_or_en : '' })
    }
    curId = null; body = []
  }
  for (const line of text.split('\n')) {
    if (line.startsWith('# - ')) {
      flush()
      curId = line.slice(4).trim().split(/\s/)[0]
    } else if (line.startsWith('#')) {
      continue
    } else if (line.trim() === '') {
      if (curId !== null && body.length) {
        flush()
      }
    } else if (curId !== null) {
      body.push(line)
    }
  }
  flush()
  return out
}

async function buildEnglishMap() {
  if (ENGLISH_MAP.size > 0) return
  const text = await window.api.translationRead('translate_shared.txt')
  for (const b of parseTxt(text)) {
    if (!b.ua) ENGLISH_MAP.set(b.hash, b.en)
  }
}

const fileName = computed(() => {
  if (fileChoice.value === 'only') return `translate_${props.platform}_only.txt`
  return 'translate_shared.txt'
})

async function reload() {
  if (ENGLISH_MAP.size === 0) await buildEnglishMap()
  const text = await window.api.translationRead(fileName.value)
  blocks.value = parseTxt(text)
  activeIdx.value = 0
  editingIdx.value = null
  emitStats()
}

function emitStats() {
  const total = blocks.value.length
  const tr = blocks.value.filter(b => /[Ѐ-ӿ]/.test(b.ua)).length
  emit('stats', total, tr)
}

watch(() => [props.platform, fileChoice.value], reload, { immediate: false })

onMounted(reload)

const filtered = computed(() => {
  if (!search.value) return blocks.value
  const q = search.value.toLowerCase()
  return blocks.value.filter(b =>
    b.en.toLowerCase().includes(q) ||
    b.ua.toLowerCase().includes(q) ||
    b.hash.includes(q),
  )
})

function seqId(idx: number) { return String(idx + 1).padStart(4, '0') }

function startEdit(idx: number) {
  activeIdx.value = idx
  editingIdx.value = idx
  nextTick(() => {
    const el = document.querySelector<HTMLInputElement>('.cell-ua input')
    el?.focus(); el?.select()
  })
}

function cancelEdit() {
  editingIdx.value = null
}

async function commitEdit(idx: number, newUa: string) {
  blocks.value[idx].ua = newUa
  editingIdx.value = null
  dirty.value = true
  emit('dirty', true)
  emitStats()
  await saveFile()
}

async function saveFile() {
  // Serialize back to the block format (header comments are lost; we emit
  // a minimal header).
  const lines: string[] = []
  lines.push(`# ${fileName.value} — auto-edited by Localization Tool`)
  lines.push('')
  for (const b of blocks.value) {
    lines.push(`# - ${b.hash}`)
    // Prefer UA when present, otherwise keep EN (so file stays valid).
    const body = b.ua || b.en
    lines.push(body)
    lines.push('')
  }
  const text = lines.join('\n')
  await window.api.translationSave(fileName.value, text)
  dirty.value = false
  emit('dirty', false)
}

const fileOptions = computed(() => [
  { value: 'shared', label: t('strings.fileShared') },
  { value: 'only',   label: t('strings.fileOnly', { p: props.platform, P: props.platform.toUpperCase() }) },
])
</script>

<template>
<div class="strings-shell">
  <div class="hero">
    <img :src="logoUrl" alt="Shattered Memories" />
  </div>

  <div class="toolbar">
    <div class="tool-field">
      <span class="label">{{ t('strings.fileLabel') }}</span>
      <div class="combo">
        <select v-model="fileChoice">
          <option v-for="o in fileOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>
    </div>
    <div class="tool-field">
      <span class="label">{{ t('strings.encodingLabel') }}</span>
      <div class="combo">
        <select disabled><option>UTF-16 LE</option></select>
      </div>
    </div>
    <div class="search-box">
      <input v-model="search" :placeholder="t('strings.searchPlaceholder')" />
      <span class="ico">⌕</span>
    </div>
  </div>

  <div class="table-pane">
    <div class="table-headers">
      <div>{{ t('strings.thId') }}</div>
      <div>{{ t('strings.thOriginal') }}</div>
      <div>{{ t('strings.thTranslation') }}</div>
    </div>
    <div class="table-body">
      <div v-for="(b, idx) in filtered" :key="b.hash"
           class="table-row" :class="{ active: idx === activeIdx }"
           @click="activeIdx = idx"
           @dblclick="startEdit(idx)">
        <div class="cell-id">{{ seqId(idx) }}</div>
        <div class="cell-en">{{ b.en || t('common.dash') }}</div>
        <div class="cell-ua" :class="{ untranslated: !b.ua }">
          <input v-if="editingIdx === idx"
                 :value="b.ua"
                 @keydown.enter="commitEdit(idx, ($event.target as HTMLInputElement).value)"
                 @keydown.esc="cancelEdit"
                 @blur="commitEdit(idx, ($event.target as HTMLInputElement).value)" />
          <span v-else>{{ b.ua || t('strings.untranslated') }}</span>
        </div>
      </div>
      <div v-if="!filtered.length" style="padding: 40px; text-align: center; color: var(--muted);">
        {{ t('strings.empty') }}
      </div>
    </div>
  </div>
</div>
</template>
