# Silent Hill: Shattered Memories — Localization Tool

A complete toolkit for Ukrainian localization of *Silent Hill: Shattered
Memories* on three platforms from a single shared translation source:

| Platform | Build script              | Output                |
| -------- | ------------------------- | --------------------- |
| **PS2**  | `tool/build_ua_ntsc.py`   | `UA/*.iso` (NTSC-U)   |
| **Wii**  | `tool/build_ua_wii.py`    | `UA_wii/*.rvz`        |
| **PSP**  | `tool/build_ua_psp.py`    | `UA_psp/*.iso`        |

Includes:

- ~28 Python build scripts (font, strings, KFONT codec, ARC archives,
  ISO9660 rebuild, PSP `;1` strip, RVZ via DolphinTool).
- An Electron + Vue 3 GUI (`gui/`) — strings editor, search, build runner,
  slot-fit analysis, project manager, UK/EN i18n.

**Author:** Dmytro Bidlov / «Little Bit»

## Translation source

The translation files (`TEXT_TRANSLATION/`) are **not bundled** with this
repo — you generate them once from your own legal disc dumps. After the
extracts described in *Build prerequisites* are in place, run:

```
python tool/init_translation_template.py
```

This produces:

```
TEXT_TRANSLATION/translate_shared.txt    # 4853 hashes, union of all platforms
TEXT_TRANSLATION/translate_ps2_only.txt  # PS2-exclusive overrides
TEXT_TRANSLATION/translate_wii_only.txt  # Wii-exclusive overrides
TEXT_TRANSLATION/translate_psp_only.txt  # PSP-exclusive overrides
```

Each block holds the English original from the source binaries:

```
# - 5585d13d
<c=1>Map

# - 31252997
<c=1>Voicemail
```

Replace the body lines with your target-language translation. Inline
tags (`<c=N>`, `<b=N>`, `<p>`, `<w=N>`) and escape sequences (`\n`,
`\t`, `\r`) must be preserved verbatim.

## Build prerequisites

You supply your own legal disc dumps:

| Platform | What you need                                                       |
| -------- | ------------------------------------------------------------------- |
| PS2      | `Silent Hill - Shattered Memories (USA) (En,Fr,Es).iso` (NTSC-U) at project root |
| Wii      | `wii_extract/` (output of `DolphinTool extract` on the source RVZ)  |
| PSP      | `psp_orig_extract/` (extracted USA PSN ISO) — plus an optional reference image for the font (see `tool/build_ua_psp.py`) |

External tools (one-time install):

- Python 3.10+ with `pip install zopfli pycdlib pillow`
- **PS2**: nothing extra (build does everything in Python)
- **Wii**: [wit (Wiimms ISO Tools)](https://wit.wiimm.de) + `DolphinTool.exe` (from Dolphin emulator)
- **PSP**: 7-Zip (for initial ISO extraction)

## How it works (high level)

Each platform has a font (Font_EUR, KFONT format) and a strings table.
We patch both.

**Font** — extended with the Ukrainian alphabet by donor-remapping unused
slots (Latin-1 supplement codepoints and extension records). Custom-drawn
glyphs (Є, є, Ї, ї, Ґ, ґ) live as PNGs in `unpacked/glyphs_<platform>/`
and are auto-injected by the build scripts. Edit them in any image
editor (keep dimensions; 0 = transparent, 255 = opaque) and re-run the
build.

| Letter | Approach across platforms                                       |
| ------ | --------------------------------------------------------------- |
| Є є    | Donor-remap of an unused Latin-1 slot, custom bitmap            |
| Ї ї    | PS2: donor bitmap; Wii / PSP: substituted to Ï / ï at pack time |
| І і    | Donor of Latin I / i (identical shape)                          |
| Ґ ґ    | Font extension record, copy of Г / г + user-drawn hook          |

**Strings** — Ukrainian text packed into UTF-16 with platform-specific
substitutions: shape-identical letters (А → A, В → B, etc.) share Latin
glyph slots; an extra substitution table on Wii / PSP routes Ї → Ï.

## GUI

```
cd gui
npm install
npm run dev      # launches Electron + Vite dev server
npm run build    # production build
```

Pages: **Strings** (inline editor), **Search** (cross-file global search),
**Export** (build + slot-analysis), **Import** (project manager + ISO
extraction wizard), **Settings** (paths / file stats / glyph counts),
**About**.

i18n: Ukrainian by default if Windows locale is `uk-*`, otherwise English;
override via dropdown in the titlebar. Choice persists across launches.

## Project structure

```
TEXT_TRANSLATION/                       # ← edit here. Single source of truth.
  translate_shared.txt                  # 4853 hashes, union of all platforms
  translate_ps2_only.txt                # PS2-exclusive hashes / overrides
  translate_wii_only.txt                # Wii-exclusive
  translate_psp_only.txt                # PSP-exclusive

unpacked/glyphs/                        # PS2 PNG glyph overrides
unpacked/glyphs_wii/                    # Wii PNG glyph overrides
unpacked/glyphs_psp/                    # PSP PNG glyph overrides

tool/                                   # all Python build scripts (~28 files)
  STATUS.md                             # detailed technical notes
  build_ua_ntsc.py                      # PS2 orchestrator
  build_ua_wii.py                       # Wii orchestrator
  build_ua_psp.py                       # PSP orchestrator
  pack_platform_strings.py              # merges shared + only at pack time
  arc_rebuild.py                        # in-place ARC patcher (PS2/Wii)
  psp_arc_patch.py / wii_arc_patch.py   # platform ARC patchers
  patch_font_ua.py / wii_patch_maindol.py / psp_patch_eboot.py
  kfont_real.py / kfont_writer.py       # KFONT codec
  ...

gui/                                    # Electron + Vite + Vue 3 GUI
  electron/                             # main process + preload
  src/                                  # Vue components, i18n, styles
  scripts/                              # dev runner
```

Local-only working directories (gitignored): `wii_extract/`,
`psp_*_extract/`, `psp_extract_work/`, `UA*/`, `unpacked/data/`,
`_wii_orig_probe/`, plus any `*.iso` / `*.rvz` files.

## Technical deep-dive

See [`tool/STATUS.md`](tool/STATUS.md) for the full per-platform layout,
font layouts, build-pipeline internals, and platform-specific quirks
(why Wii reads the font from `main.dol`, why PSP needs CFW, why the PSP
ISO needs `;N` version suffix stripped, atlas-balance behavior on PS2,
etc.).

## License

Open source. The translation text is a fan work; *Silent Hill: Shattered
Memories* belongs to Konami. This tool does not modify your original ROM
— it produces a separate patched copy. Users must supply their own legal
disc dumps.

© 2026 Dmytro Bidlov / «Little Bit». Built with ❤ for the Ukrainian
community.
