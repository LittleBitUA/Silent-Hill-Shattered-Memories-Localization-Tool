"""
Generate the TEXT_TRANSLATION/ workspace from the user's own legal disc
dumps. Writes one block per unique hash with the English original as the
body — ready for translators to replace with their target language.

Requires (one or more):
    unpacked/data/1315_2c238264.bin   (PS2 sys-strings)
    unpacked/data/1316_2c238276.bin   (PS2 ui-strings)
    wii_extract/DATA/files/data.arc   (Wii data.arc, entry idx 1329)
    psp_orig_extract/PSP_GAME/USRDIR/DATA.ARC  (PSP DATA.ARC, entry idx 1316)

Whichever extracts exist contribute their key set; missing ones are
skipped. The union of every available platform's hashes becomes
translate_shared.txt; per-platform exclusive hashes go into the
matching _only.txt files.

Run once, then translate inside TEXT_TRANSLATION/.
"""
import struct, zlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TR = ROOT / 'TEXT_TRANSLATION'
TR.mkdir(exist_ok=True)

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

def read_arc_entry(arc_path, idx):
    with open(arc_path, 'rb') as f:
        f.seek(16 + idx * 16)
        h, off, csz, usz = struct.unpack('<IIII', f.read(16))
        f.seek(off)
        blob = f.read(csz)
    if blob[:1] == b'\x78' and blob[1] in (0x9c, 0xda, 0x01, 0x5e):
        return zlib.decompress(blob)
    return blob

def parse_string_table(blob):
    ver, cnt = struct.unpack_from('<II', blob, 0)
    base = 8 + cnt * 8
    out = {}
    for i in range(cnt):
        h, off = struct.unpack_from('<II', blob, 8 + i * 8)
        out[f'{h:08x}'] = decode_string(blob, base + off * 2)
    return out

def maybe_table(label, path, idx=None):
    if not path.exists():
        print(f'  [skip] {label}: missing {path}')
        return {}
    blob = read_arc_entry(path, idx) if idx is not None else path.read_bytes()
    t = parse_string_table(blob)
    print(f'  {label}: {len(t)} hashes from {path.name}')
    return t

def write_blocks(path, hashes, body_for_hash, header_comment):
    lines = [header_comment, '']
    for h in hashes:
        lines.append(f'# - {h}')
        en = body_for_hash(h)
        lines.extend(en.split('\n'))
        lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'wrote {path.relative_to(ROOT)}: {len(hashes)} blocks')

def main():
    print('Collecting English source strings from available platform dumps:')
    ps2_sys = maybe_table('PS2 sys', ROOT / 'unpacked' / 'data' / '1315_2c238264.bin')
    ps2_ui  = maybe_table('PS2 ui',  ROOT / 'unpacked' / 'data' / '1316_2c238276.bin')
    wii     = maybe_table('Wii',     ROOT / 'wii_extract' / 'DATA' / 'files' / 'data.arc', idx=1329)
    psp     = maybe_table('PSP',     ROOT / 'psp_orig_extract' / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC', idx=1316)

    ps2 = dict(ps2_sys); ps2.update(ps2_ui)
    if not (ps2 or wii or psp):
        sys.exit('No platform dumps found. See tool/init_translation_template.py docstring for required paths.')

    all_hashes = sorted(set(ps2) | set(wii) | set(psp))
    ps2_excl = sorted([h for h in ps2 if h not in wii and h not in psp])
    wii_excl = sorted([h for h in wii if h not in ps2 and h not in psp])
    psp_excl = sorted([h for h in psp if h not in ps2 and h not in wii])
    print(f'\nUnion: {len(all_hashes)} unique hashes')
    print(f'  PS2-exclusive: {len(ps2_excl)}')
    print(f'  Wii-exclusive: {len(wii_excl)}')
    print(f'  PSP-exclusive: {len(psp_excl)}\n')

    def en_for(h):
        return ps2.get(h) or wii.get(h) or psp.get(h) or ''

    SHARED_HDR = (
        "# translate_shared.txt — English source strings.\n"
        "# Union of PS2 + Wii + PSP key sets (one entry per unique hash).\n"
        "# Translators: replace the body of each '# - <hash>' block with your\n"
        "# target-language translation. Inline tags <c=N> <b=N> <p> <w=N>\n"
        "# and \\n / \\t / \\r escape sequences must be preserved verbatim.\n"
        "# Per-platform overrides go into translate_{ps2,wii,psp}_only.txt."
    )
    write_blocks(TR / 'translate_shared.txt', all_hashes, en_for, SHARED_HDR)

    write_blocks(TR / 'translate_ps2_only.txt', ps2_excl, lambda h: ps2.get(h, ''),
                 "# translate_ps2_only.txt — PS2-exclusive hashes (not present on Wii or PSP).\n"
                 "# Also used as the override file for strings that should differ on PS2.")
    write_blocks(TR / 'translate_wii_only.txt', wii_excl, lambda h: wii.get(h, ''),
                 "# translate_wii_only.txt — Wii-exclusive hashes (not present on PS2 or PSP).\n"
                 "# Also used as the override file for strings that should differ on Wii.")
    write_blocks(TR / 'translate_psp_only.txt', psp_excl, lambda h: psp.get(h, ''),
                 "# translate_psp_only.txt — PSP-exclusive hashes (not present on PS2 or Wii).\n"
                 "# Also used as the override file for strings that should differ on PSP.")

    print('\nDone. Edit TEXT_TRANSLATION/translate_shared.txt to start translating.')

if __name__ == '__main__':
    main()
