"""
Repurpose Cyrillic Ё/ё CharRecord slots in the patched font as donors for
Ukrainian Ґ ґ (U+0490 / U+0491). Ukrainian text doesn't use Russian Ё/ё.

Initial bitmap pointer: Cyrillic Г / г (existing native glyphs). User then
runs `kfont_png_edit.py inject 0x0490 / 0x0491` with their custom drawings
to overwrite the bitmap.

Notes:
  - Ї/ї in our patched font also reference Cyrillic Ё/ё bitmaps via their
    bitmap_offset fields. Those references are by file OFFSET, not by
    codepoint — so changing Ё's codepoint to U+0490 here doesn't break
    Ї/ї rendering.
  - This must be re-run if Font_EUR_ua_raw.bin is deleted and patch_font_ua.py
    re-creates the base.
"""
import struct, pathlib, zlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'tool'))
from kfont_rle import decode  # noqa

TABLE_OFFSET = 0x4D68
RECORD_SIZE  = 0x10
RECORD_COUNT = 161
SLOT_SIZE = 14783

try:
    import zopfli.zlib as _z
    def _compress(d): return _z.compress(d, numiterations=15)
except ImportError:
    def _compress(d): return zlib.compress(d, level=9)

def parse_recs(font):
    return [struct.unpack_from('<HHbbBBIHH', font, TABLE_OFFSET+i*RECORD_SIZE)
            for i in range(RECORD_COUNT)]

raw_path = ROOT/'UA'/'_build'/'Font_EUR_ua_raw.bin'
font = bytearray(raw_path.read_bytes())
recs = parse_recs(font)

PATCHES = [
    (0x0401, 0x0490, 0x0413, 'Cyrillic Ё  -> Ґ (uses Cyrillic Г glyph)'),
    (0x0451, 0x0491, 0x0433, 'Cyrillic ё  -> ґ (uses Cyrillic г glyph)'),
]

for donor_cp, ua_cp, src_cp, label in PATCHES:
    donor_idx = None
    src = None
    for i, r in enumerate(recs):
        if r[0] == donor_cp:
            donor_idx = i
        if r[0] == src_cp:
            src = r
    if donor_idx is None or src is None:
        print(f'  SKIP: donor U+{donor_cp:04X} or source U+{src_cp:04X} not found')
        continue
    # Overwrite donor slot
    new_rec = (ua_cp, src[1], src[2], src[3], src[4], src[5], src[6], src[7], src[8])
    struct.pack_into('<HHbbBBIHH', font, TABLE_OFFSET + donor_idx*RECORD_SIZE, *new_rec)
    print(f'  slot [{donor_idx}] U+{donor_cp:04X} -> U+{ua_cp:04X} ({label})')

raw_path.write_bytes(bytes(font))
comp = _compress(bytes(font))
if len(comp) > SLOT_SIZE:
    raise SystemExit(f'compressed font {len(comp)} > slot {SLOT_SIZE}')
(ROOT/'UA'/'_build'/'Font_EUR_ua_patched.bin').write_bytes(comp)
print(f'wrote font: csz={len(comp)}')
