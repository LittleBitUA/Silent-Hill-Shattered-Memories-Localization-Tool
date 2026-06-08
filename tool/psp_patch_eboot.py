"""
Patch Font_EUR embedded in EBOOT.BIN — the PSP engine reads the font
from there, NOT from DATA.ARC (same arrangement as Wii main.dol).

Source EBOOT.BIN is signed/encrypted (~PSP magic). We work on Metallist's
DECRYPTED EBOOT.BIN as a base (it's a standard ELF, no encryption). The
resulting EBOOT.BIN is also unsigned — PSP must have CFW to launch it.

Layout in Metallist's RU EBOOT.BIN (USA ULUS):
    zlib stream @ 0x34916C → 32768-byte Font_EUR (sig 78 5e)
    budget     = next zlib at 0x34BDEC → 11392 bytes total

UA modifications on top of Metallist's PSP RUS font (charCount 157 → 161):
  U+042D (Э) → U+0404 (Є)   codepoint relabel; bitmap rotated by user
  U+044D (э) → U+0454 (є)   codepoint relabel
  + U+00CF (Ï)              extension; copy of Latin I (user adds dots)
  + U+00EF (ï)              extension; restored from orig USA PSP font
  + U+0490 (Ґ)              extension; copy of Cyrillic Г, user adds hook
  + U+0491 (ґ)              extension; copy of Cyrillic г, user adds hook

Ї/ї are substituted to Latin Ï/ï via SH_EXTRA_SUBST='Ї=Ï,ї=ï' (in
build_ua_psp.py). The substitute lookup happens at string-pack time, so
the engine never sees the U+0407/U+0457 codepoints.
"""
import struct, zlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PSP_EBOOT = ROOT / 'psp_extract_work' / 'PSP_GAME' / 'SYSDIR' / 'EBOOT.BIN'
RUS_EBOOT = pathlib.Path(r'e:\Download\Silent Hill - Shattered Memories (Europe) (EnFrDeEsIt)\psp_rus_extract\PSP_GAME\SYSDIR\EBOOT.BIN')
ORIG_FONT = ROOT / 'UA_psp' / '_build' / 'Font_EUR_orig_psp.bin'
BUILD     = ROOT / 'UA_psp' / '_build'
BUILD.mkdir(parents=True, exist_ok=True)

FONT_OFF    = 0x34916C
FONT_BUDGET = 11392   # = 0x34BDEC - 0x34916C
SH_OFF      = 0x4D18   # sub-header offset in PSP Font_EUR (different from PS2/Wii)
TBL_OFF     = SH_OFF + 48

SWAPS = [
    (0x042D, 0x0404),   # Э -> Є
    (0x044D, 0x0454),   # э -> є
]
# Extension records: (new codepoint, source codepoint, source font)
#   'rus'  = Metallist's PSP RUS font (has Cyrillic, Latin)
#   'orig' = orig USA PSP font (has Latin-1 supplements including ï)
EXTENSIONS = [
    (0x00CF, 0x0049, 'rus'),   # Ï = copy of Latin I (user adds dots)
    (0x00EF, 0x00EF, 'orig'),  # ï = restored from orig USA font
    (0x0490, 0x0413, 'rus'),   # Ґ = copy of Cyrillic Г (user adds hook)
    (0x0491, 0x0433, 'rus'),   # ґ = copy of Cyrillic г
]

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
    if not RUS_EBOOT.exists():
        raise SystemExit(f'missing Metallist EBOOT.BIN at {RUS_EBOOT}')
    if not ORIG_FONT.exists():
        raise SystemExit(f'missing orig PSP Font_EUR at {ORIG_FONT}. '
                         f'Extract with: python -c \"...DATA.ARC idx 384...\"')

    rus_eboot = RUS_EBOOT.read_bytes()
    rus_font = zlib.decompress(rus_eboot[FONT_OFF:])
    print(f'Metallist PSP embedded font: {len(rus_font)} bytes')
    orig_font = ORIG_FONT.read_bytes()

    rus_sh, rus_tbl, rus_recs = parse_records(rus_font, SH_OFF)
    rus_br = rus_tbl + rus_sh[3]*16
    rus_bitmap = bytes(rus_font[rus_br : rus_br + max(r[6]+r[7] for r in rus_recs)])
    print(f'  charCount={rus_sh[3]} fontDataSize={rus_sh[2]} bitmap={len(rus_bitmap)} bytes')

    orig_sh, orig_tbl, orig_recs = parse_records(orig_font, SH_OFF)
    orig_br = orig_tbl + orig_sh[3]*16

    # Step 1: codepoint relabel
    swap = dict(SWAPS)
    for i, r in enumerate(rus_recs):
        if r[0] in swap:
            new_cp = swap[r[0]]
            rus_recs[i] = (new_cp,) + r[1:]
            print(f'  relabel [{i:3}] U+{r[0]:04X} -> U+{new_cp:04X}')

    new_recs = []
    new_bitmap = bytearray(rus_bitmap)

    for new_cp, src_cp, src in EXTENSIONS:
        font = rus_font if src == 'rus' else orig_font
        recs = rus_recs if src == 'rus' else orig_recs
        br = rus_br if src == 'rus' else orig_br
        for r in recs:
            if r[0] == src_cp:
                bm = bytes(font[br + r[6] : br + r[6] + r[7]])
                new_boff = len(new_bitmap)
                new_bitmap.extend(bm)
                new_recs.append((new_cp, r[1], r[2], r[3], r[4], r[5], new_boff, r[7], 0x0041))
                print(f'  + extend U+{new_cp:04X} (= U+{src_cp:04X} from {src}) '
                      f'bw={r[4]} bh={r[5]} bsz={r[7]}')
                break
        else:
            raise SystemExit(f'donor source U+{src_cp:04X} not in {src} font')

    # Assemble
    all_recs = rus_recs + new_recs
    new_cc = len(all_recs)
    new_fontDataSize = new_cc * 16 + len(new_bitmap)
    print(f'new charCount={new_cc} fontDataSize={new_fontDataSize}')

    pre_body  = bytes(rus_font[:SH_OFF])
    new_sh    = struct.pack('<HHIhhhH',
                            rus_sh[0], rus_sh[1], new_fontDataSize,
                            new_cc, rus_sh[4], rus_sh[5], rus_sh[6])
    unk_data  = bytes(rus_font[SH_OFF+16 : SH_OFF+48])
    char_data = b''.join(struct.pack('<HHbbBBIHH', *r) for r in all_recs)
    font_body = pre_body + new_sh + unk_data + char_data + bytes(new_bitmap)
    font_body += b'\x00' * ((-len(font_body)) & 3)
    font_body += b'\x00' * ((-len(font_body)) & 0xFFF)
    (BUILD / 'Font_EUR_psp_ua.bin').write_bytes(font_body)

    comp = compress(font_body)
    print(f'compressed {_NAME}: {len(comp)} bytes (budget {FONT_BUDGET})')
    if len(comp) > FONT_BUDGET:
        raise SystemExit(f'compressed font {len(comp)} > budget {FONT_BUDGET}')

    # Write to PSP_EBOOT (in our build work dir)
    PSP_EBOOT.parent.mkdir(parents=True, exist_ok=True)
    target = bytearray(rus_eboot)
    target[FONT_OFF : FONT_OFF + FONT_BUDGET] = b'\x00' * FONT_BUDGET
    target[FONT_OFF : FONT_OFF + len(comp)] = comp
    PSP_EBOOT.write_bytes(bytes(target))
    print(f'wrote patched EBOOT.BIN: {PSP_EBOOT}')

if __name__ == '__main__':
    main()
