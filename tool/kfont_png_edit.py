"""
PNG-based glyph editor for Metallist's Font_EUR.

Workflow:
  1. python tool/kfont_png_edit.py extract 0x0404 --out unpacked/glyphs/ye_upper.png
       Saves the glyph as a magnified PNG (default ×16 zoom, grayscale).
       Pixel values 0-15 map to 0-255 (16 levels of grey).
  2. Open the PNG in MS Paint / Photoshop / GIMP / any image editor.
       Draw / edit pixels using ANY shade of grey:
         pure black (0)   = transparent
         pure white (255) = fully opaque foreground
         intermediates     = anti-aliased intensities
  3. Save the PNG (KEEP the same scale and size — just paint over).
  4. python tool/kfont_png_edit.py inject 0x0404 --in unpacked/glyphs/ye_upper.png
       Downscales the PNG back to 4-bit pixels and patches the font.

Recommended editors:
  - MS Paint (Windows): F11 to zoom, View → Gridlines for pixel grid.
  - GIMP: open zoomed, use Pencil (1px), Tools → Color Picker for shades.
  - Aseprite / Piskel: native pixel-art editors with palettes.
"""
import sys, struct, pathlib, zlib, argparse
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kfont_rle import decode, encode

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUS_SLUS = ROOT / 'rus' / 'SLUS_218.99_rus'
TABLE_OFFSET = 0x4D68
BITMAP_REGION = 0x5778
RECORD_SIZE  = 0x10
RECORD_COUNT = 161
SLOT_SIZE = 14783   # max compressed Font_EUR (Boot.arc slot)

try:
    import zopfli.zlib as _zopfli
    def _compress(data): return _zopfli.compress(data, numiterations=15)
except ImportError:
    def _compress(data): return zlib.compress(data, level=9)

def get_rus_font_compressed():
    elf = RUS_SLUS.read_bytes()
    p = elf.find(b'EMBEDED\x00FS')
    size = struct.unpack_from('<I', elf, p+0x14)[0]
    boot = elf[p+0x38:p+0x38+size]
    cnt = struct.unpack_from('<I', boot, 4)[0]
    for i in range(cnt):
        h, off, csz, usz = struct.unpack_from('<IIII', boot, 16 + i*16)
        if h == 0xf63bbff1:
            return boot[off:off+csz]

def load_current_font():
    patched_raw = ROOT/'UA'/'_build'/'Font_EUR_ua_raw.bin'
    if patched_raw.exists():
        return bytearray(patched_raw.read_bytes())
    return bytearray(zlib.decompress(get_rus_font_compressed()))

def parse_records(font):
    recs = []
    for i in range(RECORD_COUNT):
        cp, adv, ox, oy, bw, bh, boff, bsz, base = struct.unpack_from(
            '<HHbbBBIHH', font, TABLE_OFFSET + i*RECORD_SIZE)
        recs.append(dict(idx=i, cp=cp, adv=adv, ox=ox, oy=oy,
                         bw=bw, bh=bh, boff=boff, bsz=bsz, base=base))
    return recs

def find_by_cp(recs, cp):
    for r in recs:
        if r['cp'] == cp: return r
    raise SystemExit(f'codepoint U+{cp:04X} not in font')

def grid_to_png(grid, bw, bh, scale=16):
    """Build PNG. Width = round-up(bw)*scale. Each cell of 4-bit value
    becomes a `scale × scale` block of grayscale (value × 17, so 0→0,
    15→255)."""
    W = bw + (bw & 1)
    img = Image.new('L', (W*scale, bh*scale), 0)
    px = img.load()
    for y in range(bh):
        for x in range(W):
            v = grid[y][x]
            g = v * 17                       # 0..15 → 0..255 even spread
            for dy in range(scale):
                for dx in range(scale):
                    px[x*scale+dx, y*scale+dy] = g
    return img

def png_to_grid(img, bw_hint, bh_hint, scale=16):
    """Read PNG: average each scale×scale block, quantize to 4 bits."""
    img = img.convert('L')
    iw, ih = img.size
    if iw % scale or ih % scale:
        raise SystemExit(f'PNG dims {iw}×{ih} must be multiples of scale={scale}')
    bw = iw // scale
    bh = ih // scale
    px = img.load()
    grid = [[0]*bw for _ in range(bh)]
    for y in range(bh):
        for x in range(bw):
            # average the scale×scale block
            total = 0
            for dy in range(scale):
                for dx in range(scale):
                    total += px[x*scale+dx, y*scale+dy]
            avg = total // (scale*scale)
            # Round to nearest of 16 levels (0..15 → 0,17,34,51,..,255)
            v = (avg + 8) // 17
            if v > 15: v = 15
            grid[y][x] = v
    return grid, bw, bh

def cmd_extract(args):
    cp = int(args.codepoint, 0)
    scale = args.scale
    font = load_current_font()
    recs = parse_records(font)
    r = find_by_cp(recs, cp)
    data = bytes(font[BITMAP_REGION + r['boff'] : BITMAP_REGION + r['boff'] + r['bsz']])
    grid = decode(data, r['bw'], r['bh'])
    img = grid_to_png(grid, r['bw'], r['bh'], scale=scale)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f'wrote {out_path}  ({img.size[0]}x{img.size[1]}, scale=x{scale}, '
          f'glyph {r["bw"]}x{r["bh"]})', file=sys.stderr)

def cmd_inject(args):
    cp = int(args.codepoint, 0)
    scale = args.scale
    img = Image.open(args.inp)
    grid, new_bw, new_bh = png_to_grid(img, None, None, scale=scale)
    font = load_current_font()
    recs = parse_records(font)
    r = find_by_cp(recs, cp)
    print(f'  Glyph U+{cp:04X} dims: orig={r["bw"]}x{r["bh"]}, new={new_bw}x{new_bh}',
          file=sys.stderr)
    new_data = encode(grid, new_bw)
    print(f'  Encoded RLE: {len(new_data)} bytes (orig {r["bsz"]})', file=sys.stderr)

    bitmap_total = 0x8000 - BITMAP_REGION
    # First 3 records (idx 0-2) are KFONT header bytes interpreted as
    # CharRecords by our naive parser; they have garbage boff. Skip them.
    last_used = max(
        rr['boff'] + rr['bsz']
        for rr in recs
        if rr['boff'] + rr['bsz'] <= bitmap_total
    )
    print(f'  bitmap region: used {last_used} / {bitmap_total} B; '
          f'free tail: {bitmap_total - last_used} B', file=sys.stderr)
    if last_used + len(new_data) > bitmap_total:
        raise SystemExit(f'no room: need {len(new_data)} B, only {bitmap_total - last_used} B free')
    new_boff = last_used
    font[BITMAP_REGION + new_boff : BITMAP_REGION + new_boff + len(new_data)] = new_data

    r['bw'] = new_bw
    r['bh'] = new_bh
    r['boff'] = new_boff
    r['bsz'] = len(new_data)
    if r['adv'] < new_bw:
        r['adv'] = new_bw
    struct.pack_into('<HHbbBBIHH', font, TABLE_OFFSET + r['idx']*RECORD_SIZE,
                     r['cp'], r['adv'], r['ox'], r['oy'],
                     r['bw'], r['bh'], r['boff'], r['bsz'], r['base'])

    # Bump fontDataSize in sub-header to include new bitmap usage.
    # Sub-header layout: <HHIhhhH> at TABLE_OFFSET (which actually points
    # at sub-header in our naming). Field [2] = fontDataSize (u32) at +4.
    # Real CharRecord table comes after sub-header + unkFontData (48 B),
    # i.e. real records start at TABLE_OFFSET+48. fontDataSize covers
    # records + bitmap data.
    new_last_used = r['boff'] + r['bsz']
    actual_last_used = max(rr['boff'] + rr['bsz'] for rr in recs
                            if rr['boff'] + rr['bsz'] <= bitmap_total)
    actual_last_used = max(actual_last_used, new_last_used)
    REAL_REC_COUNT = 158
    new_fdsz = REAL_REC_COUNT * 16 + actual_last_used
    old_fdsz = struct.unpack_from('<I', font, TABLE_OFFSET + 4)[0]
    struct.pack_into('<I', font, TABLE_OFFSET + 4, new_fdsz)
    print(f'  bumped fontDataSize: {old_fdsz} -> {new_fdsz}', file=sys.stderr)

    raw_out = ROOT/'UA'/'_build'/'Font_EUR_ua_raw.bin'
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    raw_out.write_bytes(bytes(font))
    comp = _compress(bytes(font))
    if len(comp) > SLOT_SIZE:
        raise SystemExit(f'compressed font {len(comp)} > slot {SLOT_SIZE}')
    out = ROOT/'UA'/'_build'/'Font_EUR_ua_patched.bin'
    out.write_bytes(comp)
    print(f'  wrote {out.relative_to(ROOT)} ({len(comp)} B compressed)',
          file=sys.stderr)
    print('  Now run: python tool/build_ua_ntsc.py', file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description='KFONT glyph editor (PNG)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    pe = sub.add_parser('extract')
    pe.add_argument('codepoint')
    pe.add_argument('--out', required=True)
    pe.add_argument('--scale', type=int, default=16)
    pi = sub.add_parser('inject')
    pi.add_argument('codepoint')
    pi.add_argument('--in', dest='inp', required=True)
    pi.add_argument('--scale', type=int, default=16)
    args = ap.parse_args()
    if args.cmd == 'extract': cmd_extract(args)
    elif args.cmd == 'inject': cmd_inject(args)

if __name__ == '__main__':
    main()
