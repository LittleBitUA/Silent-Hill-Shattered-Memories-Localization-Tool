<script setup lang="ts">
import { ref, onMounted } from 'vue'
import NewProjectModal from './NewProjectModal.vue'
import type { ProjectEntry } from '../api'
import { t } from '../i18n'

const projects = ref<ProjectEntry[]>([])
const showModal = ref(false)

async function reload() {
  const c = await window.api.configRead()
  projects.value = c.projects ?? []
}
onMounted(reload)

async function onProjectAdded() {
  showModal.value = false
  await reload()
}

async function removeProject(id: string) {
  if (!confirm(t('import.confirmRemove'))) return
  await window.api.configRemoveProject(id)
  await reload()
}

function platformName(p: string) { return t('platform.' + p) }

function shortPath(s: string) {
  if (!s) return ''
  const parts = s.split(/[\\/]/)
  if (parts.length <= 3) return s
  return parts.slice(0, 2).join('\\') + '\\…\\' + parts.slice(-2).join('\\')
}

function formatDate(iso?: string) {
  if (!iso) return t('common.dash')
  const d = new Date(iso)
  return d.toLocaleString()
}
</script>

<template>
<div class="page-shell">
  <div class="page-header">
    <h2>{{ t('import.title') }}</h2>
    <p class="page-sub" v-html="t('import.sub', {
      a: '<code>unpacked/</code>',
      b: '<code>wii_extract/</code>',
      c: '<code>psp_orig_extract/</code>',
    })"></p>
  </div>

  <div class="import-controls">
    <button class="btn btn-primary" @click="showModal = true">
      {{ t('import.add') }}
    </button>
    <span class="info" v-html="t('import.foundCount', { n: '<b>' + projects.length + '</b>' })"></span>
  </div>

  <div class="projects-list">
    <div v-if="!projects.length" class="empty">
      <b>{{ t('import.empty.line1') }}</b>
      <div>{{ t('import.empty.line2') }}</div>
    </div>
    <div v-else class="project-grid">
      <div v-for="p in projects" :key="p.id" class="project-card">
        <div class="project-head">
          <div class="project-logo" :class="p.platform">
            {{ p.platform.toUpperCase() }}
          </div>
          <div class="project-meta">
            <div class="project-name">{{ platformName(p.platform) }}</div>
            <div class="project-id">{{ p.id }}</div>
          </div>
          <button class="btn btn-danger" @click="removeProject(p.id)">
            ✕
          </button>
        </div>

        <div class="project-row">
          <div class="row-label">{{ t('import.row.iso') }}</div>
          <div class="row-value" :title="p.isoPath">{{ shortPath(p.isoPath) }}</div>
        </div>
        <div class="project-row" v-if="p.referencePath">
          <div class="row-label">{{ t('import.row.reference') }}</div>
          <div class="row-value" :title="p.referencePath">{{ shortPath(p.referencePath) }}</div>
        </div>
        <div class="project-row">
          <div class="row-label">{{ t('import.row.created') }}</div>
          <div class="row-value">{{ formatDate(p.createdAt) }}</div>
        </div>
        <div class="project-row">
          <div class="row-label">{{ t('import.row.extracted') }}</div>
          <div class="row-value">
            <span v-if="p.extractedAt" class="ok">{{ formatDate(p.extractedAt) }}</span>
            <span v-else class="warn">{{ t('import.notExtracted') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <NewProjectModal v-if="showModal" @done="onProjectAdded" @cancel="showModal = false" />
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

.page-header { padding: 24px 32px 8px; border-bottom: 1px solid var(--line-soft); }
.page-header h2 {
  margin: 0 0 6px; font-size: 14px; letter-spacing: 4px;
  color: var(--ice-bright); font-weight: 700;
}
.page-sub { margin: 0; font-size: 12px; color: var(--silver); line-height: 1.6; }
.page-sub code {
  font-family: var(--mono); font-size: 11px; color: var(--ice-bright);
  background: var(--bg-2); padding: 1px 5px; border: 1px solid var(--line);
}

.import-controls {
  padding: 18px 32px;
  display: flex; align-items: center; gap: 18px;
}
.import-controls .info { color: var(--silver); font-size: 12px; }
.import-controls .info b { color: var(--ice-bright); }

.projects-list {
  overflow-y: auto;
  padding: 0 32px 24px;
}

.empty {
  padding: 60px 0;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}
.empty b { color: var(--ice-bright); }

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 14px;
}

.project-card {
  background: linear-gradient(180deg, var(--bg-2) 0%, var(--bg-1) 100%);
  border: 1px solid var(--line);
  padding: 14px 16px;
}

.project-head {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
  padding-bottom: 10px; border-bottom: 1px solid var(--line-soft);
}
.project-logo {
  width: 56px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--display); font-weight: 800; font-size: 13px;
  letter-spacing: 2px; color: var(--ice-bright);
  background: var(--bg-3); border: 1px solid var(--line);
  text-shadow: 0 0 8px rgba(120, 200, 255, 0.3);
}
.project-meta { flex: 1; }
.project-name {
  font-size: 14px; font-weight: 700; letter-spacing: 1px;
  color: var(--pale);
}
.project-id {
  font-family: var(--mono); font-size: 10px; color: var(--muted);
  margin-top: 2px;
}

.project-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
  align-items: center;
}
.row-label {
  color: var(--silver);
  letter-spacing: 0.5px;
}
.row-value {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--pale);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-value .ok   { color: var(--good); }
.row-value .warn { color: var(--warn); font-style: italic; }

.btn-danger {
  background: rgba(255, 77, 109, 0.1);
  border-color: rgba(255, 77, 109, 0.4);
  color: var(--crit);
  padding: 4px 10px;
}
.btn-danger:hover {
  background: rgba(255, 77, 109, 0.25);
  color: #fff;
}
</style>
