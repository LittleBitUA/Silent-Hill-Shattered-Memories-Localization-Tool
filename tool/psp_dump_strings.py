"""
Extract PSP DATA.ARC entries 1316 (translate_sys) / 1317 (translate_ui)
to unpacked/translate_psp.txt. PSP sys ⊃ ui (sys 4729 keys is a superset
of ui's 4608); we build the txt from sys's full key set.

Pre-populates each block from existing PS2/Wii translations (any source
with Cyrillic body wins, Duplicate.txt takes precedence).

Output: unpacked/translate_psp.txt
"""
import struct, zlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PSP_ARC = ROOT / 'psp_orig_extract' / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC'
UNPACKED = ROOT / 'unpacked'
SYS_IDX, UI_IDX = 1316, 1317

def has_cyrillic(s):
    return any(0x0400 <= ord(c) <= 0x04FF for c in s)

def read_entry(arc_path, idx):
    with open(arc_path, 'rb') as f:
        f.seek(16 + idx*16)
        h, off, csz, usz = struct.unpack('<IIII', f.read(16))
        f.seek(off); blob = f.read(csz)
    if blob[:1] == b'\x78' and blob[1] in (0x9c, 0xda, 0x01, 0x5e):
        return h, zlib.decompress(blob)
    return h, blob

def decode_string(data, pos):
    out = []
    while pos < len(data) - 1:
        u = data[pos] | (data[pos+1] << 8); pos += 2
        if u == 0: break
        if u == 1:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<c={n}>')
        elif u == 2:
            out.append('<p>')
        elif u == 3:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<b={n}>')
        elif u == 4:
            n = data[pos] | (data[pos+1] << 8); pos += 2
            out.append(f'<w={n}>')
        elif u == 0x0A: out.append('\\n')
        elif u == 0x09: out.append('\\t')
        elif u == 0x0D: out.append('\\r')
        else:
            out.append(chr(u))
    return ''.join(out)

def parse_strings_blob(blob):
    ver, cnt = struct.unpack_from('<II', blob, 0)
    if ver != 2:
        print(f'WARN: version={ver}')
    base = 8 + cnt*8
    rows = []
    for i in range(cnt):
        h, off = struct.unpack_from('<II', blob, 8 + i*8)
        rows.append((h, decode_string(blob, base + off*2)))
    return rows

def parse_txt_blocks(path):
    text = path.read_text(encoding='utf-8')
    out = {}
    cur_id = None
    cur_body = []
    def flush():
        if cur_id is not None:
            out[int(cur_id, 16)] = '\n'.join(cur_body).rstrip('\n')
    for line in text.splitlines():
        if line.startswith('# - '):
            flush()
            cur_id = line[4:].strip().split(maxsplit=1)[0]
            cur_body = []
        elif line.startswith('#'):
            continue
        elif line == '':
            if cur_id is not None and cur_body:
                flush()
                cur_id = None
                cur_body = []
        else:
            if cur_id is not None:
                cur_body.append(line)
    flush()
    return out

def main():
    h_s, sys_blob = read_entry(PSP_ARC, SYS_IDX)
    h_u, ui_blob  = read_entry(PSP_ARC, UI_IDX)
    print(f'PSP sys arc[{SYS_IDX}] hash=0x{h_s:08X} dlen={len(sys_blob)}')
    print(f'PSP ui  arc[{UI_IDX}] hash=0x{h_u:08X} dlen={len(ui_blob)}')
    rows_sys = parse_strings_blob(sys_blob)
    rows_ui = parse_strings_blob(ui_blob)
    set_sys = {h for h,_ in rows_sys}
    set_ui = {h for h,_ in rows_ui}
    print(f'  sys: {len(rows_sys)}, ui: {len(rows_ui)}, sys&gt;=ui? {set_ui <= set_sys}')

    # Aggregate UA from PS2/Wii sources
    ua = {}
    for src in ('translate_wii.txt', 'translate_sys.txt', 'translate_ui.txt', 'Duplicate.txt'):
        p = UNPACKED / src
        if not p.exists():
            continue
        blocks = parse_txt_blocks(p)
        cyr = {h: b for h, b in blocks.items() if has_cyrillic(b)}
        for h, b in cyr.items():
            ua[h] = b
        print(f'  loaded {src}: {len(blocks)} blocks, {len(cyr)} cyrillic')
    print(f'  total UA dict: {len(ua)} translated hashes')

    out_path = UNPACKED / 'translate_psp.txt'
    matched = 0
    with out_path.open('w', encoding='utf-8') as f:
        f.write('# SH:SM translate_psp (PSP NTSC-U sys+ui, DATA.ARC idx 1316/1317)\n')
        f.write("# PSP sys (4729) is a superset of ui (4608). We use sys order/keys as the single TXT.\n")
        f.write("# Edit text in place. '# - <id>' headers must stay untouched.\n")
        f.write('\n')
        for h, en in rows_sys:
            text = ua.get(h, en)
            if h in ua:
                matched += 1
            f.write(f'# - {h:08x}\n')
            f.write(text + '\n')
            f.write('\n')
    print(f'wrote {out_path}: {len(rows_sys)} blocks')
    print(f'  pre-translated: {matched}/{len(rows_sys)} ({100*matched/len(rows_sys):.1f}%)')

if __name__ == '__main__':
    main()
