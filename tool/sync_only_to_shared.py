"""
Copy Cyrillic translations from per-platform _only.txt files into
translate_shared.txt for hashes where shared currently has no Cyrillic.

This is a SAFE one-way sync: shared blocks that are already translated
stay untouched. Only previously-untranslated shared blocks get filled
in from _only files. Platform-specific overrides (where _only differs
from shared on already-translated hashes) are left alone.

Run once after the user has edited per-platform _only files; can be
re-run any time — it never overwrites an existing Cyrillic body in
shared.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_TR = ROOT / 'TEXT_TRANSLATION'

SHARED = TEXT_TR / 'translate_shared.txt'
ONLY_FILES = ['translate_ps2_only.txt', 'translate_wii_only.txt', 'translate_psp_only.txt']

def has_cyrillic(s):
    return any(0x0400 <= ord(c) <= 0x04FF for c in s)

def parse_blocks(path):
    """Return list of (header_line, body_lines, prefix_blank_lines) so we
    can serialise back preserving exact structure."""
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    blocks = []
    header_comments = []
    i = 0
    # Capture leading header comments (lines starting with '#' but not '# - ')
    while i < len(lines) and not lines[i].startswith('# - '):
        header_comments.append(lines[i])
        i += 1
    while i < len(lines):
        line = lines[i]
        if line.startswith('# - '):
            hash_id = line[4:].strip().split()[0]
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith('# - '):
                # Stop body capture at blank line (block separator)
                if lines[i].strip() == '' and body:
                    break
                if lines[i].startswith('#') and not body:
                    # comment between blocks
                    i += 1
                    continue
                if lines[i].strip() == '' and not body:
                    i += 1
                    continue
                body.append(lines[i])
                i += 1
            # consume trailing blanks
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            blocks.append([hash_id, body])
        else:
            i += 1
    return header_comments, blocks

def hash_dict(blocks):
    return {h: '\n'.join(body) for h, body in blocks}

def main():
    header, shared_blocks = parse_blocks(SHARED)
    shared_dict = hash_dict(shared_blocks)
    print(f'shared.txt: {len(shared_blocks)} blocks')

    # Collect proposed copies from each _only file
    proposed = {}    # hash -> (new_body, source_file)
    for name in ONLY_FILES:
        p = TEXT_TR / name
        if not p.exists(): continue
        _, only_blocks = parse_blocks(p)
        for h, body in only_blocks:
            body_text = '\n'.join(body)
            if not has_cyrillic(body_text):
                continue
            shared_text = shared_dict.get(h, '')
            if has_cyrillic(shared_text):
                continue   # shared already translated, skip
            if h not in shared_dict:
                continue   # shared doesn't have this hash, skip
            proposed[h] = (body, name)

    if not proposed:
        print('No new translations to sync.')
        return

    print(f'Will copy {len(proposed)} translation(s) from _only into shared:')
    for h, (_body, src) in list(proposed.items())[:10]:
        print(f'  {h}  <- {src}')

    # Apply: rewrite shared.txt with the new bodies
    out_lines = list(header)
    if out_lines and out_lines[-1] != '':
        out_lines.append('')
    for h, body in shared_blocks:
        out_lines.append(f'# - {h}')
        if h in proposed:
            new_body, _ = proposed[h]
            out_lines.extend(new_body)
        else:
            out_lines.extend(body)
        out_lines.append('')

    SHARED.write_text('\n'.join(out_lines), encoding='utf-8')
    print(f'\nwrote {SHARED}  ({len(shared_blocks)} blocks, +{len(proposed)} freshly translated)')

if __name__ == '__main__':
    main()
