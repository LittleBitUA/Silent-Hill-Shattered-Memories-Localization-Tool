"""
Build SH:SM Wii UA RVZ.

Pipeline:
  1. Pack TEXT_TRANSLATION/translate_shared.txt + translate_wii_only.txt
     -> translate_sys/ui_wii.bin
  2. Patch Wii Font_EUR with Cyrillic + UA glyphs (if not already cached
     in UA_wii/_build/Font_EUR_wii_ua_raw.bin)
  3. In-place patch entries 408 / 1329 / 1330 in
     wii_extract/DATA/files/data.arc
  4. Use wit to build the modified extract directory back into a Wii ISO
  5. Use DolphinTool to convert ISO -> RVZ

Requirements (one-time install):
  * wit  (Wiimms ISO Tools 3.05a or newer)
  * DolphinTool.exe (ships with Dolphin emulator)
  * Python: pip install zopfli  (optional, falls back to zlib level 9)

Inputs:
  * wii_extract/  (output of `DolphinTool extract` on the source RVZ)
  * TEXT_TRANSLATION/translate_shared.txt + translate_wii_only.txt
  * UA/_build/Font_EUR_ua_raw.bin  (the PS2 patched font, donor of Cyrillic)
"""
import os, sys, subprocess, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tool'
UNPACKED = ROOT / 'unpacked'
WII_EXTRACT = ROOT / 'wii_extract'
UA_WII = ROOT / 'UA_wii'
BUILD = UA_WII / '_build'
BUILD.mkdir(parents=True, exist_ok=True)

WIT = pathlib.Path(r'C:\Users\bidlov\bin\wit\wit-v3.05a-r8638-cygwin64\bin\wit.exe')
DOLPHIN = pathlib.Path(r'E:\Games\Dolphin\DolphinTool.exe')

ISO_OUT = UA_WII / 'Silent Hill - Shattered Memories (UA).iso'
RVZ_OUT = UA_WII / 'Silent Hill - Shattered Memories (UA).rvz'

TR_SYS = BUILD / 'translate_sys_wii.bin'
TR_UI  = BUILD / 'translate_ui_wii.bin'

# UA-specific Cyrillic letters that get substituted to Latin/Latin-1 glyphs
# that we've added to the Wii font (see wii_patch_maindol.py):
#   Ї -> Ï (U+00CF, added as Latin-I copy, user redraws dots)
#   ї -> ï (U+00EF, restored from orig USA Wii font)
WII_EXTRA_SUBST = 'Ї=Ï,ї=ï'

# Custom glyph PNGs (user-edited overrides). Anything in unpacked/glyphs_wii/
# matching a known codepoint gets injected after the base font patch.
PNG_GLYPH_MAP = {
    'ye_upper.png':          0x0404,   # Є  (user-rotated from Cyrillic Э)
    'ye_lower.png':          0x0454,   # є  (user-rotated from э)
    'i_diaeresis_upper.png': 0x00CF,   # Ï  (user-drawn dots on Latin I)
    'gh_upper.png':          0x0490,   # Ґ  (user-drawn hook on Г)
    'gh_lower.png':          0x0491,   # ґ  (user-drawn hook on г)
}

def run(cmd, label, env=None):
    print(f'\n>>> {label}')
    print(f'    {" ".join(map(str, cmd))}')
    r = subprocess.run(cmd, check=False, env=env)
    if r.returncode != 0:
        sys.exit(f'!!! {label} failed (exit {r.returncode})')

def main():
    if not WIT.exists():
        sys.exit(f'missing wit: {WIT}')
    if not DOLPHIN.exists():
        sys.exit(f'missing DolphinTool: {DOLPHIN}')
    if not (WII_EXTRACT / 'DATA' / 'files' / 'data.arc').exists():
        sys.exit(f'missing extracted Wii disc at {WII_EXTRACT}. '
                 f'Run: DolphinTool extract -i <source.rvz> -o {WII_EXTRACT}')
    if not (ROOT / 'TEXT_TRANSLATION' / 'translate_shared.txt').exists():
        sys.exit(f'missing TEXT_TRANSLATION/translate_shared.txt — '
                 f'run tool/build_shared_translation.py first')

    # 1. Patch main.dol with our Wii UA font (Metallist base + UA donor swaps
    #    + Ï ï Ґ ґ extensions). This is THE font the Wii engine reads.
    run([sys.executable, str(TOOL/'wii_patch_maindol.py')], 'patch Wii main.dol font')

    # 2. Pack strings (sys & ui identical) with Wii-specific Cyrillic
    #    substitutions on top of the global CYR2LAT_SUBST.
    # Inject any user-edited PNG overrides from unpacked/glyphs_wii/
    glyph_dir = UNPACKED / 'glyphs_wii'
    if glyph_dir.exists():
        for png_name, cp in PNG_GLYPH_MAP.items():
            png_path = glyph_dir / png_name
            if png_path.exists():
                run([sys.executable, str(TOOL/'wii_kfont_png_edit.py'),
                     'inject', hex(cp), '--in', str(png_path)],
                    f'inject U+{cp:04X} from {png_name}')

    env = os.environ.copy()
    env['SH_EXTRA_SUBST'] = WII_EXTRA_SUBST
    run([sys.executable, str(TOOL/'pack_platform_strings.py'),
         'wii', str(TR_SYS)],
        'pack Wii strings from TEXT_TRANSLATION/ (shared + wii_only)', env=env)
    shutil.copyfile(TR_SYS, TR_UI)
    print(f'    duplicated -> {TR_UI.name}')

    # 3. Patch data.arc in-place (replaces only translate_sys/ui entries —
    #    Font_EUR inside data.arc is left untouched since the engine uses
    #    the main.dol-embedded font instead).
    run([sys.executable, str(TOOL/'wii_arc_patch.py')], 'patch Wii data.arc')

    # 4. wit COPY extract/ -> ISO
    if ISO_OUT.exists():
        ISO_OUT.unlink()
    run([str(WIT), 'COPY', str(WII_EXTRACT), '--DEST', str(ISO_OUT), '--iso'],
        'wit COPY -> ISO')

    # 5. DolphinTool convert ISO -> RVZ (zstd-19 for best compression)
    if RVZ_OUT.exists():
        RVZ_OUT.unlink()
    run([str(DOLPHIN), 'convert',
         '-i', str(ISO_OUT), '-o', str(RVZ_OUT),
         '-f', 'rvz', '-c', 'zstd', '-l', '5', '-b', '131072'],
        'DolphinTool ISO -> RVZ (zstd-5)')

    # ISO is huge, optionally delete after RVZ ready
    iso_sz = ISO_OUT.stat().st_size if ISO_OUT.exists() else 0
    rvz_sz = RVZ_OUT.stat().st_size if RVZ_OUT.exists() else 0
    print(f'\nISO: {iso_sz/1e9:.2f} GB')
    print(f'RVZ: {rvz_sz/1e9:.2f} GB')
    print(f'\nDone. Load {RVZ_OUT.name} in Dolphin.')

if __name__ == '__main__':
    main()
