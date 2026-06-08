// Bridge to Electron preload (window.api).

export interface BlockStats { total: number; translated: number; percent: number }
export type StatsMap = Record<string, BlockStats | null>

export interface FileInfo { name: string; path: string; exists: boolean; size: number }

export interface ProjectEntry {
  id: string
  platform: 'ps2' | 'wii' | 'psp'
  isoPath: string
  referencePath?: string
  createdAt: string
  extractedAt?: string
  displayName: string
}

export interface HashMeta {
  status?: 'approved' | 'in_progress' | 'needs_review' | 'blocked'
  context?: string
  category?: string
  notes?: string
  developerNote?: string
  tags?: string[]
  maxLength?: number
  lastModified?: string
}

export interface GlyphInfo { name: string; path: string }

declare global {
  interface Window {
    api: {
      projectRoot(): Promise<string>
      defaultLocale(): Promise<string>
      originalsRead(platform: string): Promise<Record<string, string>>

      translationList(): Promise<FileInfo[]>
      translationRead(name: string): Promise<string>
      translationSave(name: string, content: string): Promise<{ ok: boolean; bytes: number }>
      translationStats(): Promise<StatsMap>

      buildStart(platform: string): Promise<{ id: string; pid: number }>
      buildOutputPaths(): Promise<Record<string, string>>
      buildShowInFolder(p: string): Promise<void>
      onBuildLine(cb: (p: { id: string; kind: 'out' | 'err'; line: string }) => void): void
      onBuildDone(cb: (p: { id: string; code: number }) => void): void

      metadataRead(): Promise<Record<string, HashMeta>>
      metadataSave(data: Record<string, HashMeta>): Promise<{ ok: boolean }>
      metadataPatch(hash: string, patch: Partial<HashMeta>): Promise<HashMeta>

      glyphsList(platform: string): Promise<GlyphInfo[]>
      glyphReadDataUrl(p: string): Promise<string | null>

      configRead(): Promise<{ projects: ProjectEntry[] }>
      configAddProject(p: Omit<ProjectEntry, 'id' | 'createdAt'>): Promise<ProjectEntry>
      configRemoveProject(id: string): Promise<void>
      configMarkExtracted(id: string): Promise<void>

      pickFile(opts: { title?: string; filters?: { name: string; extensions: string[] }[] }): Promise<string | null>

      extractRun(project: ProjectEntry): Promise<{ id: string; code: number }>
      onExtractLine(cb: (p: { id: string; kind: string; line?: string; code?: number }) => void): void
    }
  }
}

export {}
