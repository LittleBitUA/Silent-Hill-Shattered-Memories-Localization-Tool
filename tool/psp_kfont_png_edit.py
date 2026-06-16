"""
PNG-based glyph editor for the PSP Font_EUR embedded in EBOOT.BIN.

Same idea as wii_kfont_png_edit.py but with PSP offsets:
  EBOOT.BIN zlib stream @ 0x34916C, decompresses to 32768-byte Font_EUR
  sub-header @ 0x4D18, CharRecord table @ 0x4D48
  budget for repacked compressed font = 11392 bytes

Usage:
  python tool/psp_kfont_png_edit.py extract 0x0490 --out unpacked/glyphs_psp/gh_upper.png
  # edit the PNG (keep size; 0=transparent, 255=opaque)
  python tool/psp_kfont_png_edit.py inject 0x0490 --in unpacked/glyphs_psp/gh_upper.png
  # rebuild ISO:
  python tool/build_ua_psp.py
"""
import sys, struct, pathlib, zlib, argparse
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kfont_rle import decode, encode

ROOT = pathlib.Path(__file__).resolve().parent.parent
PSP_EBOOT = ROOT / 'psp_extract_work' / 'PSP_GAME' / 'SYSDIR' / 'EBOOT.BIN'
FONT_OFF    = 0x34916C
FONT_BUDGET = 11392
SH_OFF      = 0x4D18
TBL_OFF     = SH_OFF + 48

try:
    import zopfli.zlib as _z
    def _compress(d): return _z.compress(d, numiterations=30)
except ImportError:
    def _compress(d): return zlib.compress(d, level=9)

def load_font():
    dol = PSP_EBOOT.read_bytes()
    return bytearray(zlib.decompress(dol[FONT_OFF:])), dol

def save_font(font, dol):
    comp = _compress(bytes(font))
    if len(comp) > FONT_BUDGET:
        raise SystemExit(f'compressed font {len(comp)} > budget {FONT_BUDGET}')
    out = bytearray(dol)
    out[FONT_OFF : FONT_OFF + FONT_BUDGET] = b'\x00' * FONT_BUDGET
    out[FONT_OFF : FONT_OFF + len(comp)] = comp
    PSP_EBOOT.write_bytes(bytes(out))
    print(f'wrote {PSP_EBOOT}: font {len(comp)}/{FONT_BUDGET} bytes')

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
    bw_old, bh_old, boff_old, bsz_old = rec[4], rec[5], rec[6], rec[7]
    SCALE = args.scale
    img = Image.open(args.in_path).convert('L')
    if img.width % SCALE or img.height % SCALE:
        raise SystemExit(f'PNG dims {img.width}x{img.height} must be multiples of scale={SCALE}')
    new_W = img.width // SCALE
    new_bh = img.height // SCALE
    new_bw = new_W - (new_W & 1) if new_W & 1 else new_W
    # When bw is odd, the row is padded to an even count of nibbles in
    # storage, so the PNG canvas width is (bw + 1) * SCALE pixels. Detect
    # both even and odd cases here.
    if new_W == bw_old + (bw_old & 1):
        new_bw = bw_old   # canvas matches old odd-bw padding
    else:
        new_bw = new_W if not (new_W & 1) else new_W - 1
    W = new_bw + (new_bw & 1)
    if W != new_W:
        # Fall back: assume PNG width = bw exactly (no odd padding)
        new_bw = new_W
        W = new_bw
    if (new_bw, new_bh) != (bw_old, bh_old):
        print(f'  resize U+{cp:04X}: {bw_old}x{bh_old} -> {new_bw}x{new_bh}')
    grid = [[0]*W for _ in range(new_bh)]
    for y in range(new_bh):
        for x in range(W):
            total = 0
            for dy in range(SCALE):
                for dx in range(SCALE):
                    total += img.getpixel((x*SCALE+dx, y*SCALE+dy))
            avg = total // (SCALE * SCALE)
            grid[y][x] = (avg * 0x0F) // 0xFF
    new_bm = encode(grid, new_bw)
    print(f'  encoded RLE: {len(new_bm)} bytes (was {bsz_old})')
    br = TBL_OFF + cc * 16
    recs = [struct.unpack_from('<HHbbBBIHH', font, TBL_OFF + i*16) for i in range(cc)]
    last_used = max(r[6] + r[7] for r in recs)
    if len(new_bm) <= bsz_old:
        font[br + boff_old : br + boff_old + len(new_bm)] = new_bm
        new_boff, new_bsz = boff_old, len(new_bm)
    else:
        new_boff = last_used
        end_pos = br + last_used + len(new_bm)
        if end_pos > len(font):
            font.extend(b'\x00' * (end_pos - len(font)))
        font[br + last_used : br + last_used + len(new_bm)] = new_bm
        new_bsz = len(new_bm)
    adv = rec[1] if rec[1] >= new_bw else new_bw
    new_rec = (rec[0], adv, rec[2], rec[3], new_bw, new_bh, new_boff, new_bsz, rec[8])
    struct.pack_into('<HHbbBBIHH', font, TBL_OFF + idx*16, *new_rec)
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
    ex.add_argument('cp', help='codepoint (hex e.g. 0x0490)')
    ex.add_argument('--out', required=True)
    ex.add_argument('--scale', type=int, default=16)
    inj = sub.add_parser('inject')
    inj.add_argument('cp', help='codepoint (hex)')
    inj.add_argument('--in', dest='in_path', required=True)
    inj.add_argument('--scale', type=int, default=16,
                     help='upscale factor used when the PNG was produced (default 16)')
    args = ap.parse_args()
    if args.cmd == 'extract':
        cmd_extract(args)
    else:
        cmd_inject(args)

if __name__ == '__main__':
    main()
