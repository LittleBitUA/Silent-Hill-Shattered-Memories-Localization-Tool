"""
Consolidate per-platform translation files into a single shared source.

Inputs (existing translations to harvest from):
    unpacked/Duplicate.txt
    unpacked/translate_sys.txt
    unpacked/translate_ui.txt
    unpacked/translate_wii.txt
    unpacked/translate_psp.txt

Inputs (key sets to figure out platform exclusives):
    unpacked/data/1315_2c238264.bin (PS2 sys), 1316_2c238276.bin (PS2 ui)
    wii_extract/DATA/files/data.arc (entries 1329, 1330)
    psp_orig_extract/PSP_GAME/USRDIR/DATA.ARC (entries 1316, 1317)

Outputs:
    unpacked/translate_shared.txt       — every unique hash, best UA text
    unpacked/translate_ps2_only.txt     — hashes exclusive to PS2 (37)
    unpacked/translate_wii_only.txt     — hashes exclusive to Wii (87)
    unpacked/translate_psp_only.txt     — hashes exclusive to PSP (28)

The shared.txt is the new single source of truth. Platform "_only" files
are placeholders for any platform-specific overrides (initially each row
is the same translation as shared.txt; if the user wants different text
on a specific platform, they edit there and it overrides).

Pack-time the build scripts merge:
    shared_dict.update(platform_only_dict)
    for hash in platform_keys_from_arc:
        pack(shared_dict.get(hash, english_fallback))
"""
import struct, zlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
UNPACKED = ROOT / 'unpacked'
OUT_DIR  = ROOT / 'TEXT_TRANSLATION'
OUT_DIR.mkdir(parents=True, exist_ok=True)

PS2_SYS_BIN = UNPACKED / 'data' / '1315_2c238264.bin'
PS2_UI_BIN  = UNPACKED / 'data' / '1316_2c238276.bin'
WII_ARC = ROOT / 'wii_extract' / 'DATA' / 'files' / 'data.arc'
PSP_ARC = ROOT / 'psp_orig_extract' / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC'

WII_SYS, WII_UI = 1329, 1330
PSP_SYS, PSP_UI = 1316, 1317

def has_cyrillic(s):
    return any(0x0400 <= ord(c) <= 0x04FF for c in s)

def read_arc_entry(arc_path, idx):
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
        else: out.append(chr(u))
    return ''.join(out)

def parse_strings_blob(blob):
    ver, cnt = struct.unpack_from('<II', blob, 0)
    base = 8 + cnt*8
    rows = []
    for i in range(cnt):
        h, off = struct.unpack_from('<II', blob, 8 + i*8)
        rows.append((h, decode_string(blob, base + off*2)))
    return rows

def keyset_from_blob(blob):
    ver, cnt = struct.unpack_from('<II', blob, 0)
    return {struct.unpack_from('<I', blob, 8 + i*8)[0] for i in range(cnt)}

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
    # Load all known translations
    sources = ['translate_psp.txt', 'translate_wii.txt',
               'translate_ui.txt', 'translate_sys.txt', 'Duplicate.txt']
    # Priority: Duplicate > sys > ui > wii > psp (reversed iteration order)
    ua = {}    # hash -> best translation
    conflicts = []
    for src in sources:
        p = UNPACKED / src
        if not p.exists(): continue
        blocks = parse_txt_blocks(p)
        n_cyr = 0
        for h, body in blocks.items():
            if not has_cyrillic(body):
                continue
            n_cyr += 1
            if h in ua and ua[h] != body:
                conflicts.append((h, ua[h], body, src))
            else:
                ua[h] = body
        print(f'  loaded {src}: {len(blocks)} blocks, {n_cyr} cyrillic, dict now {len(ua)}')
    if conflicts:
        print(f'WARN: {len(conflicts)} conflicting translations (later wins)')

    # English fallback from PSP sys (the most complete EN source we have).
    en = {}
    psp_sys_rows = parse_strings_blob(read_arc_entry(PSP_ARC, PSP_SYS))
    for h, t in psp_sys_rows: en[h] = t
    ps2_sys_rows = parse_strings_blob(PS2_SYS_BIN.read_bytes())
    for h, t in ps2_sys_rows:
        if h not in en: en[h] = t   # PS2-only ids
    wii_sys_rows = parse_strings_blob(read_arc_entry(WII_ARC, WII_SYS))
    for h, t in wii_sys_rows:
        if h not in en: en[h] = t   # Wii-only ids
    print(f'\nEnglish base dict: {len(en)} entries')

    # Compute key sets per platform
    ps2_keys = keyset_from_blob(PS2_SYS_BIN.read_bytes()) | keyset_from_blob(PS2_UI_BIN.read_bytes())
    wii_keys = keyset_from_blob(read_arc_entry(WII_ARC, WII_SYS)) | keyset_from_blob(read_arc_entry(WII_ARC, WII_UI))
    psp_keys = keyset_from_blob(read_arc_entry(PSP_ARC, PSP_SYS)) | keyset_from_blob(read_arc_entry(PSP_ARC, PSP_UI))

    all_keys = ps2_keys | wii_keys | psp_keys
    ps2_only = ps2_keys - wii_keys - psp_keys
    wii_only = wii_keys - ps2_keys - psp_keys
    psp_only = psp_keys - ps2_keys - wii_keys
    print(f'\nKey sets:')
    print(f'  PS2: {len(ps2_keys)}, Wii: {len(wii_keys)}, PSP: {len(psp_keys)}')
    print(f'  union: {len(all_keys)}, intersect: {len(ps2_keys & wii_keys & psp_keys)}')
    print(f'  PS2-only: {len(ps2_only)}, Wii-only: {len(wii_only)}, PSP-only: {len(psp_only)}')

    # Order for shared.txt: PSP sys order first (most complete), then PS2 extras, then Wii extras
    seen = set()
    order = []
    for h, _ in psp_sys_rows:
        if h not in seen:
            order.append(h); seen.add(h)
    for h, _ in ps2_sys_rows:
        if h not in seen:
            order.append(h); seen.add(h)
    for h, _ in wii_sys_rows:
        if h not in seen:
            order.append(h); seen.add(h)
    # Any remaining (shouldn't be many)
    for h in all_keys - seen:
        order.append(h)
        en.setdefault(h, '???')

    # Write shared.txt
    n_translated = 0
    with (OUT_DIR / 'translate_shared.txt').open('w', encoding='utf-8') as f:
        f.write('# SH:SM translate_shared (union of PS2 + Wii + PSP, 4853 hashes)\n')
        f.write("# Primary source-of-truth translation file. Edit text in place.\n")
        f.write("# Platform _only files override individual hashes per-platform.\n")
        f.write('\n')
        for h in order:
            text = ua.get(h, en.get(h, ''))
            if h in ua:
                n_translated += 1
            f.write(f'# - {h:08x}\n')
            f.write(text + '\n\n')
    print(f'\nwrote translate_shared.txt: {len(order)} blocks, {n_translated} translated '
          f'({100*n_translated/len(order):.1f}%)')

    # Write platform _only files
    def write_only(name, keys):
        with (OUT_DIR / name).open('w', encoding='utf-8') as f:
            f.write(f'# SH:SM {name} (platform-exclusive override file)\n')
            f.write("# Hashes that ONLY exist on this platform. Edit text here to override\n")
            f.write("# shared.txt — useful for platform-specific wording or where a hash\n")
            f.write("# doesn't appear at all in other platforms.\n")
            f.write('\n')
            n_t = 0
            for h in order:
                if h not in keys: continue
                text = ua.get(h, en.get(h, ''))
                if h in ua: n_t += 1
                f.write(f'# - {h:08x}\n')
                f.write(text + '\n\n')
            return n_t
    n = write_only('translate_ps2_only.txt', ps2_only)
    print(f'wrote translate_ps2_only.txt: {len(ps2_only)} blocks, {n} translated')
    n = write_only('translate_wii_only.txt', wii_only)
    print(f'wrote translate_wii_only.txt: {len(wii_only)} blocks, {n} translated')
    n = write_only('translate_psp_only.txt', psp_only)
    print(f'wrote translate_psp_only.txt: {len(psp_only)} blocks, {n} translated')

if __name__ == '__main__':
    main()
