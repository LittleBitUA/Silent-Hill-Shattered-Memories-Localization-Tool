"""
In-place patch translate_sys/ui entries in Wii data.arc.

Wii arc entries are sector-aligned (0x800). Each entry has a "slot" that
extends from its offset to the next entry's offset. As long as our new
compressed payload fits in the slot, we can patch without rebuilding the
1.5-GB archive.

NOTE: Font_EUR in data.arc (idx 408) is NOT patched — the Wii engine
reads its font from the embedded zlib stream in main.dol instead. See
tool/wii_patch_maindol.py for the font patcher.

Patches (modifying wii_extract/DATA/files/data.arc IN PLACE):
  idx 1329 (hash 2C238264) → translate_sys   ← translate_sys_wii.bin
  idx 1330 (hash 2C238276) → translate_ui    ← translate_ui_wii.bin

To revert: re-extract data.arc from the original RVZ.
"""
import struct, zlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARC   = ROOT / 'wii_extract' / 'DATA' / 'files' / 'data.arc'
BUILD = ROOT / 'UA_wii' / '_build'

SYS_BIN   = BUILD / 'translate_sys_wii.bin'
UI_BIN    = BUILD / 'translate_ui_wii.bin'

try:
    import zopfli.zlib as _z
    def compress(data): return _z.compress(data, numiterations=15)
    _NAME = 'zopfli'
except ImportError:
    def compress(data): return zlib.compress(data, level=9)
    _NAME = 'zlib-9'

SECTOR = 0x800

def patch_entry(arc_f, entries, idx, new_raw, label):
    """Compress new_raw, write into entry idx's slot. Returns (csz, usz, slot)."""
    h, off, old_csz, old_usz = entries[idx]
    nxt_off = entries[idx+1][1]
    slot = nxt_off - off
    c = compress(new_raw)
    if len(c) > slot:
        raise SystemExit(f'{label}: compressed {len(c)} > slot {slot} (idx {idx}, '
                         f'old_csz={old_csz}). Need to rebuild arc, not in-place.')
    arc_f.seek(off)
    arc_f.write(c)
    # zero-fill the rest of the slot so leftover bytes don't confuse engine
    pad = slot - len(c)
    arc_f.write(b'\x00' * pad)
    # Update header table entry: csz and usz
    new_csz = len(c)
    new_usz = len(new_raw)
    entries[idx] = (h, off, new_csz, new_usz)
    arc_f.seek(16 + idx*16)
    arc_f.write(struct.pack('<IIII', h, off, new_csz, new_usz))
    print(f'  patched [{idx}] {label}: raw={new_usz}, comp={new_csz}/{slot} '
          f'({100*new_csz/slot:.1f}% of slot, was {old_csz})')
    return new_csz, new_usz, slot

def main():
    if not ARC.exists():
        raise SystemExit(f'missing {ARC}. Re-extract from RVZ first.')
    print(f'patching in place: {ARC} ({ARC.stat().st_size:,} bytes)')

    with ARC.open('r+b') as f:
        head = f.read(16)
        magic, n, data_off, _ = struct.unpack('<IIII', head)
        if magic != 0x0000FA10:
            raise SystemExit(f'bad magic 0x{magic:08X}')
        tbl = f.read(n*16)
        entries = [struct.unpack_from('<IIII', tbl, i*16) for i in range(n)]
        print(f'arc has {n} entries, compressor={_NAME}')

        if SYS_BIN.exists():
            patch_entry(f, entries, 1329, SYS_BIN.read_bytes(), 'translate_sys')
        else:
            print(f'  skip translate_sys: {SYS_BIN} missing')
        if UI_BIN.exists():
            patch_entry(f, entries, 1330, UI_BIN.read_bytes(), 'translate_ui')
        else:
            print(f'  skip translate_ui: {UI_BIN} missing')

    print(f'done. {ARC.stat().st_size:,} bytes (unchanged — only inside-slot replacements)')

if __name__ == '__main__':
    main()
