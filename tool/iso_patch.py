"""
Overwrite data.arc (and optionally igc.arc) inside a PS2 ISO in place,
keeping LBA layout intact.

Strategy:
  - Locate target arc by scanning for 0x0000FA10 magic at sector boundaries
    (same heuristic as iso_extract_arc.py).
  - The new arc MUST be the SAME byte length as the original — otherwise
    we would shift LBAs and break the ISO9660 layout + ELF references.
  - Write at the located offset.

Operates on a copy by default; if you pass --in-place, modifies the file
directly.

Usage:
    python iso_patch.py <iso> <new_data.arc> [--out <patched.iso>] [--in-place]
"""
import sys, mmap, struct, shutil, pathlib, argparse

MAGIC = b'\x10\xFA\x00\x00'

def find_arc(mm, target_count):
    pos = 0
    while True:
        p = mm.find(MAGIC, pos)
        if p < 0: return None
        if p % 0x800 == 0 and p + 16 <= len(mm):
            cnt, hsz, _ = struct.unpack_from('<III', mm, p+4)
            if hsz in (0x800, 0x1800, 0x8000) and cnt == target_count:
                return p
        pos = p + 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('new_arc')
    ap.add_argument('--out', help='output ISO path (default: <iso>.patched.iso)')
    ap.add_argument('--in-place', action='store_true', help='modify ISO directly (no copy)')
    args = ap.parse_args()

    new_blob = pathlib.Path(args.new_arc).read_bytes()
    new_cnt = struct.unpack_from('<I', new_blob, 4)[0]
    print(f'new arc: {len(new_blob):,} bytes, {new_cnt} entries')

    target = args.iso if args.in_place else (args.out or args.iso + '.patched.iso')
    if not args.in_place:
        print(f'Copying {args.iso} -> {target} ...')
        shutil.copy2(args.iso, target)

    with open(target, 'r+b') as f:
        mm = mmap.mmap(f.fileno(), 0)
        off = find_arc(mm, new_cnt)
        if off is None:
            mm.close()
            print(f'ERROR: could not locate arc with {new_cnt} entries in {target}')
            sys.exit(1)
        print(f'Found target arc at 0x{off:010x} in {target}')

        # Figure out original arc size (so we can refuse if new differs)
        # by scanning the entry table and finding max offset+csz.
        cnt, hsz = struct.unpack_from('<II', mm, off+4)
        max_end = hsz
        for i in range(cnt):
            _, eoff, csz, _ = struct.unpack_from('<IIII', mm, off + 16 + i*16)
            end = ((eoff + csz) + 0x7FF) & ~0x7FF
            if end > max_end:
                max_end = end
        orig_size = max_end
        print(f'Original arc total size (sector-aligned): {orig_size:,}')

        if len(new_blob) != orig_size:
            mm.close()
            print(f'ERROR: new arc is {len(new_blob):,} bytes, original was {orig_size:,}.')
            print('       In-place patching requires identical size.')
            print('       Pass --target-size to arc_rebuild.py to pad.')
            sys.exit(2)

        mm[off:off+len(new_blob)] = new_blob
        mm.flush()
        mm.close()
    # Refresh mtime so the patched ISO doesn't display the original's timestamp
    import os, time
    os.utime(target, (time.time(), time.time()))
    print(f'Patched: {target}')

if __name__ == '__main__':
    main()
