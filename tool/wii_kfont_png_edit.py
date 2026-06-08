"""
PNG-based glyph editor for the Wii Font_EUR embedded in main.dol.

Workflow (same idea as kfont_png_edit.py for PS2, but operates on the
zlib-compressed font stream inside main.dol at offset 0x3F9F78):

  1. python tool/wii_kfont_png_edit.py extract 0x0404 --out unpacked/glyphs_wii/ye_upper.png
  2. Edit the PNG in any image editor (keep size; 0=transparent, 255=opaque).
  3. python tool/wii_kfont_png_edit.py inject 0x0404 --in unpacked/glyphs_wii/ye_upper.png

The inject step decompresses the embedded font, edits the glyph, bumps
fontDataSize as needed, re-compresses with zopfli, and writes back into
main.dol — staying within the 15392-byte budget (next zlib stream at
0x3FDB98 is the hard cap).
"""
import sys, struct, pathlib, zlib, argparse
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kfont_rle import decode, encode

ROOT = pathlib.Path(__file__).resolve().parent.parent
WII_DOL = ROOT / 'wii_extract' / 'DATA' / 'sys' / 'main.dol'
FONT_OFF    = 0x3F9F78
FONT_BUDGET = 15392
SH_OFF      = 0x5F66
TBL_OFF     = SH_OFF + 48

try:
    import zopfli.zlib as _z
    def _compress(d): return _z.compress(d, numiterations=30)
except ImportError:
    def _compress(d): return zlib.compress(d, level=9)

def load_font():
    dol = WII_DOL.read_bytes()
    return bytearray(zlib.decompress(dol[FONT_OFF:])), dol

def save_font(font, dol):
    comp = _compress(bytes(font))
    if len(comp) > FONT_BUDGET:
        raise SystemExit(f'compressed font {len(comp)} > budget {FONT_BUDGET}')
    out = bytearray(dol)
    out[FONT_OFF : FONT_OFF + FONT_BUDGET] = b'\x00' * FONT_BUDGET
    out[FONT_OFF : FONT_OFF + len(comp)] = comp
    WII_DOL.write_bytes(bytes(out))
    print(f'wrote {WII_DOL}: font compressed to {len(comp)}/{FONT_BUDGET} bytes')

def find_record(font, cp):
    sh = struct.unpack_from('<HHIhhhH', font, SH_OFF)
    cc = sh[3]
    for i in range(cc):
        r = struct.unpack_from('<HHbbBBIHH', font, TBL_OFF + i*16)
        if r[0] == cp:
            return i, r, sh, cc
    raise SystemExit(f'codepoint U+{cp:04X} not in font')

def cmd_extract(args):
    font, _ = load_font()
    cp = int(args.cp, 0)
    idx, rec, sh, cc = find_record(font, cp)
    bw, bh, boff, bsz = rec[4], rec[5], rec[6], rec[7]
    br = TBL_OFF + cc * 16
    bitmap = bytes(font[br + boff : br + boff + bsz])
    grid = decode(bitmap, bw, bh)
    # Build PNG: scale ×16, each pixel = 16x16 block of 0..255 grayscale
    SCALE = args.scale
    W = bw + (bw & 1)
    img = Image.new('L', (W * SCALE, bh * SCALE), 0)
    for y, row in enumerate(grid):
        for x, p in enumerate(row):
            grey = (p * 0xFF) // 0x0F
            for dy in range(SCALE):
                for dx in range(SCALE):
                    img.putpixel((x*SCALE+dx, y*SCALE+dy), grey)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f'extracted U+{cp:04X} idx={idx} bw={bw} bh={bh} bsz={bsz} -> {out}')

def cmd_inject(args):
    font, dol = load_font()
    cp = int(args.cp, 0)
    idx, rec, sh, cc = find_record(font, cp)
    bw, bh, boff_old, bsz_old = rec[4], rec[5], rec[6], rec[7]
    W = bw + (bw & 1)
    img = Image.open(args.in_path).convert('L')
    SCALE = img.width // W
    if SCALE < 1 or img.width != W*SCALE or img.height != bh*SCALE:
        raise SystemExit(f'PNG size {img.width}x{img.height} != expected '
                         f'{W*SCALE}x{bh*SCALE} for bw={bw}, bh={bh}')
    # Build grid by averaging each SCALE×SCALE block, threshold to nibble
    grid = [[0]*W for _ in range(bh)]
    for y in range(bh):
        for x in range(W):
            total = 0
            for dy in range(SCALE):
                for dx in range(SCALE):
                    total += img.getpixel((x*SCALE+dx, y*SCALE+dy))
            avg = total // (SCALE * SCALE)
            grid[y][x] = (avg * 0x0F) // 0xFF
    new_bm = encode(grid, bw)
    print(f'  encoded RLE: {len(new_bm)} bytes (was {bsz_old})')
    # Replace bitmap: write into bitmap region at end, update record
    br = TBL_OFF + cc * 16
    # Find last_used to know where to append (only append if new size doesn't fit in place)
    recs = [struct.unpack_from('<HHbbBBIHH', font, TBL_OFF + i*16) for i in range(cc)]
    last_used = max(r[6] + r[7] for r in recs)
    if len(new_bm) <= bsz_old:
        # fits in place
        font[br + boff_old : br + boff_old + len(new_bm)] = new_bm
        new_boff, new_bsz = boff_old, len(new_bm)
    else:
        # append to end
        new_boff = last_used
        font.extend(b'\x00' * 0)  # no-op
        # Write at br + last_used, padding font if needed
        end_pos = br + last_used + len(new_bm)
        if end_pos > len(font):
            font.extend(b'\x00' * (end_pos - len(font)))
        font[br + last_used : br + last_used + len(new_bm)] = new_bm
        new_bsz = len(new_bm)
    # Update record
    new_rec = (rec[0], rec[1], rec[2], rec[3], bw, bh, new_boff, new_bsz, rec[8])
    struct.pack_into('<HHbbBBIHH', font, TBL_OFF + idx*16, *new_rec)
    # Update fontDataSize
    last_used_new = max(struct.unpack_from('<HHbbBBIHH', font, TBL_OFF + i*16)[6]
                        + struct.unpack_from('<HHbbBBIHH', font, TBL_OFF + i*16)[7]
                        for i in range(cc))
    new_fontDataSize = cc * 16 + last_used_new
    struct.pack_into('<I', font, SH_OFF + 4, new_fontDataSize)
    print(f'  new fontDataSize={new_fontDataSize}, last_used={last_used_new}')
    save_font(font, dol)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    ex = sub.add_parser('extract')
    ex.add_argument('cp', help='codepoint (hex e.g. 0x0404)')
    ex.add_argument('--out', required=True)
    ex.add_argument('--scale', type=int, default=16)
    inj = sub.add_parser('inject')
    inj.add_argument('cp', help='codepoint (hex)')
    inj.add_argument('--in', dest='in_path', required=True)
    args = ap.parse_args()
    if args.cmd == 'extract':
        cmd_extract(args)
    else:
        cmd_inject(args)

if __name__ == '__main__':
    main()
