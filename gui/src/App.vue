<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import StringsView from './components/StringsView.vue'
import AboutView from './components/AboutView.vue'
import SearchView from './components/SearchView.vue'
import ExportView from './components/ExportView.vue'
import ImportView from './components/ImportView.vue'
import SettingsView from './components/SettingsView.vue'
import NewProjectModal from './components/NewProjectModal.vue'
import { t, localeRef, setLocale, initLocale, type Locale } from './i18n'

const langModel = computed<Locale>({
  get: () => localeRef.value,
  set: (v) => setLocale(v),
})

type Platform = 'ps2' | 'psp' | 'wii'
type Nav = 'texts' | 'search' | 'export' | 'import' | 'settings' | 'about'

const platform = ref<Platform>('ps2')
const nav = ref<Nav>('texts')

const totalRows = ref(0)
const translatedRows = ref(0)
const dirty = ref(false)

const showModal = ref(false)
const projects = ref<any[]>([])

async function loadConfig() {
  const c = await window.api.configRead()
  projects.value = c.projects ?? []
  if (!projects.value.length) {
    showModal.value = true
  } else {
    const last = projects.value[projects.value.length - 1]
    if (last?.platform) platform.value = last.platform
  }
}

onMounted(async () => {
  await initLocale()
  await loadConfig()
})

async function onProjectAdded(_p: any) {
  showModal.value = false
  await loadConfig()
}

const platformItems: { id: Platform; logo: string }[] = [
  { id: 'ps2', logo: 'PS2' },
  { id: 'psp', logo: 'PSP' },
  { id: 'wii', logo: 'Wii' },
]

const navItems = computed<{ id: Nav; label: string }[]>(() => [
  { id: 'texts',    label: t('nav.texts') },
  { id: 'search',   label: t('nav.search') },
  { id: 'export',   label: t('nav.export') },
  { id: 'import',   label: t('nav.import') },
  { id: 'settings', label: t('nav.settings') },
  { id: 'about',    label: t('nav.about') },
])

const percentTranslated = computed(() =>
  totalRows.value ? Math.round(1000 * translatedRows.value / totalRows.value) / 10 : 0
)

</script>

<template>
  <div class="vhs-overlay">
    <div class="vhs-scanlines"></div>
    <div class="vhs-noise"></div>
  </div>

  <header class="titlebar">
    <span class="icon">SM</span>
    <span class="title-text">{{ t('app.title') }}<span class="dash">–</span>{{ t('app.subtitle') }}</span>
    <span class="titlebar-spacer"></span>
    <div class="lang-switch">
      <span class="lang-label">{{ t('app.languageLabel') }}:</span>
      <select v-model="langModel">
        <option value="uk">UK</option>
        <option value="en">EN</option>
      </select>
    </div>
  </header>

  <div class="main-split">
    <aside class="sidebar">
      <div class="sidebar-section">{{ t('sidebar.pickPlatform') }}</div>
      <div class="platform-cards">
        <div v-for="p in platformItems" :key="p.id"
             class="platform-card"
             :class="{ active: platform === p.id }"
             @click="platform = p.id">
          <div class="logo" :class="p.id">{{ p.logo }}</div>
          <div class="name">{{ t('platform.' + p.id) }}</div>
        </div>
      </div>

      <div class="sidebar-section">{{ t('sidebar.nav') }}</div>
      <div class="nav-items">
        <button v-for="n in navItems" :key="n.id"
                class="nav-item"
                :class="{ active: nav === n.id }"
                @click="nav = n.id">
          {{ n.label }}
        </button>
      </div>

      <div class="sidebar-footer">{{ t('app.version') }}</div>
    </aside>

    <main class="main-pane">
      <StringsView
        v-if="nav === 'texts'"
        :platform="platform"
        @stats="(tot, tr) => { totalRows = tot; translatedRows = tr }"
        @dirty="(d) => dirty = d"
      />
      <SearchView   v-else-if="nav === 'search'" />
      <ExportView   v-else-if="nav === 'export'" :platform="platform" />
      <ImportView   v-else-if="nav === 'import'" />
      <SettingsView v-else-if="nav === 'settings'" />
      <AboutView    v-else-if="nav === 'about'" />
    </main>
  </div>

  <footer class="status-bar">
    <span>{{ t('status.rows') }} <b style="color: var(--pale);">{{ totalRows.toLocaleString() }}</b></span>
    <span>{{ t('status.translated') }} <b style="color: var(--pale);">{{ translatedRows.toLocaleString() }}</b>
      <span style="color: var(--muted);">({{ percentTranslated }}%)</span>
    </span>
    <span class="right">
      <span class="saved" :class="{ dirty }">
        <span class="dot"></span>
        {{ dirty ? t('status.dirty') : t('status.saved') }}
      </span>
    </span>
  </footer>

  <NewProjectModal v-if="showModal" @done="onProjectAdded" @cancel="showModal = false" />
</template>
