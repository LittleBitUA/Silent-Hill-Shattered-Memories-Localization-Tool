<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { t } from '../i18n'

type Platform = 'ps2' | 'psp' | 'wii'
const props = defineProps<{ platform: Platform }>()

const log = ref<{ kind: string; text: string }[]>([])
const running = ref(false)
const lastCode = ref<number | null>(null)
const outputPaths = ref<Record<string, string>>({})
const logEl = ref<HTMLPreElement | null>(null)

interface AnalysisHit { hash: string; en: string; ua: string; delta: number }
const analysisLoading = ref(false)
const analysisResults = ref<AnalysisHit[]>([])
const analysisStats = ref<{ total: number; longer: number; totalDelta: number } | null>(null)
const analysisError = ref<string | null>(null)

function parseBlocks(text: string): Map<string, string> {
  const out = new Map<string, string>()
  let curId: string | null = null
  let body: string[] = []
  const flush = () => {
    if (curId !== null) out.set(curId, body.join('\n').replace(/\n+$/, ''))
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

function originalsKey(p: Platform): string { return p === 'ps2' ? 'ps2_ui' : p }

async function runAnalysis() {
  analysisLoading.value = true
  analysisError.value = null
  analysisResults.value = []
  analysisStats.value = null
  try {
    const [sharedTxt, onlyTxt, originals] = await Promise.all([
      window.api.translationRead('translate_shared.txt').catch(() => ''),
      window.api.translationRead(`translate_${props.platform}_only.txt`).catch(() => ''),
      window.api.originalsRead(originalsKey(props.platform)),
    ])
    if (!originals || Object.keys(originals).length === 0) {
      analysisError.value = t('export.analysisErr')
      return
    }
    const shared = parseBlocks(sharedTxt)
    const only = parseBlocks(onlyTxt)
    const hasUa = (s: string) => /[Ѐ-ӿ]/.test(s)

    let translated = 0, longer = 0, totalDelta = 0
    const results: AnalysisHit[] = []
    for (const [hash, en] of Object.entries(originals)) {
      const ua = only.get(hash) ?? shared.get(hash) ?? ''
      if (!ua || !hasUa(ua)) continue
      translated++
      const delta = ua.length - en.length
      if (delta > 0) {
        longer++; totalDelta += delta
        results.push({ hash, en, ua, delta })
      }
    }
    results.sort((a, b) => b.delta - a.delta)
    analysisResults.value = results
    analysisStats.value = { total: translated, longer, totalDelta }
  } finally {
    analysisLoading.value = false
  }
}

onMounted(async () => {
  outputPaths.value = await window.api.buildOutputPaths()
  window.api.onBuildLine((p) => {
    const parts = (p.line ?? '').split(/\r?\n/)
    for (const part of parts) if (part) log.value.push({ kind: p.kind, text: part })
    scrollToEnd()
  })
  window.api.onBuildDone((p) => {
    running.value = false
    lastCode.value = p.code
    log.value.push({
      kind: p.code === 0 ? 'done' : 'fail',
      text: p.code === 0
        ? t('export.buildDone')
        : t('export.buildFailed', { code: p.code }),
    })
    scrollToEnd()
  })
})

function scrollToEnd() {
  requestAnimationFrame(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

async function startBuild() {
  if (running.value) return
  log.value = []
  lastCode.value = null
  running.value = true
  log.value.push({ kind: 'info', text: t('export.logHeader', { platform: props.platform }) })
  try {
    await window.api.buildStart(props.platform)
  } catch (e: any) {
    running.value = false
    log.value.push({ kind: 'fail', text: t('export.spawnError', { msg: e?.message ?? String(e) }) })
  }
}

const outputPath = computed(() => outputPaths.value[props.platform] ?? '')
const platformLabel = computed(() => t('export.platLabel.' + props.platform))

function clearLog() { log.value = []; lastCode.value = null }
function openOutputFolder() {
  if (outputPath.value) window.api.buildShowInFolder(outputPath.value)
}
</script>

<template>
<div class="page-shell">
  <div class="page-header">
    <h2>{{ t('export.title') }}</h2>
    <p class="page-sub" v-html="t('export.sub', {
      label: '<b>' + platformLabel + '</b>',
      script: '<code>tool/build_ua_' + platform + '.py</code>',
      shared: '<code>translate_shared.txt</code>',
      only: '<code>translate_' + platform + '_only.txt</code>',
    })"></p>
  </div>

  <div class="export-controls">
    <button class="btn btn-primary" :disabled="running" @click="startBuild">
      {{ running ? t('export.building') : t('export.runBuild') }}
    </button>
    <button class="btn" :disabled="running || !log.length" @click="clearLog">
      {{ t('export.clearLog') }}
    </button>
    <div class="export-output">
      <div class="picker-label">{{ t('export.outputLabel') }}</div>
      <code class="output-path">{{ outputPath || t('export.outputPending') }}</code>
      <button class="btn" :disabled="!outputPath" @click="openOutputFolder">
        {{ t('export.openFolder') }}
      </button>
    </div>
  </div>

  <details class="analysis-card">
    <summary>
      <span class="card-title">{{ t('export.analysisTitle') }}</span>
      <span class="card-hint">{{ t('export.analysisHint') }}</span>
    </summary>

    <div class="analysis-body">
      <div class="analysis-controls">
        <button class="btn" :disabled="analysisLoading" @click="runAnalysis">
          {{ analysisLoading ? t('export.analysisRunning') : t('export.analysisRun') }}
        </button>
        <span v-if="analysisStats" class="analysis-stats">
          {{ t('export.analysisTotalRows', { n: analysisStats.total.toLocaleString() }) }}
          <span class="dot">·</span>
          {{ t('export.analysisLongerRows', { n: analysisStats.longer.toLocaleString() }) }}
          <span class="dot">·</span>
          <span v-html="t('export.analysisOversum', { n: analysisStats.totalDelta.toLocaleString() })"></span>
        </span>
      </div>

      <div v-if="analysisError" class="analysis-err">{{ analysisError }}</div>

      <div v-else-if="analysisStats && !analysisResults.length" class="analysis-empty">
        {{ t('export.analysisEmpty') }}
      </div>

      <div v-else-if="analysisResults.length" class="analysis-table-wrap">
        <table class="analysis-table">
          <thead>
            <tr>
              <th class="col-hash">{{ t('export.analysisThHash') }}</th>
              <th class="col-en">{{ t('export.analysisThEn') }}</th>
              <th class="col-ua">{{ t('export.analysisThUa') }}</th>
              <th class="col-delta">{{ t('export.analysisThDelta') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in analysisResults.slice(0, 100)" :key="r.hash">
              <td class="col-hash mono">{{ r.hash }}</td>
              <td class="col-en">{{ r.en }}</td>
              <td class="col-ua">{{ r.ua }}</td>
              <td class="col-delta">+{{ r.delta }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="analysisResults.length > 100" class="analysis-foot">
          {{ t('export.analysisShownOf', { shown: 100, total: analysisResults.length.toLocaleString() }) }}
        </div>
      </div>
    </div>
  </details>

  <pre ref="logEl" class="extract-log build-log">
<span v-if="!log.length" class="line-muted">{{ t('export.logPlaceholder') }}</span><span v-for="(l, i) in log" :key="i" :class="'line-' + l.kind">{{ l.text }}
</span></pre>
</div>
</template>

<style scoped>
.page-shell {
  height: 100%;
  display: grid;
  grid-template-rows: auto auto auto 1fr;
  overflow: hidden;
  background: #000;
  padding-bottom: 20px;
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
  line-height: 1.6;
}
.page-sub b { color: var(--pale); }
.page-sub code {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ice-bright);
  background: var(--bg-2);
  padding: 1px 5px;
  border: 1px solid var(--line);
}

.export-controls {
  padding: 18px 32px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.export-output {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.export-output .picker-label {
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--silver);
}
.output-path {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ice);
  background: var(--bg-2);
  padding: 6px 12px;
  border: 1px solid var(--line);
  max-width: 460px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.build-log {
  margin: 0 32px;
  height: auto;
  flex: 1;
  min-height: 200px;
}

.line-muted { color: var(--muted); font-style: italic; }

/* ---- Slot analysis -------------------------------------------------- */

.analysis-card {
  margin: 0 32px 16px;
  background: linear-gradient(180deg, var(--bg-2) 0%, var(--bg-1) 100%);
  border: 1px solid var(--line);
}
.analysis-card > summary {
  list-style: none;
  cursor: pointer;
  padding: 12px 18px;
  display: flex;
  align-items: center;
  gap: 16px;
  user-select: none;
}
.analysis-card > summary::-webkit-details-marker { display: none; }
.analysis-card > summary::before {
  content: '▸';
  color: var(--ice);
  font-size: 11px;
  transition: transform .15s;
}
.analysis-card[open] > summary::before { transform: rotate(90deg); }
.analysis-card > summary:hover { background: var(--bg-row-hover); }
.analysis-card .card-title {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 3px;
  color: var(--ice);
  font-weight: 700;
  flex-shrink: 0;
}
.analysis-card .card-hint {
  font-size: 12px;
  color: var(--silver);
  font-style: italic;
}

.analysis-body { padding: 6px 18px 16px; }

.analysis-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 6px 0 12px;
}
.analysis-stats {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--silver);
  letter-spacing: 0.3px;
}
.analysis-stats .dot { color: var(--muted); margin: 0 4px; }
.analysis-stats :deep(b) { color: var(--warn); font-weight: 700; }

.analysis-err, .analysis-empty {
  padding: 12px;
  font-size: 12px;
  border: 1px solid var(--line);
}
.analysis-err   { color: var(--warn); border-color: rgba(217, 168, 107, 0.5); }
.analysis-empty { color: var(--good); border-color: rgba(110, 217, 141, 0.4); }

.analysis-table-wrap {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid var(--line);
}
.analysis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.analysis-table th {
  text-align: left;
  font-size: 10px;
  letter-spacing: 1.5px;
  color: var(--silver);
  background: var(--bg-3);
  border-bottom: 1px solid var(--line-strong);
  padding: 6px 10px;
  font-weight: 500;
  position: sticky;
  top: 0;
}
.analysis-table td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--line-soft);
  color: var(--pale);
  vertical-align: top;
}
.analysis-table .col-hash {
  width: 80px;
  font-family: var(--mono);
  color: var(--ice);
  font-size: 11px;
}
.analysis-table .col-en, .analysis-table .col-ua {
  font-size: 12px;
  word-break: break-word;
}
.analysis-table .col-ua { color: var(--ice-bright); }
.analysis-table .col-delta {
  width: 60px;
  text-align: right;
  font-family: var(--mono);
  color: var(--warn);
  font-weight: 700;
}

.analysis-foot {
  padding: 8px 12px;
  font-size: 11px;
  color: var(--muted);
  font-style: italic;
  text-align: center;
}
</style>
