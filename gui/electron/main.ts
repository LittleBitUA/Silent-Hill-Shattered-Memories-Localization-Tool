import { app, BrowserWindow, ipcMain, shell, dialog } from 'electron'
import path from 'node:path'
import fs from 'node:fs'
import zlib from 'node:zlib'
import { spawn } from 'node:child_process'

process.env.APP_ROOT = path.join(__dirname, '..')

export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL
  ? path.join(process.env.APP_ROOT, 'public')
  : RENDERER_DIST

// The user's project root is the parent of gui/
const PROJECT_ROOT = path.resolve(process.env.APP_ROOT, '..')
const TEXT_TR = path.join(PROJECT_ROOT, 'TEXT_TRANSLATION')
const TOOL = path.join(PROJECT_ROOT, 'tool')

let win: BrowserWindow | null

function createWindow() {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 720,
    backgroundColor: '#0a1620',
    title: 'SHATTERED MEMORIES — UA TOOLKIT',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  win.webContents.on('did-finish-load', () => {
    win?.webContents.send('main-process-message', new Date().toLocaleString())
  })

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    win.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
    win = null
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.whenReady().then(createWindow)

// ---- IPC -----------------------------------------------------------------

ipcMain.handle('app:project-root', async () => PROJECT_ROOT)

ipcMain.handle('i18n:default-locale', async () => app.getLocale() || 'en')

// ---- Originals reader (English source strings from packed binaries) ----

interface OriginalSource {
  // path to a .arc file + entry index inside that archive
  arcPath?: string
  arcIndex?: number
  // OR: path to an already-decompressed string-table .bin
  rawPath?: string
}

const ORIGINAL_SOURCES: Record<string, OriginalSource> = {
  ps2_sys: { rawPath: path.join(PROJECT_ROOT, 'unpacked', 'data', '1315_2c238264.bin') },
  ps2_ui:  { rawPath: path.join(PROJECT_ROOT, 'unpacked', 'data', '1316_2c238276.bin') },
  wii:     { arcPath: path.join(PROJECT_ROOT, 'wii_extract', 'DATA', 'files', 'data.arc'),
             arcIndex: 1329 },
  psp:     { arcPath: path.join(PROJECT_ROOT, 'psp_orig_extract', 'PSP_GAME', 'USRDIR', 'DATA.ARC'),
             arcIndex: 1316 },
}

function readArcEntry(arcPath: string, idx: number): Buffer {
  const fd = fs.openSync(arcPath, 'r')
  try {
    const hdr = Buffer.alloc(16)
    fs.readSync(fd, hdr, 0, 16, 16 + idx * 16)
    const off = hdr.readUInt32LE(4)
    const csz = hdr.readUInt32LE(8)
    const blob = Buffer.alloc(csz)
    fs.readSync(fd, blob, 0, csz, off)
    if (blob.length >= 2 && blob[0] === 0x78 &&
        (blob[1] === 0x9c || blob[1] === 0xda || blob[1] === 0x01 || blob[1] === 0x5e)) {
      return zlib.inflateSync(blob)
    }
    return blob
  } finally {
    fs.closeSync(fd)
  }
}

function decodeString(blob: Buffer, pos: number): string {
  const out: string[] = []
  while (pos < blob.length - 1) {
    const u = blob[pos] | (blob[pos + 1] << 8)
    pos += 2
    if (u === 0) break
    if (u === 1) {
      const n = blob[pos] | (blob[pos + 1] << 8); pos += 2
      out.push(`<c=${n}>`)
    } else if (u === 2) { out.push('<p>') }
    else if (u === 3) {
      const n = blob[pos] | (blob[pos + 1] << 8); pos += 2
      out.push(`<b=${n}>`)
    } else if (u === 4) {
      const n = blob[pos] | (blob[pos + 1] << 8); pos += 2
      out.push(`<w=${n}>`)
    } else if (u === 0x0A) { out.push('\\n') }
    else if (u === 0x09) { out.push('\\t') }
    else if (u === 0x0D) { out.push('\\r') }
    else { out.push(String.fromCharCode(u)) }
  }
  return out.join('')
}

function parseStringsBlob(blob: Buffer): Record<string, string> {
  if (blob.length < 8) return {}
  const cnt = blob.readUInt32LE(4)
  const base = 8 + cnt * 8
  const out: Record<string, string> = {}
  for (let i = 0; i < cnt; i++) {
    const h = blob.readUInt32LE(8 + i * 8)
    const off = blob.readUInt32LE(8 + i * 8 + 4)
    out[h.toString(16).padStart(8, '0')] = decodeString(blob, base + off * 2)
  }
  return out
}

ipcMain.handle('originals:read', async (_e, platform: string): Promise<Record<string, string>> => {
  const src = ORIGINAL_SOURCES[platform]
  if (!src) return {}
  try {
    let blob: Buffer
    if (src.rawPath) {
      if (!fs.existsSync(src.rawPath)) return {}
      blob = fs.readFileSync(src.rawPath)
    } else {
      if (!fs.existsSync(src.arcPath!)) return {}
      blob = readArcEntry(src.arcPath!, src.arcIndex!)
    }
    return parseStringsBlob(blob)
  } catch (e) {
    return {}
  }
})

ipcMain.handle('translation:list', async () => {
  const files = ['translate_shared.txt', 'translate_ps2_only.txt',
                 'translate_wii_only.txt', 'translate_psp_only.txt']
  return files.map(name => {
    const p = path.join(TEXT_TR, name)
    return {
      name, path: p,
      exists: fs.existsSync(p),
      size: fs.existsSync(p) ? fs.statSync(p).size : 0,
    }
  })
})

ipcMain.handle('translation:read', async (_e, fileName: string) => {
  return fs.readFileSync(path.join(TEXT_TR, fileName), 'utf-8')
})

ipcMain.handle('translation:save', async (_e, fileName: string, content: string) => {
  const p = path.join(TEXT_TR, fileName)
  fs.writeFileSync(p, content, 'utf-8')
  return { ok: true, bytes: Buffer.byteLength(content, 'utf-8') }
})

function countBlocks(text: string) {
  let total = 0, translated = 0
  let inBlock = false, body = ''
  const flush = () => {
    if (inBlock) {
      total++
      if (/[Ѐ-ӿ]/.test(body)) translated++
    }
  }
  for (const line of text.split('\n')) {
    if (line.startsWith('# - ')) {
      flush(); inBlock = true; body = ''
    } else if (line.startsWith('#')) {
      continue
    } else if (line.trim() === '') {
      flush(); inBlock = false; body = ''
    } else if (inBlock) {
      body += line + '\n'
    }
  }
  flush()
  return {
    total, translated,
    percent: total ? Math.round(1000 * translated / total) / 10 : 0,
  }
}

ipcMain.handle('translation:stats', async () => {
  const out: Record<string, any> = {}
  for (const name of ['translate_shared.txt', 'translate_ps2_only.txt',
                      'translate_wii_only.txt', 'translate_psp_only.txt']) {
    const p = path.join(TEXT_TR, name)
    out[name] = fs.existsSync(p) ? countBlocks(fs.readFileSync(p, 'utf-8')) : null
  }
  return out
})

const PLATFORM_SCRIPT: Record<string, string> = {
  ps2: 'build_ua_ntsc.py',
  wii: 'build_ua_wii.py',
  psp: 'build_ua_psp.py',
}

ipcMain.handle('build:start', async (event, platform: string) => {
  const script = PLATFORM_SCRIPT[platform]
  if (!script) throw new Error(`unknown platform ${platform}`)
  const py = spawn('python', [path.join(TOOL, script)], {
    cwd: PROJECT_ROOT,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  })
  const id = Date.now().toString(36)
  py.stdout.on('data', (b: Buffer) =>
    event.sender.send('build:line', { id, kind: 'out', line: b.toString() }))
  py.stderr.on('data', (b: Buffer) =>
    event.sender.send('build:line', { id, kind: 'err', line: b.toString() }))
  py.on('close', (code) => event.sender.send('build:done', { id, code }))
  return { id, pid: py.pid }
})

ipcMain.handle('build:output-paths', async () => ({
  ps2: path.join(PROJECT_ROOT, 'UA', 'Silent Hill - Shattered Memories (UA).iso'),
  wii: path.join(PROJECT_ROOT, 'UA_wii', 'Silent Hill - Shattered Memories (UA).rvz'),
  psp: path.join(PROJECT_ROOT, 'UA_psp', 'Silent Hill - Shattered Memories (UA).iso'),
}))

ipcMain.handle('build:show-in-folder', async (_e, p: string) => {
  if (fs.existsSync(p)) shell.showItemInFolder(p)
})

// ---- Metadata sidecar (TEXT_TRANSLATION/metadata.json) -----------------

const METADATA_PATH = path.join(TEXT_TR, 'metadata.json')

interface HashMeta {
  status?: 'approved' | 'in_progress' | 'needs_review' | 'blocked'
  context?: string
  category?: string
  notes?: string
  developerNote?: string
  tags?: string[]
  maxLength?: number
  lastModified?: string
}

ipcMain.handle('metadata:read', async (): Promise<Record<string, HashMeta>> => {
  if (!fs.existsSync(METADATA_PATH)) return {}
  try { return JSON.parse(fs.readFileSync(METADATA_PATH, 'utf-8')) }
  catch { return {} }
})

ipcMain.handle('metadata:save', async (_e, data: Record<string, HashMeta>) => {
  fs.writeFileSync(METADATA_PATH, JSON.stringify(data, null, 2), 'utf-8')
  return { ok: true }
})

ipcMain.handle('metadata:patch', async (_e, hash: string, patch: Partial<HashMeta>) => {
  let data: Record<string, HashMeta> = {}
  if (fs.existsSync(METADATA_PATH)) {
    try { data = JSON.parse(fs.readFileSync(METADATA_PATH, 'utf-8')) } catch {}
  }
  data[hash] = { ...(data[hash] ?? {}), ...patch, lastModified: new Date().toISOString() }
  fs.writeFileSync(METADATA_PATH, JSON.stringify(data, null, 2), 'utf-8')
  return data[hash]
})

// ---- Glyph PNG previews ------------------------------------------------

ipcMain.handle('glyphs:list', async (_e, platform: string) => {
  const dir = path.join(PROJECT_ROOT, 'unpacked',
                        platform === 'ps2' ? 'glyphs' : `glyphs_${platform}`)
  if (!fs.existsSync(dir)) return []
  return fs.readdirSync(dir)
    .filter(n => n.endsWith('.png'))
    .map(n => ({ name: n, path: path.join(dir, n) }))
})

ipcMain.handle('glyphs:read-data-url', async (_e, fullPath: string) => {
  if (!fs.existsSync(fullPath)) return null
  const buf = fs.readFileSync(fullPath)
  return `data:image/png;base64,${buf.toString('base64')}`
})

// ---- Project config (per-platform setup state) -------------------------

const CONFIG_PATH = path.join(app.getPath('userData'), 'projects.json')

interface ProjectEntry {
  id: string
  platform: 'ps2' | 'wii' | 'psp'
  isoPath: string
  referencePath?: string      // optional secondary disc image (font donor)
  createdAt: string
  extractedAt?: string
  displayName: string
}

interface Config { projects: ProjectEntry[] }

function readConfig(): Config {
  if (!fs.existsSync(CONFIG_PATH)) return { projects: [] }
  try {
    const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8')) as Config
    let migrated = false
    for (const p of cfg.projects ?? []) {
      const legacy = (p as any).metallistPath
      if (legacy && !p.referencePath) {
        p.referencePath = legacy
        delete (p as any).metallistPath
        migrated = true
      }
    }
    if (migrated) writeConfig(cfg)
    return cfg
  }
  catch { return { projects: [] } }
}
function writeConfig(c: Config) {
  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true })
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(c, null, 2), 'utf-8')
}

ipcMain.handle('config:read', async () => readConfig())

ipcMain.handle('config:add-project', async (_e, p: Omit<ProjectEntry, 'id' | 'createdAt'>) => {
  const c = readConfig()
  const entry: ProjectEntry = {
    ...p,
    id: `${p.platform}-${Date.now().toString(36)}`,
    createdAt: new Date().toISOString(),
  }
  c.projects.push(entry)
  writeConfig(c)
  return entry
})

ipcMain.handle('config:remove-project', async (_e, id: string) => {
  const c = readConfig()
  c.projects = c.projects.filter(p => p.id !== id)
  writeConfig(c)
})

ipcMain.handle('config:mark-extracted', async (_e, id: string) => {
  const c = readConfig()
  const p = c.projects.find(p => p.id === id)
  if (p) {
    p.extractedAt = new Date().toISOString()
    writeConfig(c)
  }
})

// ---- File dialog --------------------------------------------------------

ipcMain.handle('dialog:open-file', async (_e, opts: any) => {
  const r = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: opts?.filters ?? [{ name: 'Disc images', extensions: ['iso', 'rvz', 'wbfs'] }],
    title: opts?.title ?? 'Pick a file',
  })
  return r.canceled ? null : r.filePaths[0]
})

// ---- Extraction --------------------------------------------------------

const DOLPHIN_TOOL = 'E:\\Games\\Dolphin\\DolphinTool.exe'
const SEVEN_ZIP    = 'C:\\Program Files\\7-Zip\\7z.exe'

function streamProc(
  event: Electron.IpcMainInvokeEvent,
  channel: string,
  jobId: string,
  cmd: string,
  args: string[],
  cwd?: string,
) {
  return new Promise<number>((resolve) => {
    const p = spawn(cmd, args, { cwd, shell: false,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' } })
    p.stdout.on('data', (b) => event.sender.send(channel, { id: jobId, kind: 'out', line: b.toString() }))
    p.stderr.on('data', (b) => event.sender.send(channel, { id: jobId, kind: 'err', line: b.toString() }))
    p.on('close', (code) => { event.sender.send(channel, { id: jobId, kind: 'done', code }); resolve(code ?? -1) })
    p.on('error', (err) => {
      event.sender.send(channel, { id: jobId, kind: 'err', line: `[spawn error] ${err.message}\n` })
      event.sender.send(channel, { id: jobId, kind: 'done', code: -1 })
      resolve(-1)
    })
  })
}

ipcMain.handle('extract:run', async (event, project: ProjectEntry) => {
  const id = Date.now().toString(36)
  const platform = project.platform

  if (platform === 'wii') {
    const out = path.join(PROJECT_ROOT, 'wii_extract')
    fs.mkdirSync(out, { recursive: true })
    event.sender.send('extract:line', { id, kind: 'info', line: `[wii] DolphinTool extract -> ${out}\n` })
    const code = await streamProc(event, 'extract:line', id,
      DOLPHIN_TOOL, ['extract', '-i', project.isoPath, '-o', out, '-q'])
    return { id, code }
  }

  if (platform === 'psp') {
    const out = path.join(PROJECT_ROOT, 'psp_orig_extract')
    fs.mkdirSync(out, { recursive: true })
    event.sender.send('extract:line', { id, kind: 'info', line: `[psp] 7z extract -> ${out}\n` })
    const code = await streamProc(event, 'extract:line', id,
      SEVEN_ZIP, ['x', '-y', `-o${out}`, project.isoPath])
    if (code === 0 && project.referencePath) {
      const outR = path.join(PROJECT_ROOT, 'psp_ref_extract')
      fs.mkdirSync(outR, { recursive: true })
      event.sender.send('extract:line', { id, kind: 'info', line: `[psp] 7z extract reference -> ${outR}\n` })
      await streamProc(event, 'extract:line', id,
        SEVEN_ZIP, ['x', '-y', `-o${outR}`, project.referencePath])
    }
    return { id, code }
  }

  // PS2 — copy the user-picked ISO to the project root with the known name
  if (platform === 'ps2') {
    const dst = path.join(PROJECT_ROOT, 'Silent Hill - Shattered Memories (USA) (En,Fr,Es).iso')
    event.sender.send('extract:line', { id, kind: 'info', line: `[ps2] copy ISO -> ${dst}\n` })
    if (path.resolve(project.isoPath) !== path.resolve(dst)) {
      fs.copyFileSync(project.isoPath, dst)
    }
    event.sender.send('extract:line', { id, kind: 'done', code: 0 })
    return { id, code: 0 }
  }

  return { id, code: -1 }
})
