<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { t } from '../i18n'

interface Hit {
  file: string
  hash: string
  body: string
  hasUa: boolean
}

const FILES = [
  'translate_shared.txt',
  'translate_ps2_only.txt',
  'translate_wii_only.txt',
  'translate_psp_only.txt',
]

const query = ref('')
const fileFilter = ref<'all' | string>('all')
const statusFilter = ref<'all' | 'translated' | 'untranslated'>('all')
const loading = ref(false)
const allBlocks = ref<Hit[]>([])

function parseBlocks(file: string, text: string): Hit[] {
  const out: Hit[] = []
  let curId: string | null = null
  let body: string[] = []
  const flush = () => {
    if (curId !== null) {
      const joined = body.join('\n').replace(/\n+$/, '')
      out.push({ file, hash: curId, body: joined, hasUa: /[Ѐ-ӿ]/.test(joined) })
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
      if (curId !== null && body.length) flush()
    } else if (curId !== null) {
      body.push(line)
    }
  }
  flush()
  return out
}

async function loadAll() {
  loading.value = true
  const all: Hit[] = []
  for (const name of FILES) {
    try {
      const text = await window.api.translationRead(name)
      all.push(...parseBlocks(name, text))
    } catch (e) { /* file missing — skip */ }
  }
  allBlocks.value = all
  loading.value = false
}

onMounted(loadAll)

const results = computed<Hit[]>(() => {
  const q = query.value.trim().toLowerCase()
  return allBlocks.value.filter(h => {
    if (fileFilter.value !== 'all' && h.file !== fileFilter.value) return false
    if (statusFilter.value === 'translated' && !h.hasUa) return false
    if (statusFilter.value === 'untranslated' && h.hasUa) return false
    if (!q) return true
    return h.body.toLowerCase().includes(q) || h.hash.includes(q)
  })
})

const stats = computed(() => {
  const total = allBlocks.value.length
  const tr = allBlocks.value.filter(b => b.hasUa).length
  return { total, tr, shown: results.value.length }
})

function shortLabel(file: string) {
  if (file === 'translate_shared.txt') return 'SHARED'
  if (file === 'translate_ps2_only.txt') return 'PS2'
  if (file === 'translate_wii_only.txt') return 'WII'
  if (file === 'translate_psp_only.txt') return 'PSP'
  return file
}

function highlight(text: string): string {
  const q = query.value.trim()
  if (!q) return escapeHtml(text)
  const re = new RegExp(escapeRegex(q), 'gi')
  return escapeHtml(text).replace(re, m => `<mark>${escapeHtml(m)}</mark>`)
}
function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;' }[c]!))
}
function escapeRegex(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>

<template>
<div class="page-shell search-shell">
  <div class="page-header">
    <h2>{{ t('search.title') }}</h2>
    <p class="page-sub">
      {{ t('search.sub') }}
      <span v-html="t('search.foundOf', {
        shown: '<b>' + stats.shown.toLocaleString() + '</b>',
        total: '<b>' + stats.total.toLocaleString() + '</b>',
        tr: '<b>' + stats.tr.toLocaleString() + '</b>',
      })"></span>
    </p>
  </div>

  <div class="toolbar search-toolbar">
    <div class="search-box">
      <input v-model="query" :placeholder="t('search.placeholder')" autofocus />
      <span class="ico">⌕</span>
    </div>
    <div class="tool-field">
      <span class="label">{{ t('search.fileLabel') }}</span>
      <div class="combo">
        <select v-model="fileFilter">
          <option value="all">{{ t('search.allFiles') }}</option>
          <option v-for="f in FILES" :key="f" :value="f">{{ shortLabel(f) }}  ({{ f }})</option>
        </select>
      </div>
    </div>
    <div class="tool-field">
      <span class="label">{{ t('search.statusLabel') }}</span>
      <div class="combo">
        <select v-model="statusFilter">
          <option value="all">{{ t('search.statusAll') }}</option>
          <option value="translated">{{ t('search.statusTranslated') }}</option>
          <option value="untranslated">{{ t('search.statusUntranslated') }}</option>
        </select>
      </div>
    </div>
  </div>

  <div class="search-results">
    <div v-if="loading" class="search-empty">{{ t('search.loading') }}</div>
    <div v-else-if="!results.length" class="search-empty">
      {{ t('search.empty') }}
    </div>
    <div v-else class="results-list">
      <div v-for="(r, i) in results.slice(0, 500)" :key="r.file + ':' + r.hash + ':' + i"
           class="result-row">
        <div class="result-meta">
          <span class="result-file" :class="'tag-' + shortLabel(r.file).toLowerCase()">
            {{ shortLabel(r.file) }}
          </span>
          <span class="result-hash">{{ r.hash }}</span>
          <span class="result-status" :class="{ tr: r.hasUa, un: !r.hasUa }">
            {{ r.hasUa ? t('search.dotTranslated') : t('search.dotUntranslated') }}
          </span>
        </div>
        <div class="result-body" v-html="highlight(r.body)"></div>
      </div>
      <div v-if="results.length > 500" class="search-empty">
        {{ t('search.truncated', { shown: 500, total: results.length.toLocaleString() }) }}
      </div>
    </div>
  </div>
</div>
</template>

<style scoped>
.page-shell {
  height: 100%;
  display: grid;
  grid-template-rows: auto auto 1fr;
  overflow: hidden;
  background: #000;
}

.page-header {
  padding: 24px 32px 8px;
  border-bottom: 1px solid var(--line-soft);
}
.page-header h2 {
  margin: 0 0 6px;
  font-size: 14px;
  letter-spacing: 4px;
  color: var(--ice-bright);
  font-weight: 700;
}
.page-sub {
  margin: 0;
  font-size: 12px;
  color: var(--silver);
  letter-spacing: 0.3px;
}
.page-sub b { color: var(--pale); font-weight: 600; }

.search-toolbar {
  padding: 14px 32px;
  gap: 16px;
}
.search-toolbar .search-box { margin-left: 0; flex: 1; max-width: 480px; }

.search-results {
  overflow-y: auto;
  padding: 0 32px 24px;
}
.search-empty {
  padding: 60px 0;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.5px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
}

.result-row {
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-left: 2px solid var(--line-strong);
  padding: 12px 16px;
}
.result-row:hover {
  border-left-color: var(--ice);
  background: var(--bg-row-hover);
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.result-file {
  padding: 1px 7px;
  background: var(--bg-3);
  color: var(--ice-bright);
  border: 1px solid var(--line);
  font-weight: 600;
  letter-spacing: 1px;
}
.result-file.tag-ps2  { color: #b8d4ee; border-color: #2c5878; }
.result-file.tag-wii  { color: #b8eed4; border-color: #2c7858; }
.result-file.tag-psp  { color: #eed4b8; border-color: #785828; }
.result-file.tag-shared { color: #d4b8ee; border-color: #58287c; }

.result-hash { color: var(--silver); }
.result-status.tr { color: var(--good); }
.result-status.un { color: var(--muted); font-style: italic; }

.result-body {
  font-family: var(--display);
  font-size: 13px;
  color: var(--pale);
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.result-body :deep(mark) {
  background: rgba(120, 200, 255, 0.25);
  color: var(--ice-bright);
  padding: 0 2px;
}
</style>
