import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('api', {
  projectRoot: () => ipcRenderer.invoke('app:project-root'),
  defaultLocale: () => ipcRenderer.invoke('i18n:default-locale'),
  originalsRead: (platform: string) => ipcRenderer.invoke('originals:read', platform),

  translationList: () => ipcRenderer.invoke('translation:list'),
  translationRead: (name: string) => ipcRenderer.invoke('translation:read', name),
  translationSave: (name: string, content: string) =>
    ipcRenderer.invoke('translation:save', name, content),
  translationStats: () => ipcRenderer.invoke('translation:stats'),

  buildStart: (platform: string) => ipcRenderer.invoke('build:start', platform),
  buildOutputPaths: () => ipcRenderer.invoke('build:output-paths'),
  buildShowInFolder: (p: string) => ipcRenderer.invoke('build:show-in-folder', p),

  onBuildLine: (cb: (payload: any) => void) =>
    ipcRenderer.on('build:line', (_e, payload) => cb(payload)),
  onBuildDone: (cb: (payload: any) => void) =>
    ipcRenderer.on('build:done', (_e, payload) => cb(payload)),

  metadataRead: () => ipcRenderer.invoke('metadata:read'),
  metadataSave: (data: any) => ipcRenderer.invoke('metadata:save', data),
  metadataPatch: (hash: string, patch: any) =>
    ipcRenderer.invoke('metadata:patch', hash, patch),

  glyphsList: (platform: string) => ipcRenderer.invoke('glyphs:list', platform),
  glyphReadDataUrl: (p: string) => ipcRenderer.invoke('glyphs:read-data-url', p),

  configRead: () => ipcRenderer.invoke('config:read'),
  configAddProject: (p: any) => ipcRenderer.invoke('config:add-project', p),
  configRemoveProject: (id: string) => ipcRenderer.invoke('config:remove-project', id),
  configMarkExtracted: (id: string) => ipcRenderer.invoke('config:mark-extracted', id),

  pickFile: (opts: any) => ipcRenderer.invoke('dialog:open-file', opts),

  extractRun: (project: any) => ipcRenderer.invoke('extract:run', project),
  onExtractLine: (cb: (payload: any) => void) =>
    ipcRenderer.on('extract:line', (_e, payload) => cb(payload)),
})
