"""
Silent Hill: Shattered Memories (PS2) .arc unpacker.

Format (derived from data.arc / igc.arc header analysis — HYPOTHESIS, verify!):

    HEADER (16 bytes):
        uint32  magic        = 0x0000FA10  (same in data.arc and igc.arc)
        uint32  num_entries
        uint32  data_offset   (e.g. 0x8000 for data.arc, 0x1800 for igc.arc)
        uint32  reserved      (0)

    ENTRY (16 bytes, num_entries of them, sector-aligned to data_offset):
        uint32  hash               (name hash; algorithm unknown — likely CRC32 or FNV)
        uint32  offset             (byte offset inside the archive)
        uint32  size_compressed    (bytes on disk; covers aligned-up to 0x800 in storage)
        uint32  size_uncompressed  (0 if file is stored raw; otherwise decompressed size)

Compression algorithm: UNKNOWN yet. Check first bytes per entry — LZSS / refpack / LZ4
are all candidates. data.arc has size_uncompressed > size_compressed for many entries,
igc.arc has size_uncompressed == 0 for all (raw streams).

Usage:
    python arc_unpack.py list  data.arc
    python arc_unpack.py dump  data.arc out/data/
    python arc_unpack.py probe data.arc        # print signatures of first N raw bytes
"""

import os, sys, struct, pathlib, collections, zlib, zlib as _zlib

MAGIC = 0x0000FA10
SECTOR = 0x800

def maybe_decompress(blob):
    """Return (data, was_compressed). zlib if header is 78 DA / 78 9C / 78 01."""
    if len(blob) >= 2 and blob[0] == 0x78 and blob[1] in (0xDA, 0x9C, 0x01, 0x5E):
        try:
            return _zlib.decompress(blob), True
        except _zlib.error:
            return blob, False
    return blob, False

def parse_header(buf):
    magic, n, data_off, _ = struct.unpack_from('<IIII', buf, 0)
    if magic != MAGIC:
        raise ValueError(f'Unexpected magic 0x{magic:08x} (expected 0x{MAGIC:08x})')
    entries = []
    for i in range(n):
        h, off, csz, usz = struct.unpack_from('<IIII', buf, 16 + i*16)
        entries.append((h, off, csz, usz))
    return n, data_off, entries

def open_arc(path):
    f = open(path, 'rb')
    head = f.read(16)
    magic, n, data_off, _ = struct.unpack('<IIII', head)
    if magic != MAGIC:
        raise ValueError(f'{path}: bad magic 0x{magic:08x}')
    tbl = f.read(n * 16)
    entries = [struct.unpack_from('<IIII', tbl, i*16) for i in range(n)]
    return f, n, data_off, entries

def cmd_list(arc):
    f, n, data_off, entries = open_arc(arc)
    print(f'# {arc}: {n} entries, data starts at 0x{data_off:08x}')
    print(f'# {"idx":>5}  {"hash":>10}  {"offset":>10}  {"comp":>10}  {"uncomp":>10}  ratio')
    for i, (h, off, csz, usz) in enumerate(entries):
        ratio = (csz / usz) if usz else 1.0
        print(f'  {i:>5}  {h:08x}    {off:08x}    {csz:08x}    {usz:08x}    {ratio:.2f}')
    f.close()

def sig_of(data):
    """Return a short, human-readable signature for the first few bytes."""
    if len(data) < 4: return 'short'
    h4 = data[:4]
    # Known signatures we'll meet.
    if h4 == b'\x10\xFA\x00\x00':              return 'arc-sub (PAK?)'
    if h4 == b'\x00\x00\x01\xBA':              return 'MPEG-PS (movie)'
    if h4[:3] == b'TM2':                        return 'TIM2-text?'
    if h4 == b'TIM2':                           return 'TIM2'
    if h4 == b'\x10\x00\x00\x00' and len(data) >= 12:
        # RenderWare 3 stream: type=0x10 (Clump) for DFF, or 0x16 (TXD), 0x40000 KFONT plugin id…
        return 'RW-stream?'
    rw_first_dword = struct.unpack('<I', h4)[0]
    rw_types = {
        0x10: 'RW Clump (DFF)',
        0x14: 'RW Atomic',
        0x16: 'RW TexDictionary (TXD)',
        0x1B: 'RW Anim Animation',
        0x2D: 'RW Light',
        0x39: 'RW MorphPLG',
        0x510: 'RW BSP (custom)',
    }
    if rw_first_dword in rw_types:
        return rw_types[rw_first_dword]
    if h4 == b'PK\x03\x04':                     return 'ZIP'
    if data[:2] == b'\x1f\x8b':                 return 'gzip'
    if h4[0] in (0x10, 0x11) and h4[1:4] == b'\x00\x00\x00':
        return 'LZSS-like?'
    if h4 == b'<?xm':                           return 'XML (uncompressed)'
    # refpack signature: 10 FB
    if data[0] == 0x10 and data[1] in (0xFB, 0xFC): return 'refpack?'
    return f'?{h4.hex()}'

def cmd_probe(arc, n_show=64):
    f, n, data_off, entries = open_arc(arc)
    print(f'# {arc}: first {n_show}/{n} entries (after zlib decompression where applicable)')
    print(f'# {"idx":>5}  {"hash":>10}  {"csz":>9}  {"usz":>9}  zlib?  first8(decomp)  signature')
    for i, (h, off, csz, usz) in enumerate(entries[:n_show]):
        f.seek(off)
        blob = f.read(min(csz, 65536))
        data, was_z = maybe_decompress(blob)
        head = data[:8] if len(data) >= 8 else data
        print(f'  {i:>5}  {h:08x}    {csz:08x}  {usz:08x}    {"Y" if was_z else "n"}    {head.hex():16}  {sig_of(data)}')
    # Histogram on DECOMPRESSED content (read whole files)
    sigs = collections.Counter()
    for h, off, csz, usz in entries:
        f.seek(off)
        blob = f.read(csz)
        data, _ = maybe_decompress(blob)
        sigs[sig_of(data)] += 1
    print(f'\n# decompressed signature histogram ({n} entries):')
    for s, c in sigs.most_common():
        print(f'  {c:>6}  {s}')
    f.close()

EXT_BY_SIG = {
    'MPEG-PS (movie)': 'pss',
    'TIM2':            'tm2',
    'TIM2-text?':      'tm2',
    'RW Clump (DFF)':  'dff',
    'RW TexDictionary (TXD)': 'txd',
    'RW Atomic':       'rwa',
    'RW Anim Animation': 'anm',
    'arc-sub (PAK?)':  'arc',
    'XML (uncompressed)': 'xml',
}

def cmd_dump(arc, out_dir, decompress=True):
    f, n, data_off, entries = open_arc(arc)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    width = max(4, len(str(n-1)))
    manifest = []
    for i, (h, off, csz, usz) in enumerate(entries):
        f.seek(off)
        blob = f.read(csz)
        data, was_z = (maybe_decompress(blob) if decompress else (blob, False))
        sig = sig_of(data[:16])
        ext = EXT_BY_SIG.get(sig, 'bin')
        name = f'{i:0{width}d}_{h:08x}.{ext}'
        (out / name).write_bytes(data)
        manifest.append((i, h, off, csz, usz, was_z, sig, name))
    with open(out / '_manifest.tsv', 'w', encoding='utf-8') as mf:
        mf.write('idx\thash\toffset\tcsz\tusz\tzlib\tsig\tname\n')
        for row in manifest:
            mf.write('{}\t{:08x}\t{:08x}\t{:08x}\t{:08x}\t{}\t{}\t{}\n'.format(*row))
    print(f'wrote {n} files to {out} (decompress={decompress})')
    f.close()

if __name__ == '__main__':
    cmd = sys.argv[1]
    arc = sys.argv[2]
    if cmd == 'list':   cmd_list(arc)
    elif cmd == 'probe': cmd_probe(arc, int(sys.argv[3]) if len(sys.argv) > 3 else 64)
    elif cmd == 'dump':  cmd_dump(arc, sys.argv[3])
    else: print(__doc__); sys.exit(1)
