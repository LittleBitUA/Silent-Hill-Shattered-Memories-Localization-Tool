"""
NTSC-U variant of the UA build pipeline.

Uses iso_discover.py to find all offsets automatically, so this script
works on ANY SLUS-21899 dump (or any other region) without code changes.

Output:
    <project>/UA/Silent Hill - Shattered Memories (UA).iso

Inputs:
    NTSC_ISO  = ../Silent Hill - Shattered Memories (USA) (En,Fr,Es).iso
    RUS_FONT  = direct-copy from ../rus/SLUS_218.99 (Metallist's working Cyrillic font)
    UA_TEXT   = ../unpacked/translate_ui.tsv / translate_sys.tsv
"""
import sys, struct, zlib, mmap, shutil, subprocess, pathlib, time, os, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = pathlib.Path(__file__).resolve().parent
NTSC_ISO = ROOT / 'Silent Hill - Shattered Memories (USA) (En,Fr,Es).iso'
RUS_SLUS = ROOT / 'rus' / 'SLUS_218.99_rus'   # Metallist's patched SLUS (Cyrillic font)
OUT_ISO  = ROOT / 'UA' / 'Silent Hill - Shattered Memories (UA).iso'
WORK     = ROOT / 'UA' / '_build'

FONT_HASH = 0xf63bbff1

# Custom glyph PNGs (user-edited overrides). Anything dropped into
# unpacked/glyphs/ matching a known codepoint gets injected after the
# base font patch. File name -> codepoint mapping:
PNG_GLYPH_MAP = {
    'd_upper.png':   0x0414,   # Д  (user-redrawn, taller)
    'd_lower.png':   0x0434,   # д  (user-redrawn, taller)
    'yu_upper.png':  0x042E,   # Ю
    'yu_lower.png':  0x044E,   # ю  (user-redrawn, wider)
    'exclaim.png':   0x0021,   # !
    'gh_upper.png':  0x0490,   # Ґ  (donor remapped from Cyrillic Ё via add_gh_donors)
    'gh_lower.png':  0x0491,   # ґ  (donor remapped from Cyrillic ё)
}

def main():
    if not NTSC_ISO.exists(): sys.exit(f'missing {NTSC_ISO}')
    if not RUS_SLUS.exists(): sys.exit(f'missing {RUS_SLUS}')

    print('=== 1. Discover NTSC-U ISO layout ===')
    SECTOR = 0x800
    with open(NTSC_ISO, 'rb') as f:
        iso_mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        # ISO9660 PVD @ sector 16; root dir record at byte 156
        root_lba  = struct.unpack_from('<I', iso_mm, 16*SECTOR + 156 + 2)[0]
        root_size = struct.unpack_from('<I', iso_mm, 16*SECTOR + 156 + 10)[0]
        elf_off = data_arc_off = data_arc_size = elf_size = 0
        pos = 0
        root = iso_mm[root_lba*SECTOR : root_lba*SECTOR + root_size]
        while pos < root_size:
            rec_len = root[pos]
            if rec_len == 0:
                pos += SECTOR - (pos % SECTOR); continue
            lba  = struct.unpack_from('<I', root, pos+2)[0]
            size = struct.unpack_from('<I', root, pos+10)[0]
            name = bytes(root[pos+33 : pos+33 + root[pos+32]]).split(b';')[0].decode('ascii', errors='replace')
            if 'SLUS' in name:
                elf_off, elf_size = lba*SECTOR, size
            elif name == 'DATA.ARC':
                data_arc_off, data_arc_size = lba*SECTOR, size
            pos += rec_len
        # Find EMBEDED magic in the ELF -> Boot.arc location
        sles_bytes = bytes(iso_mm[elf_off : elf_off + elf_size])
        emb = sles_bytes.find(b'EMBEDED\x00FS')
        if emb < 0:
            sys.exit('EMBEDED magic not found in SLUS ELF')
        # 0x14-byte header after the magic: size at offset +0x14
        boot_size = struct.unpack_from('<I', sles_bytes, emb + 0x14)[0]
        boot_off  = emb + 0x38                     # offset of Boot.arc inside the ELF
        # Find Font_EUR (hash 0xF63BBFF1) in the embedded Boot.arc TOC
        boot = sles_bytes[emb + 0x38 : emb + 0x38 + boot_size]
        cnt = struct.unpack_from('<I', boot, 4)[0]
        font_index = font_csz = -1
        for i in range(cnt):
            h, off, csz, usz = struct.unpack_from('<IIII', boot, 16 + i*16)
            if h == FONT_HASH:
                font_index, font_csz = i, csz
                break
        if font_index < 0:
            sys.exit('Font_EUR entry not found in Boot.arc')
        iso_mm.close()
    print(f'  ELF at 0x{elf_off:x} size {elf_size}')
    print(f'  Boot.arc at 0x{boot_off:x} size {boot_size}')
    print(f'  Font_EUR entry [{font_index}] csz={font_csz}')
    print(f'  data.arc at 0x{data_arc_off:x} size {data_arc_size}')

    WORK.mkdir(parents=True, exist_ok=True)
    overrides = WORK / 'overrides'; overrides.mkdir(exist_ok=True)

    print('\n=== 2. Extract NTSC-U ELF + data.arc ===')
    sles_path = WORK / 'SLUS_orig.69'
    data_arc_path = WORK / 'data_orig.arc'
    with open(NTSC_ISO, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        sles_path.write_bytes(bytes(mm[elf_off : elf_off + elf_size]))
        data_arc_path.write_bytes(bytes(mm[data_arc_off : data_arc_off + data_arc_size]))
        mm.close()
    print(f'  saved orig ELF and data.arc')

    print('\n=== 3. Patch NTSC-U ELF: inject UA-patched Font_EUR ===')
    sles = sles_path.read_bytes()
    # Read TOC entry for font
    toc_pos = boot_off + 16 + font_index*16
    h, off, csz, usz = struct.unpack_from('<IIII', sles, toc_pos)
    assert h == FONT_HASH, f'unexpected font hash {h:x}'
    abs_off = boot_off + off

    # Always rebuild the raw font from scratch. kfont_png_edit.py inject
    # APPENDS new bitmap data to the region tail (never in-place reuse),
    # so consecutive builds accumulate dead bytes and eventually overflow
    # the 0x8000-byte budget. Wiping the raw file every build forces a
    # clean tail; PNG injection below reapplies the user's custom glyphs.
    raw_path = ROOT/'UA'/'_build'/'Font_EUR_ua_raw.bin'
    if raw_path.exists():
        raw_path.unlink()
    subprocess.check_call([sys.executable, str(TOOL/'patch_font_ua.py')],
                          stdout=subprocess.DEVNULL)
    # Repurpose Cyrillic Ё/ё slots as Ґ/ґ donors (uses Cyrillic Г/г as
    # initial bitmap). PNG injection below can overwrite with custom hooks.
    subprocess.check_call([sys.executable, str(TOOL/'add_gh_donors.py')],
                          stdout=subprocess.DEVNULL)

    # Inject any user-edited PNG overrides from unpacked/glyphs/.
    glyph_dir = ROOT / 'unpacked' / 'glyphs'
    if glyph_dir.exists():
        for png_name, cp in PNG_GLYPH_MAP.items():
            png_path = glyph_dir / png_name
            if png_path.exists():
                subprocess.check_call([sys.executable, str(TOOL/'kfont_png_edit.py'),
                                       'inject', hex(cp), '--in', str(png_path)],
                                      stdout=subprocess.DEVNULL)
                print(f'  inject U+{cp:04X} from {png_name}')

    # Always recompress raw font fresh (zopfli) so build picks up any
    # custom glyph edits made via kfont_png_edit.py since last build.
    try:
        import zopfli.zlib as _zopfli
        ua_font_comp = _zopfli.compress(raw_path.read_bytes(), numiterations=15)
    except ImportError:
        import zlib as _zlib
        ua_font_comp = _zlib.compress(raw_path.read_bytes(), level=9)
    (ROOT/'UA'/'_build'/'Font_EUR_ua_patched.bin').write_bytes(ua_font_comp)
    # usz stays at 32768 (KFONT decompressed size — engine expectation)
    ua_usz = 0x8000
    print(f'  UA-patched Font_EUR: csz={len(ua_font_comp)}, usz={ua_usz}')
    assert len(ua_font_comp) <= csz, (
        f'UA font {len(ua_font_comp)} B does not fit slot {csz} B')

    patched = bytearray(sles)
    patched[abs_off:abs_off+csz] = bytes(csz)
    patched[abs_off:abs_off+len(ua_font_comp)] = ua_font_comp
    struct.pack_into('<I', patched, toc_pos + 8,  len(ua_font_comp))
    struct.pack_into('<I', patched, toc_pos + 12, ua_usz)
    patched_elf_path = WORK / 'SLUS_patched.69'
    patched_elf_path.write_bytes(bytes(patched))
    print(f'  wrote patched SLUS ({len(patched)} bytes -- same size)')

    print('\n=== 4. Pack UA text into 1315 + 1316 ===')
    # Strings come from TEXT_TRANSLATION/ (shared + ps2_only).
    # pack_platform_strings reads shared.txt + ps2_only.txt, filters to
    # the platform's actual hash list (from .arc), and packs.
    subprocess.check_call([sys.executable, str(TOOL/'pack_platform_strings.py'),
                           'ps2_sys', str(overrides/'2c238264.bin')])
    subprocess.check_call([sys.executable, str(TOOL/'pack_platform_strings.py'),
                           'ps2_ui',  str(overrides/'2c238276.bin')])
    print(f'  packed strings to {overrides}')

    print('\n=== 5. Rebuild data.arc (in-place) ===')
    new_arc = WORK / 'data.arc'
    subprocess.check_call([sys.executable, str(TOOL/'arc_rebuild.py'),
                           str(data_arc_path), str(overrides), str(new_arc),
                           '--target-size', str(data_arc_size)], stdout=subprocess.DEVNULL)

    print('\n=== 6. Copy ISO and patch ===')
    shutil.copy2(NTSC_ISO, OUT_ISO)
    new_arc_bytes = new_arc.read_bytes()
    with open(OUT_ISO, 'r+b') as f:
        mm = mmap.mmap(f.fileno(), 0)
        # patch data.arc
        mm[data_arc_off : data_arc_off + len(new_arc_bytes)] = new_arc_bytes
        # patch ELF
        mm[elf_off : elf_off + len(patched)] = patched
        mm.flush(); mm.close()
    os.utime(OUT_ISO, (time.time(), time.time()))
    print(f'\nDONE: {OUT_ISO}')

if __name__ == '__main__':
    main()
