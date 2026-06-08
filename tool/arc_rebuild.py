"""
Rebuild a SH:SM .arc archive, allowing in-place replacement of selected entries.

Strategy:
  - Load original .arc (we need it for the entry table: hash, sizes, ordering).
  - For each entry, allow an override file (by hash hex name, e.g. "2c238276.bin").
  - Re-compress each entry with zlib (or keep stored raw if original was raw — see manifest).
  - Lay out everything at 0x800 sector alignment.
  - Optionally pad the final archive to a given target size (so ISO LBAs stay valid).

Usage:
    python arc_rebuild.py <orig.arc> <override_dir> <out.arc> [--target-size N]

    override_dir contains files named "<hash:08x>.bin" — these are DECOMPRESSED
    payloads; the script will zlib them if the original entry was compressed.
"""
import sys, struct, pathlib, zlib, argparse

SECTOR = 0x800

# Prefer zopfli (significantly tighter than zlib level 9) when available —
# critical for fitting longer UA translations into the original sector-
# aligned slots inside data.arc.
try:
    import zopfli.zlib as _zopfli
    def _compress(data: bytes) -> bytes:
        return _zopfli.compress(data, numiterations=500)
    _COMPRESSOR = 'zopfli'
except ImportError:
    def _compress(data: bytes) -> bytes:
        return zlib.compress(data, level=9)
    _COMPRESSOR = 'zlib-9'

def align(n, a=SECTOR):
    return (n + a - 1) & ~(a - 1)

def read_arc_header(data):
    sig, cnt, hsize, _ = struct.unpack_from('<IIII', data, 0)
    if sig != 0x0000FA10:
        raise ValueError(f'bad signature 0x{sig:08x}')
    entries = []
    for i in range(cnt):
        h, off, csz, usz = struct.unpack_from('<IIII', data, 16 + i*16)
        entries.append({'hash':h, 'offset':off, 'csz':csz, 'usz':usz})
    return cnt, hsize, entries

def maybe_decompress(blob):
    if len(blob) >= 2 and blob[0] == 0x78 and blob[1] in (0xDA, 0x9C, 0x01, 0x5E):
        try:
            return zlib.decompress(blob), True
        except zlib.error:
            return blob, False
    return blob, False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('orig')
    ap.add_argument('overrides_dir')
    ap.add_argument('out')
    ap.add_argument('--target-size', type=int, default=0,
                    help='pad output to this exact byte size (default: keep natural size)')
    args = ap.parse_args()

    orig = pathlib.Path(args.orig).read_bytes()
    overrides = pathlib.Path(args.overrides_dir)
    cnt, hsize, entries = read_arc_header(orig)
    print(f'Loaded {args.orig}: {cnt} entries, header/data start at 0x{hsize:x}, compressor={_COMPRESSOR}')

    # Preserve magic markers (8 bytes immediately after the entry table,
    # if there's space before hsize — see Archive.cpp m_magicMarker1/2)
    table_end = 16 + cnt * 16
    markers = b''
    if entries and entries[0]['offset'] >= table_end + 16:
        markers = orig[table_end:table_end + 8]

    # Phase 1: decide payload bytes for each entry
    new_payloads = []      # list of (compressed_blob, decompressed_size)
    n_replaced = 0
    for e in entries:
        raw = orig[e['offset']:e['offset']+e['csz']]
        orig_aligned = align(e['csz'])    # how many bytes this entry takes on disk after padding
        ov_path = overrides / f'{e["hash"]:08x}.bin'
        if ov_path.exists():
            decompressed = ov_path.read_bytes()
            n_replaced += 1
            was_packed = (e['usz'] != 0)
            if was_packed:
                comp = _compress(decompressed)
                if align(len(comp)) > orig_aligned:
                    raise ValueError(
                        f'override for {e["hash"]:08x} is {len(comp)} bytes compressed, '
                        f'needs {align(len(comp))} on-disk; original slot is only {orig_aligned}. '
                        f'cannot fit without shifting later entries.')
                new_payloads.append((comp, len(decompressed)))
            else:
                if align(len(decompressed)) > orig_aligned:
                    raise ValueError(
                        f'override for {e["hash"]:08x} is {len(decompressed)} bytes (raw), '
                        f'needs {align(len(decompressed))} on-disk; original slot is only {orig_aligned}.')
                new_payloads.append((decompressed, 0))
        else:
            new_payloads.append((raw, e['usz']))

    print(f'Replaced: {n_replaced} entries; kept: {cnt - n_replaced}')

    # Phase 2: IN-PLACE replacement — start from a copy of the original archive
    # and overwrite only the bytes of the modified entries (padded inside their
    # original sector-aligned slot). This guarantees that every other entry's
    # absolute offset stays identical, so anything in the engine that has a
    # hard-coded LBA continues to work.
    out = bytearray(orig)
    new_records = []
    for e, (blob, usz) in zip(entries, new_payloads):
        slot_size = align(e['csz'])
        if len(blob) > slot_size:
            raise ValueError(f'override for {e["hash"]:08x} exceeds slot ({len(blob)} > {slot_size})')
        # Zero-fill the slot, then write the new payload at its start
        out[e['offset']:e['offset'] + slot_size] = bytes(slot_size)
        out[e['offset']:e['offset'] + len(blob)] = blob
        new_records.append((e['hash'], e['offset'], len(blob), usz))

    # Update the entry table in place (offsets unchanged; csz/usz refresh for overrides)
    for i, (h, off, csz, usz) in enumerate(new_records):
        struct.pack_into('<IIII', out, 16 + i*16, h, off, csz, usz)
    # Magic markers area is preserved by the in-place copy; no need to restore.

    # Target-size pad
    if args.target_size and len(out) < args.target_size:
        out.extend(b'\x00' * (args.target_size - len(out)))
        print(f'Padded to target size {args.target_size:,}')
    elif args.target_size and len(out) > args.target_size:
        raise ValueError(f'Rebuilt arc is {len(out):,} bytes, exceeds target {args.target_size:,}')

    pathlib.Path(args.out).write_bytes(bytes(out))
    print(f'Wrote {args.out}: {len(out):,} bytes')

if __name__ == '__main__':
    main()
