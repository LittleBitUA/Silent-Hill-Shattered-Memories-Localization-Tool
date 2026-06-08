"""
Patch Metallist's Font_EUR to add native CharRecord entries for Ukrainian
letters that currently require substitute (Є є Ї ї І і).

We repurpose donor CharRecord slots whose codepoints are Latin-1 supplement
characters never used in Ukrainian text:

    donor -> UA codepoint    bitmap source
    ¡  -> Є  (U+0404)         Cyrillic Э (U+042D, mirror C with mid bar)
    £  -> є  (U+0454)         Cyrillic э (U+044D)
    ®  -> Ї  (U+0407)         Cyrillic Ё (U+0401, "E with two dots")
    °  -> ї  (U+0457)         Cyrillic ё (U+0451)
    º  -> І  (U+0406)         Latin I (U+0049, exact base shape)
    ¿  -> і  (U+0456)         Latin i (U+0069)

After patching, text containing native UA codepoints renders via these
existing visually-similar glyphs. NO new bitmaps are drawn — we only
re-route codepoints. Output is fed back into Boot.arc inside the SLUS ELF.
"""
import struct, pathlib, zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUS_SLUS = ROOT / 'rus' / 'SLUS_218.99_rus'

# Patcher facility
import sys
sys.path.insert(0, str(ROOT/'tool'))
from kfont_patcher import (parse_records, serialize_records,
                            find_record_by_cp, get_rus_font_compressed,
                            TABLE_OFFSET, RECORD_SIZE)

# Try zopfli for tighter compression (matches what arc_rebuild uses)
try:
    import zopfli.zlib as _zopfli
    def _compress(data): return _zopfli.compress(data, numiterations=15)
    _COMPRESSOR = 'zopfli'
except ImportError:
    def _compress(data): return zlib.compress(data, level=9)
    _COMPRESSOR = 'zlib-9'

PATCHES = [
    # (donor_codepoint, target_ua_codepoint, source_glyph_codepoint, label)
    (0x00A1, 0x0404, 0x042D, 'Є -> uses Э glyph'),
    (0x00A3, 0x0454, 0x044D, 'є -> uses э glyph'),
    (0x00AE, 0x0407, 0x0401, 'Ї -> uses Ё glyph (E with dots)'),
    (0x00B0, 0x0457, 0x0451, 'ї -> uses ё glyph'),
    (0x00BA, 0x0406, 0x0049, 'І -> uses Latin I glyph'),
    (0x00BF, 0x0456, 0x0069, 'і -> uses Latin i glyph'),
]

def main():
    comp = get_rus_font_compressed()
    orig_csz = len(comp)
    font = zlib.decompress(comp)
    print(f'orig font: csz={orig_csz}, usz={len(font)}, compressor={_COMPRESSOR}')

    recs = parse_records(font)

    print('\nApplying UA patches:')
    for donor_cp, ua_cp, src_cp, label in PATCHES:
        donor = find_record_by_cp(recs, donor_cp)
        if donor is None:
            print(f'  SKIP (donor U+{donor_cp:04X} not in font): {label}')
            continue
        src = find_record_by_cp(recs, src_cp)
        if src is None:
            print(f'  SKIP (source U+{src_cp:04X} not in font): {label}')
            continue
        # Overwrite donor's codepoint + bitmap pointer to source
        donor['codepoint']     = ua_cp
        donor['advance']       = src['advance']
        donor['offset_x']      = src['offset_x']
        donor['offset_y']      = src['offset_y']
        donor['bw']            = src['bw']
        donor['bh']            = src['bh']
        donor['bitmap_offset'] = src['bitmap_offset']
        donor['bitmap_size']   = src['bitmap_size']
        print(f'  slot [{donor["idx"]}] U+{donor_cp:04X} -> U+{ua_cp:04X} '
              f'(bitmap from U+{src_cp:04X}): {label}')

    patched = serialize_records(font, recs)
    new_comp = _compress(patched)
    print(f'\npatched font: csz={len(new_comp)} (orig slot {orig_csz})')
    if len(new_comp) > orig_csz:
        raise SystemExit(f'compressed grew over slot! {len(new_comp)} > {orig_csz}')

    out = ROOT/'UA'/'_build'/'Font_EUR_ua_patched.bin'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(new_comp)
    print(f'wrote {out.relative_to(ROOT)} ({len(new_comp)} B)')

    out_raw = ROOT/'UA'/'_build'/'Font_EUR_ua_raw.bin'
    out_raw.write_bytes(patched)
    print(f'wrote {out_raw.relative_to(ROOT)} ({len(patched)} B decompressed)')

if __name__ == '__main__':
    main()
