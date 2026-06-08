"""
Build SH:SM PSP UA ISO.

Pipeline:
  1. Sync psp_extract_work/ from psp_orig_extract/ (one-time bulk copy)
  2. Replace psp_extract_work/PSP_GAME/SYSDIR/EBOOT.BIN with Metallist's
     decrypted EBOOT (we build on top of it). Orig EBOOT is signed/encrypted.
  3. Patch EBOOT.BIN font (psp_patch_eboot.py)
  4. Pack TEXT_TRANSLATION/translate_shared.txt + translate_psp_only.txt
     -> translate_sys_psp.bin with
     SH_EXTRA_SUBST='Ї=Ï,ї=ï' (same Wii substitutions)
  5. Patch DATA.ARC (psp_arc_patch.py) in psp_extract_work
  6. Rebuild ISO via pycdlib from psp_extract_work

Output: UA_psp/Silent Hill - Shattered Memories (UA).iso (~970 MB)

PSP must be running CFW (custom firmware) to launch the unsigned EBOOT
— same constraint as Metallist's RU patch.
"""
import os, sys, subprocess, shutil, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tool'
UNPACKED = ROOT / 'unpacked'
PSP_ORIG = ROOT / 'psp_orig_extract'
PSP_RUS  = ROOT / 'psp_rus_extract'
PSP_WORK = ROOT / 'psp_extract_work'
UA_PSP = ROOT / 'UA_psp'
BUILD = UA_PSP / '_build'
BUILD.mkdir(parents=True, exist_ok=True)

ISO_OUT = UA_PSP / 'Silent Hill - Shattered Memories (UA).iso'
TR_SYS = BUILD / 'translate_sys_psp.bin'

PSP_EXTRA_SUBST = 'Ї=Ï,ї=ï'   # Ї/ї are substituted to Latin Ï/ï at pack
                              # time; the font has Ï/ï records via extension.

# Custom glyph PNGs (user-edited overrides). Anything dropped into
# unpacked/glyphs_psp/ matching a known codepoint gets injected after the
# base font patch. File name -> codepoint mapping:
PNG_GLYPH_MAP = {
    'ye_upper.png':       0x0404,   # Є  (user-rotated from Cyrillic Э)
    'ye_lower.png':       0x0454,   # є  (user-rotated from э)
    'i_diaeresis_upper.png': 0x00CF, # Ï  (user-drawn dots on Latin I)
    'gh_upper.png':       0x0490,   # Ґ  (user-drawn hook on Г)
    'gh_lower.png':       0x0491,   # ґ  (user-drawn hook on г)
}

def run(cmd, label, env=None):
    print(f'\n>>> {label}')
    print(f'    {" ".join(map(str, cmd))}')
    r = subprocess.run(cmd, check=False, env=env)
    if r.returncode != 0:
        sys.exit(f'!!! {label} failed (exit {r.returncode})')

def sync_work_dir():
    if PSP_WORK.exists():
        # Reset DATA.ARC and EBOOT.BIN from orig — keep other files
        shutil.copyfile(PSP_ORIG / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC',
                        PSP_WORK / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC')
        print('    reset DATA.ARC from orig (other files left intact)')
    else:
        print(f'    copying {PSP_ORIG} -> {PSP_WORK} (one-time, ~1 GB)')
        shutil.copytree(PSP_ORIG, PSP_WORK)
    # Always replace EBOOT.BIN with Metallist's decrypted ELF as starting base
    shutil.copyfile(PSP_RUS / 'PSP_GAME' / 'SYSDIR' / 'EBOOT.BIN',
                    PSP_WORK / 'PSP_GAME' / 'SYSDIR' / 'EBOOT.BIN')
    print('    EBOOT.BIN = Metallist decrypted ELF (base for our patches)')

def build_iso():
    # Pure ISO9660 (NO Joliet, NO UDF), matching real PSP UMD structure
    # observed in known-bootable PSN-rips. Real PSP firmware reads UMD via
    # ISO9660 only — Joliet extensions confuse Inferno driver. Filenames are
    # already 8.3-compatible in PSP_GAME structure, so no Joliet needed.
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1, vol_ident='NO LABEL',
            sys_ident='PSP GAME', app_ident_str='PSP GAME')
    src = PSP_WORK
    dirs = sorted([p for p in src.rglob('*') if p.is_dir()])
    files = sorted([p for p in src.rglob('*') if p.is_file()])
    for d in dirs:
        rel = d.relative_to(src).as_posix()
        iso.add_directory('/' + rel.upper())
    for f in files:
        rel = f.relative_to(src).as_posix()
        iso_path = '/' + rel.upper() + ';1'
        iso.add_file(str(f), iso_path=iso_path)
    if ISO_OUT.exists():
        ISO_OUT.unlink()
    iso.write(str(ISO_OUT))
    iso.close()
    # Real PSP firmware reads file identifiers literally; the ;1 version
    # suffix that pycdlib mandates trips up Inferno driver's name lookup.
    # Strip ;N from every directory record's file identifier in place.
    _strip_version_suffix(ISO_OUT)
    print(f'    wrote {ISO_OUT}: {ISO_OUT.stat().st_size:,} bytes')

def _strip_version_suffix(iso_path):
    """Post-process: for every directory record whose file identifier ends
    with ;N, shrink name_len by 2 (or whatever ';N' length is) and zero
    out the trailing bytes. Keeps rec_len + LBAs unchanged."""
    import struct
    data = bytearray(iso_path.read_bytes())
    # Parse PVD at sector 16 to find path table and walk all dirs.
    pvd = bytes(data[16*2048:17*2048])
    root_dr = pvd[156:156+34]
    root_lba  = struct.unpack_from('<I', root_dr, 2)[0]
    root_size = struct.unpack_from('<I', root_dr, 10)[0]

    visited = set()
    queue = [(root_lba, root_size)]
    n_stripped = 0
    while queue:
        lba, size = queue.pop()
        if (lba, size) in visited: continue
        visited.add((lba, size))
        sec_off = lba * 2048
        off = 0
        while off < size:
            rec_off = sec_off + off
            rec_len = data[rec_off]
            if rec_len == 0:
                # skip to next sector boundary
                off = ((off // 2048) + 1) * 2048
                continue
            flags = data[rec_off + 25]
            name_len = data[rec_off + 32]
            name_off = rec_off + 33
            name = bytes(data[name_off : name_off + name_len])
            # If it's a real dir (not '.' or '..'), enqueue its extent
            if flags & 0x02 and name not in (b'\x00', b'\x01'):
                d_lba  = struct.unpack_from('<I', data, rec_off + 2)[0]
                d_size = struct.unpack_from('<I', data, rec_off + 10)[0]
                queue.append((d_lba, d_size))
            # Strip ;N from file identifiers
            semi = name.rfind(b';')
            if semi != -1 and semi > 0:
                ver = name[semi+1:]
                if ver.isdigit():
                    new_len = semi
                    # Update name_len byte
                    data[rec_off + 32] = new_len
                    # Zero out the ';N' bytes
                    for i in range(semi, name_len):
                        data[name_off + i] = 0
                    n_stripped += 1
            off += rec_len
    iso_path.write_bytes(bytes(data))
    print(f'    stripped ;N from {n_stripped} directory records')

def main():
    if not (PSP_ORIG / 'PSP_GAME' / 'USRDIR' / 'DATA.ARC').exists():
        sys.exit(f'missing PSP orig extract at {PSP_ORIG}')
    if not (PSP_RUS / 'PSP_GAME' / 'SYSDIR' / 'EBOOT.BIN').exists():
        sys.exit(f'missing PSP rus extract at {PSP_RUS}')
    if not (ROOT / 'TEXT_TRANSLATION' / 'translate_shared.txt').exists():
        sys.exit(f'missing TEXT_TRANSLATION/translate_shared.txt — '
                 f'run tool/build_shared_translation.py first')

    print('\n>>> sync psp_extract_work/ from orig + Metallist EBOOT')
    sync_work_dir()

    run([sys.executable, str(TOOL/'psp_patch_eboot.py')],
        'patch PSP EBOOT.BIN font')

    # Inject any user-edited PNG overrides
    glyph_dir = UNPACKED / 'glyphs_psp'
    if glyph_dir.exists():
        for png_name, cp in PNG_GLYPH_MAP.items():
            png_path = glyph_dir / png_name
            if png_path.exists():
                run([sys.executable, str(TOOL/'psp_kfont_png_edit.py'),
                     'inject', hex(cp), '--in', str(png_path)],
                    f'inject U+{cp:04X} from {png_name}')

    env = os.environ.copy()
    if PSP_EXTRA_SUBST:
        env['SH_EXTRA_SUBST'] = PSP_EXTRA_SUBST
    run([sys.executable, str(TOOL/'pack_platform_strings.py'),
         'psp', str(TR_SYS)],
        'pack PSP strings from TEXT_TRANSLATION/ (shared + psp_only)', env=env)

    run([sys.executable, str(TOOL/'psp_arc_patch.py')],
        'patch PSP DATA.ARC')

    print('\n>>> rebuild ISO (pycdlib)')
    build_iso()

    print(f'\nDone. Run {ISO_OUT.name} on PPSSPP or CFW PSP.')

if __name__ == '__main__':
    main()
