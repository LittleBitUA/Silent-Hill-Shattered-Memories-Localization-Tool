"""
In-place patch translate_sys entry in PSP DATA.ARC.

Same approach as wii_arc_patch.py: sector-aligned slot replacement, no
full rebuild. PSP entries are sector-aligned to 0x800.

Patches (modify psp_extract_work/PSP_GAME/USRDIR/DATA.ARC IN PLACE):
  idx 1316 (hash 2C238264) → translate_sys   ← translate_sys_psp.bin

Note: PSP sys (1316) is a superset of ui (1317) — 4729 vs 4608 keys.
Metallist's RUS patch only modifies sys, never ui — engine reads from
sys for all strings, ui table is unused. We follow the same convention.

Font_EUR at idx 384 is NOT touched — engine reads its font from
EBOOT.BIN instead. See tool/psp_patch_eboot.py.
"""
import struct, zlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARC   = ROOT / 'psp_extract_work' / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC'
BUILD = ROOT / 'UA_psp' / '_build'

SYS_BIN = BUILD / 'translate_sys_psp.bin'

try:
    import zopfli.zlib as _z
    def compress(d): return _z.compress(d, numiterations=15)
    _NAME = 'zopfli'
except ImportError:
    def compress(d): return zlib.compress(d, level=9)
    _NAME = 'zlib-9'

def patch_entry(arc_f, entries, idx, new_raw, label):
    h, off, old_csz, old_usz = entries[idx]
    nxt_off = entries[idx+1][1]
    slot = nxt_off - off
    c = compress(new_raw)
    if len(c) > slot:
        raise SystemExit(f'{label}: compressed {len(c)} > slot {slot}')
    arc_f.seek(off)
    arc_f.write(c)
    pad = slot - len(c)
    arc_f.write(b'\x00' * pad)
    new_csz = len(c)
    new_usz = len(new_raw)
    entries[idx] = (h, off, new_csz, new_usz)
    arc_f.seek(16 + idx*16)
    arc_f.write(struct.pack('<IIII', h, off, new_csz, new_usz))
    print(f'  patched [{idx}] {label}: raw={new_usz}, comp={new_csz}/{slot} '
          f'({100*new_csz/slot:.1f}% of slot, was {old_csz})')

def main():
    if not ARC.exists():
        raise SystemExit(f'missing {ARC}')
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
            patch_entry(f, entries, 1316, SYS_BIN.read_bytes(), 'translate_sys')
        else:
            print(f'  skip translate_sys: {SYS_BIN} missing')

    print(f'done. {ARC.stat().st_size:,} bytes (unchanged)')

if __name__ == '__main__':
    main()
