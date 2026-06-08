"""
Dump the SH:SM Strings message table (version 2) into a TSV.

Format (from consolgames-tools Strings.cpp):
  u32 version = 2
  u32 stringCount
  per string: u32 hash, u32 offset (in UINT16 units)
  block of UTF-16 LE NUL-terminated strings with inline control codes:
    1 N   -> <c=N>   color
    2     -> <p>     paragraph
    3 N   -> <b=N>   button icon
    4 N   -> <w=N>   delay

Output TSV columns: hash, text.
"""
import sys, struct, pathlib

def decode_string(data, pos):
    out = []
    while pos < len(data) - 1:
        u = data[pos] | (data[pos+1] << 8)
        pos += 2
        if u == 0:
            break
        if u == 1:
            if pos+1 < len(data):
                n = data[pos] | (data[pos+1] << 8); pos += 2
                out.append(f'<c={n}>')
        elif u == 2:
            out.append('<p>')
        elif u == 3:
            if pos+1 < len(data):
                n = data[pos] | (data[pos+1] << 8); pos += 2
                out.append(f'<b={n}>')
        elif u == 4:
            if pos+1 < len(data):
                n = data[pos] | (data[pos+1] << 8); pos += 2
                out.append(f'<w={n}>')
        elif u == 0x0A:
            out.append('\\n')
        elif u == 0x09:
            out.append('\\t')
        else:
            out.append(chr(u))
    return ''.join(out), pos

def dump(arc_file, out_tsv):
    data = pathlib.Path(arc_file).read_bytes()
    ver, cnt = struct.unpack_from('<II', data, 0)
    if ver != 2:
        print(f'WARN: version={ver}, expected 2');
    records = []
    for i in range(cnt):
        h, off = struct.unpack_from('<II', data, 8 + i*8)
        records.append((h, off))
    text_base = 8 + cnt*8
    with open(out_tsv, 'w', encoding='utf-8', newline='') as f:
        f.write('hash\ttext\n')
        for i, (h, off) in enumerate(records):
            pos = text_base + off*2
            s, _ = decode_string(data, pos)
            # TSV-safe escapes
            s = s.replace('\t','\\t').replace('\r','\\r').replace('\n','\\n')
            f.write(f'{h:08x}\t{s}\n')
    print(f'Wrote {cnt} messages to {out_tsv}')

if __name__ == '__main__':
    dump(sys.argv[1], sys.argv[2])
