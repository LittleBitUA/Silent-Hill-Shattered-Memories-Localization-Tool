"""
KFONT RLE bitmap codec for Silent Hill: Shattered Memories fonts.

Ported from consolgames-tools FontEditor (Delphi):
    https://github.com/mbystryantsev/consolgames-tools

Format per glyph (`bsz` bytes pointed at by CharRecord.bitmap_offset):

  Stream of <count><payload> blocks.
  count byte (signed-like):
    0x01..0x7F  =>  STORE mode: <count> literal pairs follow (count bytes).
    0x80..0xFF  =>  RLE mode: (0x100 - count) repeats of next byte.

  Each "pair" byte holds 2 pixels (4 bits each):
    low nibble  = LEFT pixel
    high nibble = RIGHT pixel

  Pixels fill row-major over a grid of W aligned-to-even × H. When the
  current x reaches W, advance to next row (x=0).
"""
from typing import List

def decode(data: bytes, bw: int, bh: int) -> List[List[int]]:
    """Decode RLE-encoded glyph bytes to a (bh × W) 2D list of 4-bit
    pixel values, where W is bw rounded up to even."""
    W = bw + (bw & 1)
    grid = [[0]*W for _ in range(bh)]
    x = y = 0
    p = 0
    while p < len(data) and y < bh:
        count = data[p]; p += 1
        if count >= 0x80:
            count = 0x100 - count
            block = False
        else:
            block = True
        # In STORE mode the bytes that follow are individual pairs.
        # In RLE mode a SINGLE byte follows and is repeated `count` times.
        while count > 0:
            if x >= W:
                y += 1
                if y >= bh: break
                x = 0
            if p >= len(data): break
            b = data[p]
            grid[y][x]     = b & 0xF
            grid[y][x + 1] = (b >> 4) & 0xF
            x += 2
            if block:
                p += 1
            count -= 1
        if not block:
            p += 1
    return grid

def encode(grid: List[List[int]], bw: int) -> bytes:
    """Encode a (bh × W) pixel grid back to RLE bytes.
    bw is the logical glyph width (used to mask pad column when bw is odd)."""
    bh = len(grid)
    if bh == 0: return b''
    W = bw + (bw & 1)
    # Flatten into 1-byte pair stream (1 byte = 2 pixels)
    pairs = []
    for y in range(bh):
        for x in range(0, W, 2):
            p0 = grid[y][x] if x < bw else 0
            p1 = grid[y][x+1] if x+1 < bw else 0
            pairs.append(((p1 & 0xF) << 4) | (p0 & 0xF))

    out = bytearray()
    i = 0
    n = len(pairs)
    while i < n:
        # Detect run length of identical pairs at i
        run = 1
        while i + run < n and pairs[i + run] == pairs[i] and run < 128:
            run += 1
        if run >= 2:
            # RLE mode — single byte repeated
            out.append((0x100 - run) & 0xFF)
            out.append(pairs[i])
            i += run
        else:
            # STORE mode — collect non-RLE pairs up to 127
            start = i
            end = i + 1
            while end < n and end - start < 127:
                # peek ahead: if a run of >=2 starts at end, stop
                if end + 1 < n and pairs[end] == pairs[end + 1]:
                    break
                end += 1
            count = end - start
            out.append(count)
            out.extend(pairs[start:end])
            i = end
    return bytes(out)

if __name__ == '__main__':
    # Round-trip test on all glyphs in Metallist's Font_EUR
    import struct, pathlib, zlib
    ROOT = pathlib.Path(__file__).resolve().parent.parent
    elf = (ROOT/'rus'/'SLUS_218.99_rus').read_bytes()
    p = elf.find(b'EMBEDED\x00FS')
    sz = struct.unpack_from('<I', elf, p+0x14)[0]
    boot = elf[p+0x38:p+0x38+sz]
    cnt = struct.unpack_from('<I', boot, 4)[0]
    for i in range(cnt):
        h, off, csz, usz = struct.unpack_from('<IIII', boot, 16 + i*16)
        if h == 0xf63bbff1:
            font = zlib.decompress(boot[off:off+csz]); break

    BITMAP = 0x5778
    n_ok = n_diff_size = n_diff_pixel = n_skipped = 0
    diffs = []
    for j in range(161):
        rec = font[0x4D68+j*0x10 : 0x4D68+(j+1)*0x10]
        cp, adv, ox, oy, bw, bh, boff, bsz, base = struct.unpack('<HHbbBBIHH', rec)
        if bsz == 0 or bw == 0 or bh == 0:
            n_skipped += 1; continue
        data = font[BITMAP+boff : BITMAP+boff+bsz]
        grid = decode(data, bw, bh)
        re_enc = encode(grid, bw)
        # Round-trip decode
        grid2 = decode(re_enc, bw, bh)
        same_grid = (grid == grid2)
        same_bytes = (re_enc == data)
        if same_bytes:
            n_ok += 1
        elif same_grid:
            n_diff_size += 1
            if len(diffs) < 5:
                diffs.append((cp, j, len(data), len(re_enc), 'pixel-identical'))
        else:
            n_diff_pixel += 1
            if len(diffs) < 5:
                diffs.append((cp, j, len(data), len(re_enc), 'PIXEL DIFFERS'))
    print(f'Round-trip result: {n_ok} byte-identical, {n_diff_size} pixel-identical-different-bytes, '
          f'{n_diff_pixel} pixel-different (BUG), {n_skipped} skipped (empty)')
    for d in diffs:
        print(f'  cp=U+{d[0]:04X} idx={d[1]}  orig={d[2]}B  enc={d[3]}B  {d[4]}')
