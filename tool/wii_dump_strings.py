"""
Extract Wii data.arc entries 1329 (translate_sys) / 1330 (translate_ui)
to a single unpacked/translate_wii.txt file. Both entries have IDENTICAL
key sets on Wii (verified: 4660 keys each, full overlap), so one file is
the source of truth — no Duplicate.txt needed.

Pre-populates each block with the existing PS2 translation when the hash
matches anything in:
    unpacked/translate_sys.txt
    unpacked/translate_ui.txt
    unpacked/Duplicate.txt
(Duplicate wins last; only Cyrillic bodies are kept.)

The remaining ~100-200 Wii-specific hashes stay as English for the user
to translate manually.
"""
import struct, zlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WII_ARC = ROOT / 'wii_extract' / 'DATA' / 'files' / 'data.arc'
UNPACKED = ROOT / 'unpacked'

SYS_IDX = 1329
UI_IDX  = 1330

def has_cyrillic(s):
    return any(0x0400 <= ord(c) <= 0x04FF for c in s)

def read_arc_entry(arc_path, idx):
    with open(arc_path, 'rb') as f:
        f.seek(16 + idx*16)
        h, off, csz, usz = struct.unpack('<IIII', f.read(16))
        f.seek(off)
        blob = f.read(csz)
    if blob[:1] == b'\x78' and blob[1] in (0x9c, 0xda, 0x01, 0x5e):
        return h, zlib.decompress(blob)
    return h, blob

def decode_string(data, pos):
    out = []
    while pos < len(data) - 1:
        u = data[pos] | (data[pos+1] << 8); pos += 2
        if u == 0:
            break
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
    """Return ordered list [(hash, text), ...]."""
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
    wh_sys, sys_blob = read_arc_entry(WII_ARC, SYS_IDX)
    wh_ui,  ui_blob  = read_arc_entry(WII_ARC, UI_IDX)
    print(f'Wii sys arc[{SYS_IDX}] hash=0x{wh_sys:08X} dlen={len(sys_blob)}')
    print(f'Wii ui  arc[{UI_IDX}] hash=0x{wh_ui:08X} dlen={len(ui_blob)}')
    rows_sys = parse_strings_blob(sys_blob)
    rows_ui  = parse_strings_blob(ui_blob)
    set_sys = {h for h,_ in rows_sys}
    set_ui  = {h for h,_ in rows_ui}
    print(f'  sys: {len(rows_sys)} rows, ui: {len(rows_ui)} rows')
    print(f'  identical key sets? {set_sys == set_ui}')

    ua = {}
    for src in ('translate_sys.txt', 'translate_ui.txt', 'Duplicate.txt'):
        p = UNPACKED / src
        if not p.exists():
            print(f'skip {src}: not found'); continue
        blocks = parse_txt_blocks(p)
        cyr = {h: b for h, b in blocks.items() if has_cyrillic(b)}
        for h, b in cyr.items():
            ua[h] = b
        print(f'  loaded {src}: {len(blocks)} blocks, {len(cyr)} cyrillic')
    print(f'  total UA dict: {len(ua)} translated hashes')

    out_path = UNPACKED / 'translate_wii.txt'
    matched_sys = 0
    matched_ui  = 0
    with out_path.open('w', encoding='utf-8') as f:
        f.write('# SH:SM translate_wii (Wii NTSC-U sys+ui, data.arc idx 1329/1330)\n')
        f.write("# Sys and UI have identical key sets on Wii (4660 each, full overlap).\n")
        f.write("# Edit text in place (replace English with Ukrainian). Blocks are\n")
        f.write("# separated by blank lines. Do not change the '# - <id>' lines.\n")
        f.write('\n')
        # Use the sys order (since sys==ui keys, order matters for either).
        # Some hashes in ui order may differ — handle that later if needed.
        for h, en in rows_sys:
            text = ua.get(h, en)
            if h in ua:
                matched_sys += 1
            f.write(f'# - {h:08x}\n')
            f.write(text + '\n')
            f.write('\n')
    for h, _ in rows_ui:
        if h in ua:
            matched_ui += 1
    print(f'wrote {out_path}: {len(rows_sys)} blocks')
    print(f'  pre-translated from PS2: sys {matched_sys}/{len(rows_sys)} ({100*matched_sys/len(rows_sys):.1f}%), '
          f'ui {matched_ui}/{len(rows_ui)} ({100*matched_ui/len(rows_ui):.1f}%)')

if __name__ == '__main__':
    main()
