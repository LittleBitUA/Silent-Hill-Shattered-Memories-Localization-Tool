"""
Patch the Font_EUR embedded in main.dol — this is the font the Wii engine
actually uses for rendering. The Font_EUR in data.arc is loaded but NOT
the one consulted at draw time.

Layout in main.dol (USA NTSC-U R5WEA4):
    data section 12 file @ 0x3DAF80..0x453540, load @ 0x803DEE80
    zlib(36864 bytes) stream @ 0x3F9F78..0x3FDB7D  ← Font_EUR
    budget = next stream at 0x3FDB98 - 0x3F9F78 = 15392 bytes

Base font for our build: Metallist's RUS main.dol embedded font (157
records, has all Russian Cyrillic via donor approach on Latin-1 slots,
verified compresses to ~14779 with zopfli — leaves room for UA edits).

UA strategy on Wii (built atop Metallist's RUS main.dol font):

    Cyrillic letter   Wii treatment
    ---------------   -------------
    А В Е К М Н О Р С Т Х (а е о р с у х) — CYR2LAT_SUBST → Latin lookalike
    Б Г Д Ж И Й Л П У Ф Ц Ч Ш Щ Ъ Ы Ь Э Ю Я (+ lowercase) — Metallist
        already added these as Cyrillic CharRecords
    Ё ё — Metallist included (used by Russian)
    Є є — donor SWAP: U+042D Э → U+0404 Є, U+044D э → U+0454 є
        (visual rotation; user will redraw bitmap)
    І і — CYR2LAT_SUBST → Latin I/i
    Ї ї — CYR2LAT_SUBST → Latin Ï/ï (U+00CF / U+00EF); we ADD these
        records back to the font (Metallist had removed them) by
        EXTENDING with bitmaps from the original USA Wii Font_EUR.
    Ґ ґ — EXTEND with new records U+0490 / U+0491; initial bitmap is a
        copy of Cyrillic Г/г from Metallist's font (visual placeholder;
        user redraws the hook later via PNG inject, same as PS2).

Result: charCount goes from 157 → 161 (+4 extension records).
"""
import struct, zlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / 'UA_wii' / '_build'
BUILD.mkdir(parents=True, exist_ok=True)

WII_DOL    = ROOT / 'wii_extract' / 'DATA' / 'sys' / 'main.dol'
RUS_DOL    = pathlib.Path(r'E:\Download\shsm_wii_rus_by_metallist\work\extract\DATA\sys\main.dol')
ORIG_FONT  = ROOT / 'wii_extract' / 'Font_EUR.bin'   # decompressed orig USA Font_EUR
FONT_OFF   = 0x3F9F78
FONT_BUDGET = 15392   # = 0x3FDB98 - 0x3F9F78

# UA donor swaps inside Metallist's font (codepoint relabel only)
SWAPS = [
    (0x042D, 0x0404),   # Э -> Є
    (0x044D, 0x0454),   # э -> є
]

# Codepoints to re-add (extension) from orig USA Wii Font_EUR.
# Orig USA Wii has ï (U+00EF, lowercase with diaeresis). We re-add it
# (Metallist had stripped it).
ADD_FROM_ORIG = [0x00EF]

# Ï uppercase (U+00CF) is NOT in any platform's orig font (also not in PS2
# USA). We create a new record by COPYING the Latin I bitmap from
# Metallist's font as a placeholder — the user will redraw it later
# (add the diaeresis dots) via the kfont_png_edit workflow.
ADD_FROM_LATIN = [(0x0049, 0x00CF)]    # (source Latin codepoint, target codepoint)

SH_OFF      = 0x5F66
TBL_OFF     = SH_OFF + 48

try:
    import zopfli.zlib as _z
    def compress(d): return _z.compress(d, numiterations=30)
    _NAME = 'zopfli-30'
except ImportError:
    def compress(d): return zlib.compress(d, level=9)
    _NAME = 'zlib-9'

def parse_records(font, sh_off):
    sh = struct.unpack_from('<HHIhhhH', font, sh_off)
    tbl = sh_off + 48
    recs = [struct.unpack_from('<HHbbBBIHH', font, tbl + i*16) for i in range(sh[3])]
    return sh, tbl, recs

def main():
    if not RUS_DOL.exists():
        raise SystemExit(f'missing Metallist main.dol at {RUS_DOL}. '
                         f'Run the imagePatch first under shsm_wii_rus_by_metallist/.')
    if not ORIG_FONT.exists():
        raise SystemExit(f'missing decompressed orig USA Font_EUR at {ORIG_FONT}')

    rus_dol = RUS_DOL.read_bytes()
    rus_font = zlib.decompress(rus_dol[FONT_OFF:])
    print(f'Metallist embedded font: {len(rus_font)} bytes (decompressed)')

    orig_font = ORIG_FONT.read_bytes()
    print(f'Orig USA Font_EUR: {len(orig_font)} bytes')

    # Parse Metallist
    rus_sh, rus_tbl, rus_recs = parse_records(rus_font, SH_OFF)
    rus_cc = rus_sh[3]
    rus_bitmap_region = rus_tbl + rus_cc * 16
    rus_bitmap = bytes(rus_font[rus_bitmap_region : rus_bitmap_region
                                + max(r[6]+r[7] for r in rus_recs)])
    print(f'  charCount={rus_cc} fontDataSize={rus_sh[2]}, bitmap region {len(rus_bitmap)} bytes')

    # Parse orig USA (for Ï / ï bitmaps)
    orig_sh, orig_tbl, orig_recs = parse_records(orig_font, SH_OFF)
    orig_bitmap_region = orig_tbl + orig_sh[3] * 16

    # Step 1: codepoint relabel (Э→Є, э→є)
    swap_dict = dict(SWAPS)
    relabeled = []
    for i, r in enumerate(rus_recs):
        if r[0] in swap_dict:
            new_cp = swap_dict[r[0]]
            relabeled.append((i, r[0], new_cp))
            rus_recs[i] = (new_cp,) + r[1:]
    for i, old, new in relabeled:
        print(f'  relabel [{i:3}] U+{old:04X} -> U+{new:04X}')

    # Step 2: extend with Ï (U+00CF) and ï (U+00EF) from orig USA
    new_recs = []
    new_bitmap_blob = bytearray(rus_bitmap)
    for add_cp in ADD_FROM_ORIG:
        for r in orig_recs:
            if r[0] == add_cp:
                # Copy bitmap bytes
                bm = orig_font[orig_bitmap_region + r[6] : orig_bitmap_region + r[6] + r[7]]
                new_boff = len(new_bitmap_blob)
                new_bitmap_blob.extend(bm)
                new_recs.append((add_cp, r[1], r[2], r[3], r[4], r[5],
                                 new_boff, r[7], 0x0041))
                print(f'  + extend U+{add_cp:04X} bw={r[4]} bh={r[5]} bsz={r[7]} (from orig USA)')
                break
        else:
            raise SystemExit(f'U+{add_cp:04X} not in orig USA font')

    # Step 2b: add Ï (U+00CF) as copy of Latin I from Metallist's font
    for src_cp, new_cp in ADD_FROM_LATIN:
        for r in rus_recs:
            if r[0] == src_cp:
                bm = bytes(rus_font[rus_bitmap_region + r[6] : rus_bitmap_region + r[6] + r[7]])
                new_boff = len(new_bitmap_blob)
                new_bitmap_blob.extend(bm)
                new_recs.append((new_cp, r[1], r[2], r[3], r[4], r[5],
                                 new_boff, r[7], 0x0041))
                print(f'  + extend U+{new_cp:04X} (copy of Latin U+{src_cp:04X}) bw={r[4]} bh={r[5]} bsz={r[7]}')
                break
        else:
            raise SystemExit(f'source U+{src_cp:04X} not in Metallist font')

    # Step 3: add Ґ (U+0490) and ґ (U+0491) as copies of Cyrillic Г / г
    GHE_SOURCES = [(0x0413, 0x0490), (0x0433, 0x0491)]
    for src_cp, new_cp in GHE_SOURCES:
        for r in rus_recs:
            if r[0] == src_cp:
                # Copy Metallist's Г bitmap
                bm = bytes(rus_font[rus_bitmap_region + r[6] : rus_bitmap_region + r[6] + r[7]])
                new_boff = len(new_bitmap_blob)
                new_bitmap_blob.extend(bm)
                new_recs.append((new_cp, r[1], r[2], r[3], r[4], r[5],
                                 new_boff, r[7], 0x0041))
                print(f'  + extend U+{new_cp:04X} (copy of U+{src_cp:04X}) bw={r[4]} bh={r[5]} bsz={r[7]}')
                break
        else:
            raise SystemExit(f'source U+{src_cp:04X} not in Metallist font')

    # Build new font
    all_recs = rus_recs + new_recs
    new_cc = len(all_recs)
    new_fontDataSize = new_cc * 16 + len(new_bitmap_blob)
    print(f'new charCount={new_cc}, new fontDataSize={new_fontDataSize}')

    pre_body  = bytes(rus_font[:SH_OFF])
    new_sh    = struct.pack('<HHIhhhH',
                            rus_sh[0], rus_sh[1], new_fontDataSize,
                            new_cc, rus_sh[4], rus_sh[5], rus_sh[6])
    unk_data  = bytes(rus_font[SH_OFF + 16 : SH_OFF + 48])
    char_data = b''.join(struct.pack('<HHbbBBIHH', *r) for r in all_recs)
    font_body = pre_body + new_sh + unk_data + char_data + bytes(new_bitmap_blob)
    # 4-byte align
    font_body += b'\x00' * ((-len(font_body)) & 3)
    # Pad to 0x1000 (matches original 36864-byte layout — engine may rely on
    # fixed buffer sizing). Actually engine uses fontDataSize allocation;
    # padding is for nice rounding only.
    font_body += b'\x00' * ((-len(font_body)) & 0xFFF)
    (BUILD / 'Font_EUR_wii_ua_dol.bin').write_bytes(font_body)

    comp = compress(font_body)
    print(f'compressed {_NAME}: {len(comp)} bytes (budget {FONT_BUDGET})')
    if len(comp) > FONT_BUDGET:
        raise SystemExit(f'compressed font {len(comp)} > budget {FONT_BUDGET} — '
                         f'need to reduce content or relocate.')

    if not WII_DOL.exists():
        raise SystemExit(f'missing wii_extract main.dol at {WII_DOL}')
    target = bytearray(WII_DOL.read_bytes())
    target[FONT_OFF : FONT_OFF + FONT_BUDGET] = b'\x00' * FONT_BUDGET
    target[FONT_OFF : FONT_OFF + len(comp)] = comp
    WII_DOL.write_bytes(bytes(target))
    print(f'wrote patched main.dol: {WII_DOL} ({len(target)} bytes)')

if __name__ == '__main__':
    main()
