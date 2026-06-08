"""
KFONT structural patcher for Metallist's Font_EUR.

Operates ONLY at the CharRecord level (does not touch RLE bitmap data).

Use cases:
  1. Identity round-trip — verify our parser/serializer is exact.
  2. Redirect codepoints — overwrite an unused donor CharRecord's
     codepoint with a UA codepoint, optionally repoint bitmap_offset
     to a visually similar existing glyph.

CharRecord layout (16 bytes):
    u16 codepoint
    u16 advance_width
    s8  offset_x
    s8  offset_y
    u8  bitmap_width
    u8  bitmap_height
    u32 bitmap_offset       # into bitmap data region (font[0x5778:])
    u16 bitmap_size
    u16 baseline (=0x0041)

Table location: font[0x4D68 : 0x4D68 + 161*0x10] = font[0x4D68:0x5778]
"""
import struct, pathlib, zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TABLE_OFFSET = 0x4D68
RECORD_SIZE  = 0x10
RECORD_COUNT = 161
BITMAP_REGION = 0x5778

def get_rus_font_compressed():
    elf = (ROOT/'rus'/'SLUS_218.99_rus').read_bytes()
    p = elf.find(b'EMBEDED\x00FS')
    size = struct.unpack_from('<I', elf, p+0x14)[0]
    boot = elf[p+0x38:p+0x38+size]
    cnt = struct.unpack_from('<I', boot, 4)[0]
    for i in range(cnt):
        h, off, csz, usz = struct.unpack_from('<IIII', boot, 16 + i*16)
        if h == 0xf63bbff1:
            return boot[off:off+csz]

def parse_records(font: bytes):
    recs = []
    for i in range(RECORD_COUNT):
        off = TABLE_OFFSET + i*RECORD_SIZE
        cp, adv, ox, oy, bw, bh, boff, bsz, base = struct.unpack_from(
            '<HHbbBBIHH', font, off)
        recs.append(dict(
            idx=i, codepoint=cp, advance=adv, offset_x=ox, offset_y=oy,
            bw=bw, bh=bh, bitmap_offset=boff, bitmap_size=bsz, baseline=base,
        ))
    return recs

def serialize_records(font: bytes, recs) -> bytes:
    out = bytearray(font)
    for r in recs:
        struct.pack_into('<HHbbBBIHH', out, TABLE_OFFSET + r['idx']*RECORD_SIZE,
                         r['codepoint'], r['advance'], r['offset_x'], r['offset_y'],
                         r['bw'], r['bh'], r['bitmap_offset'],
                         r['bitmap_size'], r['baseline'])
    return bytes(out)

def find_record_by_cp(recs, cp):
    for r in recs:
        if r['codepoint'] == cp:
            return r
    return None

def copy_glyph(recs, src_cp, dst_idx, new_cp):
    """Overwrite recs[dst_idx]: keep dst's idx position, copy src's bitmap
    pointers, change codepoint to new_cp."""
    src = find_record_by_cp(recs, src_cp)
    if src is None:
        raise ValueError(f'source codepoint U+{src_cp:04X} not in font')
    dst = recs[dst_idx]
    print(f'  slot [{dst_idx}] U+{dst["codepoint"]:04X} → U+{new_cp:04X} '
          f'(using bitmap of U+{src_cp:04X})')
    dst['codepoint']      = new_cp
    dst['advance']        = src['advance']
    dst['offset_x']       = src['offset_x']
    dst['offset_y']       = src['offset_y']
    dst['bw']             = src['bw']
    dst['bh']             = src['bh']
    dst['bitmap_offset']  = src['bitmap_offset']
    dst['bitmap_size']    = src['bitmap_size']
    # keep baseline

def main_identity_test():
    """Verify parse → serialize round-trip is byte-identical."""
    import zlib as _z
    comp = get_rus_font_compressed()
    font = _z.decompress(comp)
    recs = parse_records(font)
    rebuilt = serialize_records(font, recs)
    same = (rebuilt == font)
    print(f'Identity round-trip: {"OK" if same else "FAIL"}')
    if not same:
        # show diffs
        for i, (a, b) in enumerate(zip(font, rebuilt)):
            if a != b:
                print(f'  diff @0x{i:x}: orig 0x{a:02x}  vs  rebuilt 0x{b:02x}')
                if i > 50: break
    return same

if __name__ == '__main__':
    main_identity_test()
