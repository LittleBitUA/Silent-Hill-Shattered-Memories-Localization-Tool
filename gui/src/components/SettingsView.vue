<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import type { StatsMap, GlyphInfo } from '../api'
import { t } from '../i18n'

const projectRoot = ref('')
const stats = ref<StatsMap>({})
const glyphCounts = ref<Record<string, number>>({ ps2: 0, wii: 0, psp: 0 })
const buildPaths = ref<Record<string, string>>({})
const loading = ref(true)

async function reload() {
  loading.value = true
  projectRoot.value = await window.api.projectRoot()
  stats.value = await window.api.translationStats()
  buildPaths.value = await window.api.buildOutputPaths()
  for (const p of ['ps2', 'wii', 'psp']) {
    try {
      const g: GlyphInfo[] = await window.api.glyphsList(p)
      glyphCounts.value[p] = g.length
    } catch { glyphCounts.value[p] = 0 }
  }
  loading.value = false
}
onMounted(reload)

const totalHashes = computed(() => {
  let n = 0
  for (const k in stats.value) n += stats.value[k]?.total ?? 0
  return n
})
const totalTranslated = computed(() => {
  let n = 0
  for (const k in stats.value) n += stats.value[k]?.translated ?? 0
  return n
})

function shortLabel(file: string) {
  if (file === 'translate_shared.txt') return 'SHARED'
  if (file === 'translate_ps2_only.txt') return 'PS2'
  if (file === 'translate_wii_only.txt') return 'WII'
  if (file === 'translate_psp_only.txt') return 'PSP'
  return file
}

function openOutput(p: string) {
  if (p) window.api.buildShowInFolder(p)
}
</script>

<template>
<div class="page-shell settings-shell">
  <div class="page-header">
    <h2>{{ t('settings.title') }}</h2>
    <p class="page-sub">{{ t('settings.sub') }}</p>
  </div>

  <div class="settings-scroll">
    <section class="card">
      <h3>{{ t('settings.cardPaths') }}</h3>
      <div class="kv-row">
        <div class="k">{{ t('settings.kProjectRoot') }}</div>
        <div class="v mono">{{ projectRoot || '…' }}</div>
      </div>
      <div class="kv-row">
        <div class="k">DolphinTool</div>
        <div class="v mono">E:\Games\Dolphin\DolphinTool.exe</div>
      </div>
      <div class="kv-row">
        <div class="k">7-Zip</div>
        <div class="v mono">C:\Program Files\7-Zip\7z.exe</div>
      </div>
      <div class="kv-row">
        <div class="k">Python</div>
        <div class="v mono">{{ t('settings.kPython') }}</div>
      </div>
    </section>

    <section class="card">
      <h3>{{ t('settings.cardFiles') }}</h3>
      <div v-if="loading" class="empty">{{ t('settings.loading') }}</div>
      <table v-else class="stats-table">
        <thead>
          <tr>
            <th>{{ t('settings.thFile') }}</th>
            <th class="num">{{ t('settings.thTotal') }}</th>
            <th class="num">{{ t('settings.thTranslated') }}</th>
            <th class="num">%</th>
            <th>{{ t('settings.thProgress') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, name) in stats" :key="name">
            <td>
              <span class="file-tag" :class="'tag-' + shortLabel(name).toLowerCase()">
                {{ shortLabel(name) }}
              </span>
              <span class="mono dim">{{ name }}</span>
            </td>
            <td class="num">{{ (s?.total ?? 0).toLocaleString() }}</td>
            <td class="num">{{ (s?.translated ?? 0).toLocaleString() }}</td>
            <td class="num">{{ s?.percent ?? 0 }}</td>
            <td>
              <div class="progress">
                <div class="progress-fill" :style="{ width: (s?.percent ?? 0) + '%' }"></div>
              </div>
            </td>
          </tr>
          <tr class="total-row">
            <td><b>{{ t('settings.totalRow') }}</b></td>
            <td class="num"><b>{{ totalHashes.toLocaleString() }}</b></td>
            <td class="num"><b>{{ totalTranslated.toLocaleString() }}</b></td>
            <td class="num">
              <b>{{ totalHashes ? Math.round(1000 * totalTranslated / totalHashes) / 10 : 0 }}</b>
            </td>
            <td>
              <div class="progress">
                <div class="progress-fill"
                     :style="{ width: (totalHashes ? 100 * totalTranslated / totalHashes : 0) + '%' }">
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card">
      <h3>{{ t('settings.cardGlyphs') }}</h3>
      <div class="glyph-grid">
        <div v-for="p in (['ps2','wii','psp'] as const)" :key="p" class="glyph-tile">
          <div class="glyph-platform">{{ p.toUpperCase() }}</div>
          <div class="glyph-count">{{ glyphCounts[p] }}</div>
          <div class="glyph-label">{{ t('settings.glyphPng') }}</div>
        </div>
      </div>
    </section>

    <section class="card">
      <h3>{{ t('settings.cardOutputs') }}</h3>
      <div class="kv-row" v-for="p in (['ps2','wii','psp'] as const)" :key="p">
        <div class="k">{{ p.toUpperCase() }}</div>
        <div class="v mono path-row">
          <span class="path">{{ buildPaths[p] || '…' }}</span>
          <button class="btn btn-small" @click="openOutput(buildPaths[p])">
            {{ t('settings.openBtn') }}
          </button>
        </div>
      </div>
    </section>
  </div>
</div>
</template>

<style scoped>
.page-shell {
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
  background: #000;
}

.page-header { padding: 24px 32px 8px; border-bottom: 1px solid var(--line-soft); }
.page-header h2 {
  margin: 0 0 6px; font-size: 14px; letter-spacing: 4px;
  color: var(--ice-bright); font-weight: 700;
}
.page-sub { margin: 0; font-size: 12px; color: var(--silver); line-height: 1.6; }

.settings-scroll {
  overflow-y: auto;
  padding: 18px 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card {
  background: linear-gradient(180deg, var(--bg-2) 0%, var(--bg-1) 100%);
  border: 1px solid var(--line);
  padding: 16px 20px;
}
.card h3 {
  margin: 0 0 12px;
  font-size: 11px;
  letter-spacing: 3px;
  color: var(--ice);
  font-weight: 700;
  font-family: var(--mono);
}

.kv-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  padding: 5px 0;
  align-items: center;
  font-size: 12px;
}
.k { color: var(--silver); letter-spacing: 0.5px; }
.v { color: var(--pale); }
.mono { font-family: var(--mono); font-size: 11px; }
.dim { color: var(--muted); margin-left: 8px; }

.path-row {
  display: flex; align-items: center; gap: 10px;
}
.path-row .path {
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--ice);
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.stats-table th {
  text-align: left;
  font-size: 10px;
  letter-spacing: 1.5px;
  color: var(--silver);
  border-bottom: 1px solid var(--line);
  padding: 6px 8px;
  font-weight: 500;
}
.stats-table th.num { text-align: right; }
.stats-table td {
  padding: 8px 8px;
  border-bottom: 1px solid var(--line-soft);
  color: var(--pale);
}
.stats-table td.num { text-align: right; font-family: var(--mono); }
.stats-table tr.total-row td {
  border-bottom: none;
  padding-top: 12px;
  color: var(--ice-bright);
}

.file-tag {
  display: inline-block;
  padding: 1px 7px;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 1px;
  background: var(--bg-3);
  color: var(--ice-bright);
  border: 1px solid var(--line);
  margin-right: 8px;
}
.file-tag.tag-ps2  { color: #b8d4ee; border-color: #2c5878; }
.file-tag.tag-wii  { color: #b8eed4; border-color: #2c7858; }
.file-tag.tag-psp  { color: #eed4b8; border-color: #785828; }
.file-tag.tag-shared { color: #d4b8ee; border-color: #58287c; }

.progress {
  width: 140px;
  height: 8px;
  background: var(--bg-3);
  border: 1px solid var(--line);
  position: relative;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ice) 0%, var(--ice-bright) 100%);
  box-shadow: 0 0 8px rgba(120, 200, 255, 0.5);
}

.glyph-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.glyph-tile {
  background: var(--bg-3);
  border: 1px solid var(--line);
  padding: 14px;
  text-align: center;
}
.glyph-platform {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--silver);
}
.glyph-count {
  font-size: 32px;
  font-weight: 800;
  color: var(--ice-bright);
  text-shadow: 0 0 10px rgba(120, 200, 255, 0.3);
  margin: 6px 0 2px;
  letter-spacing: 2px;
  font-family: var(--display);
}
.glyph-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: var(--muted);
}

.empty { color: var(--muted); padding: 14px 0; }

.btn-small { padding: 4px 10px; font-size: 11px; }
</style>
