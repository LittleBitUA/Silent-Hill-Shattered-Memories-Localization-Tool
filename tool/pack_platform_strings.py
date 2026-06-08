"""
Assemble a platform strings .bin from the shared translation source.

Reads:
    TEXT_TRANSLATION/translate_shared.txt
    TEXT_TRANSLATION/translate_<platform>_only.txt   (optional overrides)

For each hash that appears in the platform's actual key list (taken from
the source .arc entry), uses:
    1) text from translate_<platform>_only.txt if present (override)
    2) else text from translate_shared.txt
    3) else the English source from the platform's .arc entry

Usage:
    python pack_platform_strings.py wii  out.bin
    python pack_platform_strings.py psp  out.bin
    python pack_platform_strings.py ps2_sys out.bin
    python pack_platform_strings.py ps2_ui  out.bin

The pack itself is delegated to strings_pack.pack(), which applies
CYR2LAT_SUBST and SH_EXTRA_SUBST as usual.
"""
import os, sys, struct, zlib, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import strings_pack

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_TR = ROOT / 'TEXT_TRANSLATION'

PLATFORM_SOURCE = {
    'wii':     (ROOT / 'wii_extract' / 'DATA' / 'files' / 'data.arc', 1329),
    'psp':     (ROOT / 'psp_orig_extract' / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC', 1316),
    'ps2_sys': (None, None),   # PS2 reads from unpacked/data/1315_2c238264.bin
    'ps2_ui':  (None, None),   # PS2 reads from unpacked/data/1316_2c238276.bin
}
PS2_SOURCES = {
    'ps2_sys': ROOT / 'unpacked' / 'data' / '1315_2c238264.bin',
    'ps2_ui':  ROOT / 'unpacked' / 'data' / '1316_2c238276.bin',
}
ONLY_FILE = {
    'wii': 'translate_wii_only.txt',
    'psp': 'translate_psp_only.txt',
    'ps2_sys': 'translate_ps2_only.txt',
    'ps2_ui':  'translate_ps2_only.txt',
}

def read_entry(arc_path, idx):
    with open(arc_path, 'rb') as f:
        f.seek(16 + idx*16)
        h, off, csz, usz = struct.unpack('<IIII', f.read(16))
        f.seek(off); blob = f.read(csz)
    if blob[:1] == b'\x78' and blob[1] in (0x9c, 0xda, 0x01, 0x5e):
        return zlib.decompress(blob)
    return blob

def decode_string(data, pos):
    out = []
    while pos < len(data) - 1:
        u = data[pos] | (data[pos+1] << 8); pos += 2
        if u == 0: break
        if u == 1:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<c={n}>')
        elif u == 2: out.append('<p>')
        elif u == 3:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<b={n}>')
        elif u == 4:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<w={n}>')
        elif u == 0x0A: out.append('\\n')
        elif u == 0x09: out.append('\\t')
        elif u == 0x0D: out.append('\\r')
        else: out.append(chr(u))
    return ''.join(out)

def get_platform_rows(platform):
    if platform.startswith('ps2_'):
        blob = PS2_SOURCES[platform].read_bytes()
    else:
        arc, idx = PLATFORM_SOURCE[platform]
        blob = read_entry(arc, idx)
    ver, cnt = struct.unpack_from('<II', blob, 0)
    base = 8 + cnt*8
    rows = []
    for i in range(cnt):
        h, off = struct.unpack_from('<II', blob, 8 + i*8)
        rows.append((h, decode_string(blob, base + off*2)))
    return rows

def parse_txt(path):
    if not path.exists(): return {}
    text = path.read_text(encoding='utf-8')
    out = {}
    cur_id = None; cur_body = []
    def flush():
        if cur_id is not None:
            out[int(cur_id, 16)] = '\n'.join(cur_body).rstrip('\n')
    for line in text.splitlines():
        if line.startswith('# - '):
            flush()
            cur_id = line[4:].strip().split(maxsplit=1)[0]; cur_body = []
        elif line.startswith('#'):
            continue
        elif line == '':
            if cur_id is not None and cur_body:
                flush(); cur_id = None; cur_body = []
        else:
            if cur_id is not None: cur_body.append(line)
    flush()
    return out

def assemble_rows(platform):
    shared = parse_txt(TEXT_TR / 'translate_shared.txt')
    only   = parse_txt(TEXT_TR / ONLY_FILE[platform])
    en_rows = get_platform_rows(platform)
    merged = dict(shared); merged.update(only)
    rows = []
    matched = 0
    for h, en in en_rows:
        text = merged.get(h, en)
        if h in merged: matched += 1
        rows.append((h, text))
    print(f'[pack_platform_strings] {platform}: {matched}/{len(rows)} from shared/only '
          f'({100*matched/len(rows):.1f}%)', file=sys.stderr)
    return rows

def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    platform = sys.argv[1]
    out_path = sys.argv[2]
    if platform not in PLATFORM_SOURCE:
        sys.exit(f'unknown platform {platform}')
    rows = assemble_rows(platform)
    blob = strings_pack.pack(rows, warmup=False)
    pathlib.Path(out_path).write_bytes(blob)
    print(f'wrote {out_path}  ({len(blob):,} bytes, {len(rows):,} strings)')

if __name__ == '__main__':
    main()
