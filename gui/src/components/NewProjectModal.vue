<script setup lang="ts">
import { ref, computed } from 'vue'

const emit = defineEmits<{
  (e: 'done', project: any): void
  (e: 'cancel'): void
}>()

type Step = 'platform' | 'sources' | 'extract'
const step = ref<Step>('platform')

const platform = ref<'ps2' | 'wii' | 'psp' | null>(null)
const isoPath = ref('')
const referencePath = ref('')
const log = ref<{ kind: string; text: string }[]>([])
const extractRunning = ref(false)
const extractDone = ref(false)
const extractFailed = ref(false)

import { t } from '../i18n'

const platforms = computed(() => [
  { id: 'ps2' as const, name: t('platform.ps2'), code: 'NTSC-U  ·  SLUS-218.99',
    note: t('modal.note.ps2') },
  { id: 'wii' as const, name: t('platform.wii'), code: 'NTSC-U  ·  R5WEA4',
    note: t('modal.note.wii') },
  { id: 'psp' as const, name: t('platform.psp'), code: 'NTSC-U  ·  ULUS',
    note: t('modal.note.psp') },
])

function selectPlatform(id: 'ps2' | 'wii' | 'psp') {
  platform.value = id
  step.value = 'sources'
}

async function pickIso() {
  const p = await window.api.pickFile({
    title: 'Pick source disc image',
    filters: [{ name: 'Disc images', extensions: ['iso', 'rvz', 'wbfs'] }],
  })
  if (p) isoPath.value = p
}

async function pickReference() {
  const p = await window.api.pickFile({
    title: 'Pick reference disc image (optional)',
    filters: [{ name: 'Disc images', extensions: ['iso', 'rvz'] }],
  })
  if (p) referencePath.value = p
}

const canExtract = computed(() => platform.value && isoPath.value)

async function runExtract() {
  if (!canExtract.value) return
  step.value = 'extract'
  log.value = []
  extractRunning.value = true
  extractDone.value = false
  extractFailed.value = false

  const entry = await window.api.configAddProject({
    platform: platform.value!,
    isoPath: isoPath.value,
    referencePath: referencePath.value || undefined,
    displayName: `${platform.value!.toUpperCase()} :: ${isoPath.value.split(/[\\/]/).pop()}`,
  })

  window.api.onExtractLine((p: any) => {
    if (p.kind === 'done') {
      extractRunning.value = false
      if (p.code === 0) { extractDone.value = true } else { extractFailed.value = true }
      window.api.configMarkExtracted(entry.id)
      log.value.push({ kind: p.code === 0 ? 'done' : 'fail',
                       text: p.code === 0
                         ? `\n=== EXTRACT DONE :: exit 0 ===\n`
                         : `\n!!! EXTRACT FAILED :: exit ${p.code} !!!\n` })
    } else {
      for (const part of p.line.split(/\r?\n/)) {
        if (part) log.value.push({ kind: p.kind, text: part })
      }
    }
  })
  await window.api.extractRun(entry)

  // emit done so parent picks up the new project (even on partial failure)
  if (extractDone.value || extractFailed.value) {
    // wait a sec for user to see
  }
}

function finish() {
  emit('done', { platform: platform.value })
}
function back() {
  if (step.value === 'sources') step.value = 'platform'
}
</script>

<template>
  <div class="modal-backdrop">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">{{ t('modal.title') }}</div>
        <div class="modal-step">{{ t('modal.step', { n: step === 'platform' ? '1' : step === 'sources' ? '2' : '3' }) }}</div>
      </div>

      <!-- Step 1: pick platform -->
      <div v-if="step === 'platform'" class="modal-body">
        <p class="modal-prompt">{{ t('modal.prompt.pickPlatform') }}</p>
        <div class="platform-cards">
          <button v-for="p in platforms" :key="p.id"
                  class="platform-card-btn" @click="selectPlatform(p.id)">
            <div class="label">{{ t('modal.platformLabel') }}</div>
            <div class="name">{{ p.name }}</div>
            <div class="code">{{ p.code }}</div>
            <div class="note">{{ p.note }}</div>
          </button>
        </div>
      </div>

      <!-- Step 2: pick ISO -->
      <div v-else-if="step === 'sources'" class="modal-body">
        <p class="modal-prompt" v-html="t('modal.prompt.sources', {
          name: '<b>' + (platforms.find(p => p.id === platform)?.name ?? '') + '</b>',
        })"></p>

        <div class="picker">
          <div class="picker-label">{{ t('modal.sourceLabel') }}</div>
          <div class="picker-row">
            <input type="text" v-model="isoPath" placeholder="(none)" readonly />
            <button class="btn" @click="pickIso">PICK</button>
          </div>
          <p class="hint">{{ platforms.find(p => p.id === platform)?.note }}</p>
        </div>

        <div class="picker" v-if="platform === 'wii' || platform === 'psp'">
          <div class="picker-label">{{ t('modal.referenceLabel') }}</div>
          <div class="picker-row">
            <input type="text" v-model="referencePath" :placeholder="t('modal.referencePlaceholder')" readonly />
            <button class="btn" @click="pickReference">PICK</button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn" @click="back">{{ t('modal.back') }}</button>
          <button class="btn btn-primary" :disabled="!canExtract" @click="runExtract">{{ t('modal.extract') }}</button>
        </div>
      </div>

      <!-- Step 3: extract -->
      <div v-else class="modal-body">
        <p class="modal-prompt" v-html="t('modal.prompt.extracting', {
          name: '<b>' + (platforms.find(p => p.id === platform)?.name ?? '') + '</b>',
        })"></p>
        <pre class="extract-log">
<span v-for="(l, i) in log" :key="i" :class="'line-' + l.kind">{{ l.text }}
</span></pre>
        <div class="modal-actions" v-if="!extractRunning">
          <button class="btn btn-primary" @click="finish">{{ extractFailed ? t('modal.continueAnyway') : t('modal.continue') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  width: 920px;
  max-width: 96vw;
  max-height: 90vh;
  background: linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%);
  border: 1px solid var(--ice);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.85), 0 0 80px rgba(120, 200, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 28px;
  border-bottom: 1px solid var(--line);
  background: var(--bg-2);
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 4px;
  color: var(--ice-bright);
  text-shadow: 0 0 8px rgba(120, 200, 255, 0.3);
}

.modal-step {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--silver);
}

.modal-body {
  padding: 28px;
  overflow-y: auto;
}

.modal-prompt {
  font-size: 14px;
  letter-spacing: 1.5px;
  color: var(--pale);
  margin: 0 0 22px;
}

.platform-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.platform-card-btn {
  text-align: left;
  background: linear-gradient(160deg, var(--bg-2) 0%, var(--bg-1) 100%);
  border: 1px solid var(--line);
  padding: 20px;
  cursor: pointer;
  color: var(--pale);
  transition: all .15s;
}
.platform-card-btn:hover {
  border-color: var(--ice);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 24px rgba(120,200,255,0.15);
}
.platform-card-btn .label {
  font-size: 10px; letter-spacing: 2.5px; color: var(--silver); margin-bottom: 6px;
}
.platform-card-btn .name {
  font-size: 22px; font-weight: 700; letter-spacing: 3px;
  color: var(--ice-bright); margin-bottom: 4px;
}
.platform-card-btn .code {
  font-family: var(--mono); font-size: 11px; color: var(--silver); margin-bottom: 12px;
}
.platform-card-btn .note {
  font-size: 12px; color: var(--silver); line-height: 1.5;
}

.picker { margin-bottom: 22px; }
.picker-label {
  font-size: 11px; letter-spacing: 2.5px; color: var(--silver);
  margin-bottom: 8px; font-weight: 700;
}
.picker-row {
  display: flex; gap: 8px; align-items: stretch;
}
.picker-row input {
  flex: 1; background: var(--bg-2); border: 1px solid var(--line);
  color: var(--pale); padding: 10px 14px; font-family: var(--mono); font-size: 12px;
}
.hint {
  margin: 8px 0 0; font-size: 12px; color: var(--silver); font-style: italic;
}

.modal-actions {
  display: flex; gap: 12px; justify-content: flex-end;
  margin-top: 28px;
}

.extract-log {
  background: #04090d;
  border: 1px solid var(--line);
  padding: 16px 20px;
  font-family: var(--mono);
  font-size: 12px;
  line-height: 1.5;
  height: 320px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--pale);
}
.extract-log .line-out  { color: var(--pale); }
.extract-log .line-err  { color: var(--warn); }
.extract-log .line-info { color: var(--ice); }
.extract-log .line-done { color: var(--good); font-weight: bold; }
.extract-log .line-fail { color: var(--crit); font-weight: bold; }
</style>
