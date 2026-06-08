"""
Re-pack a SH:SM strings table (version 2) from JSON/TSV → .bin.

Format mirrors strings_dump.py:
  u32 version = 2
  u32 stringCount
  per string: u32 hash, u32 offset (in UINT16 units, base = 8 + count*8)
  block of UTF-16 LE NUL-terminated strings with inline control codes:
     1 N  -> <c=N>   color
     2    -> <p>     paragraph
     3 N  -> <b=N>   button icon
     4 N  -> <w=N>   delay
     literal \n, \t, \r are restored to U+000A, U+0009, U+000D

Usage:
    python strings_pack.py <hashes.tsv> <out.bin>   # hashes.tsv columns: hash<TAB>text
    python strings_pack.py --merge <translate_ui.tsv> <out.bin>
        # uses 'ua' column when non-empty, else falls back to 'en'

Round-trip test (verify our format understanding is correct):
    python strings_dump.py orig.bin tmp.tsv
    python strings_pack.py tmp.tsv  tmp.bin
    cmp orig.bin tmp.bin     # should differ ONLY due to shared-string dedup
"""
import os, sys, struct, pathlib, re, json

TAG_RX = re.compile(r'<([cbw])=(-?\d+)>|<p>')
ESC_RX = re.compile(r'\\([nrt\\])')
ESC_MAP = {'n':'\n','r':'\r','t':'\t','\\':'\\'}

# Env var SH_NATIVE_CHARS allows testing: e.g. SH_NATIVE_CHARS="Лл" disables
# substitute for upper/lower Л — the engine receives native U+041B.
_NATIVE = set(os.environ.get('SH_NATIVE_CHARS', ''))

# Latin-1 supplement accented characters → plain ASCII. Metallist overwrote
# the CharRecord slots that previously held À..ÿ accented letters with
# Cyrillic codepoints, so the font no longer has glyphs for á é í ó ü etc.
# Without this substitute, credits like "Andr<é> Schreiber" render as "Andr?".
LAT1_SUBST = str.maketrans({
    'À':'A','Á':'A','Â':'A','Ã':'A','Ä':'A','Å':'A','Æ':'A',
    'Ç':'C','Ð':'D',
    'È':'E','É':'E','Ê':'E','Ë':'E',
    'Ì':'I','Í':'I','Î':'I','Ï':'I',
    'Ñ':'N',
    'Ò':'O','Ó':'O','Ô':'O','Õ':'O','Ö':'O','Ø':'O','Œ':'O',
    'Ù':'U','Ú':'U','Û':'U','Ü':'U',
    'Ý':'Y','Ÿ':'Y',
    'Þ':'P','ß':'s',
    'à':'a','á':'a','â':'a','ã':'a','ä':'a','å':'a','æ':'a',
    'ç':'c','ð':'d',
    'è':'e','é':'e','ê':'e','ë':'e',
    'ì':'i','í':'i','î':'i','ï':'i',
    'ñ':'n',
    'ò':'o','ó':'o','ô':'o','õ':'o','ö':'o','ø':'o','œ':'o',
    'ù':'u','ú':'u','û':'u','ü':'u',
    'ý':'y','ÿ':'y',
    'þ':'p',
})

# Cyrillic → Latin shape-identical (used by Metallist trick: write Latin in
# text for chars that look the same, since the font doesn't have those Cyrillic
# codepoints. Engine renders Latin bitmap which is visually identical.)
CYR2LAT_SUBST = str.maketrans({
    # Latin-shape Cyrillic that's ABSENT from rus font → use Latin glyph
    # (verified by inspecting rus text: они substitute these exact letters too)
    'А':'A','В':'B','Е':'E','К':'K','М':'M','Н':'H','О':'O',
    'Р':'P','С':'C','Т':'T','Х':'X',
    'З':'3',                              # uppercase З absent — use digit 3
    # Ukrainian І/і substitute to Latin I/i on both platforms:
    #   PS2: U+0406/U+0456 records point at Latin I/i bitmaps via donor
    #   Wii: no record for U+0406/U+0456; engine renders Latin I/i directly
    'І':'I','і':'i',
    # Л removed: rus font HAS Cyrillic Л natively (idx 113).
    # UA letters Є є Ї ї removed: native CharRecords on PS2; Wii uses
    # SH_EXTRA_SUBST (Ї→Ï, ї→ï).
    # Ґ ґ removed: native CharRecords on both PS2 and Wii.
    # Lowercase substitutes — only for codepoints NOT in patched font.
    'а':'a','е':'e','о':'o','р':'p','с':'c','у':'y','х':'x',
})

# Apply SH_NATIVE_CHARS — chars listed there are removed from the substitute
# table so they survive packing as native Cyrillic codepoints.
for _ch in _NATIVE:
    CYR2LAT_SUBST.pop(ord(_ch), None)
if _NATIVE:
    print(f'[strings_pack] SH_NATIVE_CHARS active: {"".join(sorted(_NATIVE))} '
          f'→ left native', file=sys.stderr)

# SH_EXTRA_SUBST extends the table with platform-specific substitutions.
# Format: "Ї=Ï,ї=ï,І=I". Used by Wii build to map letters that have
# different donor slots than PS2.
_EXTRA = os.environ.get('SH_EXTRA_SUBST', '')
if _EXTRA:
    for pair in _EXTRA.split(','):
        if '=' in pair:
            src, dst = pair.split('=', 1)
            if len(src) == 1 and len(dst) == 1:
                CYR2LAT_SUBST[ord(src)] = ord(dst)
    print(f'[strings_pack] SH_EXTRA_SUBST applied: {_EXTRA}', file=sys.stderr)

def encode_text(text: str) -> bytes:
    # First strip Latin-1 accents (á→a, é→e, ñ→n, ...): rus font no longer
    # has CharRecords for accented Latin-1 supplement codepoints.
    text = text.translate(LAT1_SUBST)
    # Then Cyrillic look-alike substitution (А→A, В→B, ...) so the engine
    # renders them via existing Latin glyphs.
    text = text.translate(CYR2LAT_SUBST)
    out = bytearray()
    i = 0
    while i < len(text):
        # try a tag
        m = TAG_RX.match(text, i)
        if m:
            if m.group(0) == '<p>':
                out += b'\x02\x00'
            else:
                t, n = m.group(1), int(m.group(2))
                opcode = {'c':1,'b':3,'w':4}[t]
                out += struct.pack('<HH', opcode, n & 0xFFFF)
            i = m.end()
            continue
        # try an escape
        if text[i] == '\\' and i+1 < len(text) and text[i+1] in 'nrt\\':
            out += ESC_MAP[text[i+1]].encode('utf-16le')
            i += 2
            continue
        # literal char
        out += text[i].encode('utf-16le')
        i += 1
    out += b'\x00\x00'   # NUL terminator
    return bytes(out)

def read_input(path, merge_mode=False):
    """Return list of (hash, text) in file order.

    Accepts .txt (preferred translation format), .json, or .tsv (legacy).

    .txt format (minimal block):
        # - <id>
        text on next line(s)
        <blank line>

    User edits the text in-place (no separate en/ua fields).
    """
    path = pathlib.Path(path)
    rows = []
    if path.suffix.lower() == '.txt':
        text = path.read_text(encoding='utf-8')
        cur_id = None
        cur_body = []
        def flush():
            if cur_id is not None:
                body = '\n'.join(cur_body).rstrip('\n')
                rows.append((int(cur_id, 16), body))
        for line in text.splitlines():
            if line.startswith('# - '):
                flush()
                cur_id = line[4:].strip().split(maxsplit=1)[0]
                cur_body = []
            elif line.startswith('#'):
                continue   # header/comment line
            elif line == '' and cur_id is not None and not cur_body:
                continue   # blank line right after header
            elif line == '':
                # blank line ends current block
                flush()
                cur_id = None
                cur_body = []
            else:
                if cur_id is not None:
                    cur_body.append(line)
        flush()
        return rows
    if path.suffix.lower() == '.json':
        entries = json.loads(path.read_text(encoding='utf-8'))
        # Translation file is a list of {en, ua}. Hashes live in a sibling
        # *_ids.json read-only file (so user never sees id clutter).
        # The two arrays are aligned by index — entry N uses ids[N].
        ids_path = path.with_name(path.stem + '_ids.json')
        if not ids_path.exists():
            sys.exit(f'missing id-mapping file: {ids_path}\n'
                     f'Re-run tool/tsv_to_json.py to regenerate it.')
        ids = json.loads(ids_path.read_text(encoding='utf-8'))
        if len(ids) != len(entries):
            sys.exit(f'translation/id-mapping size mismatch: '
                     f'{len(entries)} entries vs {len(ids)} ids in '
                     f'{ids_path.name}. Did you add/delete rows in the '
                     f'translation file? Order and count must stay aligned.')
        for hex_id, e in zip(ids, entries):
            h = int(hex_id, 16)
            ua = e.get('ua', '')
            en = e.get('en', '')
            text = ua if ua else en
            rows.append((h, text))
        return rows
    # TSV fallback
    with open(path, encoding='utf-8') as f:
        next(f)  # header
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if merge_mode:
                h, en, _ru, ua = (parts + ['','','',''])[:4]
                text = ua if ua else en
            else:
                h, text = (parts + [''])[:2]
            rows.append((int(h, 16), text))
    return rows

# Legacy alias (any callers using the old name keep working)
read_tsv = read_input

def collect_cyrillic_codepoints(rows, min_records=20):
    """Scan rows for Cyrillic codepoints AND count how many unique records
    each appears in. Return only codepoints that appear in fewer than
    `min_records` records — these are the ones needing warmup. Codepoints
    already widespread get cached naturally and don't need help."""
    records_with_cp = {}     # cp -> set of row indices that contain it
    for idx, (_h, text) in enumerate(rows):
        for cp in {ord(c) for c in text.translate(CYR2LAT_SUBST)
                   if 0x0400 <= ord(c) <= 0x04FF}:
            records_with_cp.setdefault(cp, set()).add(idx)
    rare = [cp for cp, recs in records_with_cp.items() if len(recs) < min_records]
    return sorted(rare)

def build_warmup_rows(cyr_cps, records_per_cp=50, fake_hash_base=0xDEAD0000):
    """Build synthetic records: many per Cyrillic codepoint, each with a
    fake hash that no engine code references. Engine pre-cache scans
    early records and registers each codepoint's glyph; user never sees
    these because no game code looks up the fake hashes.

    Engine appears to count UNIQUE RECORDS containing a codepoint, not
    raw character frequency — test showed 100 Л copies in 1 record did
    not cache, but 1 Л in 100 different records did. We default to 50
    records per codepoint as a safe margin."""
    rows = []
    idx = 0
    for cp in cyr_cps:
        for _ in range(records_per_cp):
            h = fake_hash_base + idx
            rows.append((h, chr(cp)))
            idx += 1
    return rows

def pack(rows, dedup=True, warmup=True):
    """Build the binary blob with shared-string deduplication (matches
    consolgames-tools collapseDuplicates behavior)."""
    if warmup:
        # Engine has a finite glyph atlas (FIFO/LRU eviction). Cyrillic
        # codepoints get added to atlas the first time the engine renders
        # them. Codepoints already FREQUENT in real strings get cached
        # naturally; broken ones below the atlas-survival threshold get
        # evicted before they're needed.
        #
        # MINIMAL warmup: only prepend codepoints that are KNOWN broken in
        # our build. Cycling through many codepoints fills the atlas with
        # our prefixes, evicting OTHER codepoints that previously worked.
        #
        # Currently known-broken in our NTSC-U + UA build:
        #   U+041B Л  (uppercase, atlas miss)
        # If more codepoints turn up broken, add them here. NEVER include
        # codepoints that already render — adding them only displaces
        # other glyphs from atlas.
        FORCE_PREFIX = (0x041B,)
        PREPEND_COUNT = 100
        new_rows = list(rows)
        cycle = list(FORCE_PREFIX)
        for i in range(min(PREPEND_COUNT, len(new_rows))):
            cp = cycle[i % len(cycle)]
            h, text = new_rows[i]
            new_rows[i] = (h, chr(cp) + text)
        rows = new_rows
        print(f'[strings_pack] prepended {", ".join(f"U+{cp:04X}" for cp in cycle)} '
              f'to first {PREPEND_COUNT} rows for glyph-cache warmup',
              file=sys.stderr)
    count = len(rows)
    # First pass: encode each string, dedup by exact byte content.
    blob = bytearray()
    offs = []
    seen = {}                     # encoded_bytes -> offset_in_u16
    for h, text in rows:
        enc = encode_text(text)
        if dedup and enc in seen:
            offs.append(seen[enc])
        else:
            off_u16 = len(blob) // 2
            seen[enc] = off_u16
            blob.extend(enc)
            offs.append(off_u16)
    # Assemble
    header = struct.pack('<II', 2, count)
    table = b''.join(struct.pack('<II', h, off) for (h, _t), off in zip(rows, offs))
    out = header + table + bytes(blob)
    # Pad to a 4-byte boundary at the end (engine reads u32 freely; safer)
    pad = (-len(out)) & 3
    return out + (b'\x00' * pad)

def main():
    args = sys.argv[1:]
    merge_mode = False
    warmup = True
    while args and args[0].startswith('--'):
        if args[0] == '--merge':
            merge_mode = True
            args = args[1:]
        elif args[0] == '--no-warmup':
            warmup = False
            args = args[1:]
        else:
            print(f'unknown flag {args[0]}'); sys.exit(1)
    if len(args) != 2:
        print(__doc__); sys.exit(1)
    rows = read_input(args[0], merge_mode=merge_mode)
    blob = pack(rows, warmup=warmup)
    pathlib.Path(args[1]).write_bytes(blob)
    print(f'Wrote {args[1]}  ({len(blob):,} bytes, {len(rows):,} strings)')

if __name__ == '__main__':
    main()
