"""
Extract a glyph from the ORIGINAL USA SLUS Font_EUR (not Metallist's).
Saves as a PNG ready to be injected into our patched font via
kfont_png_edit.py inject.
"""
import sys, struct, pathlib, zlib, argparse
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kfont_rle import decode

ROOT = pathlib.Path(__file__).resolve().parent.parent
USA_ISO = ROOT / 'Silent Hill - Shattered Memories (USA) (En,Fr,Es).iso'

def get_usa_font():
    elf = USA_ISO.read_bytes()[0x9c000:0x9c000+4812240]
    p = elf.find(b'EMBEDED\x00FS')
    size = struct.unpack_from('<I', elf, p+0x14)[0]
    boot = elf[p+0x38:p+0x38+size]
    cnt = struct.unpack_from('<I', boot, 4)[0]
    for i in range(cnt):
        h, off, csz, usz = struct.unpack_from('<IIII', boot, 16 + i*16)
        if h == 0xf63bbff1:
            return zlib.decompress(boot[off:off+csz])

def grid_to_png(grid, bw, scale=16):
    W = bw + (bw & 1)
    bh = len(grid)
    img = Image.new('L', (W*scale, bh*scale), 0)
    px = img.load()
    for y in range(bh):
        for x in range(W):
            g = grid[y][x] * 17
            for dy in range(scale):
                for dx in range(scale):
                    px[x*scale+dx, y*scale+dy] = g
    return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('codepoint', help='source codepoint, e.g. 0x00EF for i with dots')
    ap.add_argument('--out', required=True)
    ap.add_argument('--scale', type=int, default=16)
    args = ap.parse_args()
    cp = int(args.codepoint, 0)
    font = get_usa_font()
    # Sub-header at 0x4D68 tells us charCount; bitmap region starts after
    # real table = 0x4D68 + 16 (sub-header) + 32 (unkFontData) + charCount*16.
    sh = struct.unpack_from('<HHIhhhH', font, 0x4D68)
    charCount = sh[3]
    real_table = 0x4D68 + 16 + 32
    bitmap_region = real_table + charCount * 16
    print(f'  USA font: charCount={charCount}, real table @ 0x{real_table:x}, '
          f'bitmap region @ 0x{bitmap_region:x}', file=sys.stderr)

    # Iterate real records only
    for j in range(charCount):
        rec_cp, adv, ox, oy, bw, bh, boff, bsz, base = struct.unpack_from(
            '<HHbbBBIHH', font, real_table + j*0x10)
        if rec_cp == cp:
            data = font[bitmap_region+boff : bitmap_region+boff+bsz]
            grid = decode(data, bw, bh)
            img = grid_to_png(grid, bw, args.scale)
            out = pathlib.Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out)
            print(f'wrote {out}: glyph {bw}x{bh}, PNG {img.size[0]}x{img.size[1]}',
                  file=sys.stderr)
            return
    raise SystemExit(f'codepoint U+{cp:04X} not in USA font')

if __name__ == '__main__':
    main()
