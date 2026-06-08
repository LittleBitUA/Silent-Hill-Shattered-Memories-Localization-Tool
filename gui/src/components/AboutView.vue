<script setup lang="ts">
import logoUrl from '../assets/Logo.png'
import { t } from '../i18n'

const APP_VERSION = '0.1.0'
</script>

<template>
  <div class="about-pane">
    <div class="about-hero">
      <img :src="logoUrl" alt="Shattered Memories" />
      <div class="about-tag">{{ t('about.tag', { v: APP_VERSION }) }}</div>
    </div>

    <div class="about-grid">
      <section class="about-card">
        <h3>{{ t('about.aboutTitle') }}</h3>
        <p v-html="t('about.aboutP1')"></p>
        <p v-html="t('about.aboutP2')"></p>
      </section>

      <section class="about-card">
        <h3>{{ t('about.howTitle') }}</h3>
        <ol>
          <li v-html="t('about.howUnpack')"></li>
          <li v-html="t('about.howFont')"></li>
          <li v-html="t('about.howStrings')"></li>
          <li v-html="t('about.howBuild')"></li>
        </ol>
      </section>

      <section class="about-card">
        <h3>{{ t('about.stackTitle') }}</h3>
        <div class="tech-grid">
          <div class="tech">
            <div class="tech-name">Electron + Vite + Vue 3</div>
            <div class="tech-desc">{{ t('about.stack.gui') }}</div>
          </div>
          <div class="tech">
            <div class="tech-name">TypeScript</div>
            <div class="tech-desc">{{ t('about.stack.ts') }}</div>
          </div>
          <div class="tech">
            <div class="tech-name">Python 3</div>
            <div class="tech-desc">{{ t('about.stack.py') }}</div>
          </div>
          <div class="tech">
            <div class="tech-name">zopfli</div>
            <div class="tech-desc">{{ t('about.stack.zopfli') }}</div>
          </div>
          <div class="tech">
            <div class="tech-name">wit + DolphinTool</div>
            <div class="tech-desc">{{ t('about.stack.wii') }}</div>
          </div>
          <div class="tech">
            <div class="tech-name">pycdlib + 7-Zip</div>
            <div class="tech-desc">{{ t('about.stack.psp') }}</div>
          </div>
        </div>
      </section>

      <section class="about-card author-card">
        <h3>{{ t('about.authorTitle') }}</h3>
        <div class="author">
          <div class="author-name">Dmytro Bidlov</div>
          <div class="author-studio">{{ t('about.author.studio') }}</div>
          <div class="author-meta">
            <div>{{ t('about.author.meta1') }}</div>
            <div>{{ t('about.author.meta2') }}</div>
          </div>
        </div>
      </section>

      <section class="about-card">
        <h3>{{ t('about.licenseTitle') }}</h3>
        <p v-html="t('about.license.p1')"></p>
        <p class="muted small">{{ t('about.license.p2') }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.about-pane {
  height: 100%;
  overflow-y: auto;
  padding: 24px 40px 40px;
  background: #000;
}

.about-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0 28px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
}
.about-hero img {
  max-height: 200px;
  mix-blend-mode: screen;
  margin-bottom: 6px;
}
.about-tag {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 4px;
  color: var(--silver);
}

.about-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
}

.about-card {
  background: linear-gradient(180deg, rgba(12, 24, 34, 0.65) 0%, rgba(0,0,0,0.85) 100%);
  border: 1px solid var(--line);
  padding: 20px 22px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--pale);
}

.about-card h3 {
  font-size: 11px;
  letter-spacing: 3px;
  color: var(--ice);
  margin: 0 0 12px;
  font-weight: 700;
  font-family: var(--mono);
}

.about-card p { margin: 0 0 12px; color: var(--pale); }
.about-card p:last-child { margin-bottom: 0; }
.about-card p.muted { color: var(--muted); font-size: 12px; }
.about-card p.small { font-size: 12px; }

.about-card code {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ice-bright);
  background: var(--bg-2);
  padding: 1px 6px;
  border: 1px solid var(--line);
}

.about-card a {
  color: var(--ice-bright);
  text-decoration: none;
  border-bottom: 1px solid var(--line-strong);
}
.about-card a:hover { color: var(--pale); border-bottom-color: var(--ice); }

.about-card ol {
  margin: 0;
  padding-left: 22px;
}
.about-card ol li { margin-bottom: 10px; }
.about-card ol li:last-child { margin-bottom: 0; }

.tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.tech {
  background: var(--bg-2);
  border: 1px solid var(--line);
  padding: 10px 14px;
}
.tech-name {
  font-family: var(--display);
  font-size: 13px;
  color: var(--ice-bright);
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}
.tech-desc {
  font-size: 11px;
  color: var(--silver);
}

.author-card {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, rgba(20, 50, 80, 0.4) 0%, rgba(0,0,0,0.85) 100%);
  border-color: var(--line-strong);
}
.author {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.author-name {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--ice-bright);
  text-shadow: 0 0 14px rgba(120, 200, 255, 0.3);
}
.author-studio {
  font-family: var(--mono);
  font-size: 13px;
  color: var(--ice);
  letter-spacing: 2px;
  margin-bottom: 8px;
}
.author-meta {
  font-size: 13px;
  color: var(--silver);
  line-height: 1.7;
}
</style>
