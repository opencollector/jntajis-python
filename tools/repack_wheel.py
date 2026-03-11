"""Repack wheels to limit per-entry inflation below a threshold.

PyPI rejects wheels where any zip entry inflates over 50x (zip bomb detection).
This script re-compresses entries that exceed the limit using deflate with
frequent Z_FULL_FLUSH to reduce compression efficiency while keeping the
data genuinely compressed.

Usage (cibuildwheel repair-wheel-command):
    # Single wheel -> dest_dir (Windows, no prior repair step)
    python tools/repack_wheel.py WHEEL DEST_DIR

    # All wheels in a directory, in-place (after auditwheel/delocate)
    python tools/repack_wheel.py DEST_DIR
"""

import os
import struct
import sys
import time
import zlib
import zipfile

CHUNK_SIZE = 4096
MAX_INFLATION = 50


def compress_chunked(data, chunk_size):
    """Compress data with frequent flushes to reduce compression efficiency."""
    c = zlib.compressobj(1, zlib.DEFLATED, -15)
    parts = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        parts.append(c.compress(chunk))
        parts.append(c.flush(zlib.Z_FULL_FLUSH))
    parts.append(c.flush(zlib.Z_FINISH))
    return b''.join(parts)


def make_dos_datetime(dt):
    mod_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2)
    mod_date = ((dt[0] - 1980) << 9) | (dt[1] << 5) | dt[2]
    return mod_time, mod_date


def repack_wheel(src_path, dst_path):
    """Repack a wheel, limiting per-entry inflation below MAX_INFLATION.

    src_path and dst_path may be the same file (in-place repack).
    """
    with zipfile.ZipFile(src_path, 'r') as zin:
        items_data = [(item, zin.read(item.filename)) for item in zin.infolist()]

    tmp_path = dst_path + '.tmp'
    needs_repack = False

    with open(tmp_path, 'wb') as f:
        central_dir = []

        for item, data in items_data:
            crc = zlib.crc32(data) & 0xFFFFFFFF
            uncompressed_size = len(data)

            # Compress normally first
            c = zlib.compressobj(6, zlib.DEFLATED, -15)
            compressed = c.compress(data) + c.flush()

            # Check if inflation exceeds limit
            if len(compressed) > 0 and uncompressed_size / len(compressed) >= MAX_INFLATION:
                needs_repack = True
                t0 = time.time()
                compressed = compress_chunked(data, CHUNK_SIZE)
                elapsed = time.time() - t0
                inflation = uncompressed_size / len(compressed)
                print(f'  {item.filename}: {uncompressed_size} -> {len(compressed)} '
                      f'({len(compressed) / uncompressed_size * 100:.1f}%, {inflation:.1f}x) [{elapsed:.1f}s]')

            compress_type = zipfile.ZIP_DEFLATED
            compressed_size = len(compressed)

            local_header_offset = f.tell()
            fname = item.filename.encode('utf-8')
            mod_time, mod_date = make_dos_datetime(item.date_time)

            # Local file header
            f.write(struct.pack(
                '<4sHHHHHIIIHH',
                b'PK\x03\x04',
                20,  # version needed
                0,   # flags
                compress_type,
                mod_time,
                mod_date,
                crc,
                compressed_size,
                uncompressed_size,
                len(fname),
                0,   # extra length
            ))
            f.write(fname)
            f.write(compressed)

            central_dir.append((
                fname, compress_type, mod_time, mod_date,
                crc, compressed_size, uncompressed_size,
                local_header_offset, item.external_attr,
            ))

        # Central directory
        cd_offset = f.tell()
        for (fname, ct, mt, md, crc, cs, us, offset, ext_attr) in central_dir:
            f.write(struct.pack(
                '<4sHHHHHHIIIHHHHHII',
                b'PK\x01\x02',
                20,  # version made by
                20,  # version needed
                0,   # flags
                ct, mt, md, crc, cs, us,
                len(fname),
                0,   # extra length
                0,   # comment length
                0,   # disk number start
                0,   # internal attributes
                ext_attr,
                offset,
            ))
            f.write(fname)

        cd_size = f.tell() - cd_offset

        # End of central directory
        f.write(struct.pack(
            '<4sHHHHIIH',
            b'PK\x05\x06',
            0, 0,
            len(central_dir),
            len(central_dir),
            cd_size,
            cd_offset,
            0,
        ))

    if needs_repack:
        os.replace(tmp_path, dst_path)
    else:
        os.unlink(tmp_path)
        if src_path != dst_path:
            import shutil
            shutil.copy2(src_path, dst_path)


def verify_wheel(whl_path):
    with zipfile.ZipFile(whl_path, 'r') as zf:
        max_inflation = 0
        for info in zf.infolist():
            if info.compress_size > 0:
                inf = info.file_size / info.compress_size
                max_inflation = max(max_inflation, inf)
        zf.testzip()
        fsize = os.path.getsize(whl_path)
        return fsize, max_inflation


def main():
    if len(sys.argv) == 3 and not os.path.isdir(sys.argv[1]):
        # Mode: repack_wheel.py WHEEL DEST_DIR
        src_wheel = sys.argv[1]
        dest_dir = sys.argv[2]
        basename = os.path.basename(src_wheel)
        dst_wheel = os.path.join(dest_dir, basename)
        print(f'Repacking {basename}...')
        repack_wheel(src_wheel, dst_wheel)
        fsize, max_inf = verify_wheel(dst_wheel)
        print(f'  -> {fsize:,} bytes, max entry inflation={max_inf:.1f}x')
    elif len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        # Mode: repack_wheel.py DEST_DIR (in-place)
        dest_dir = sys.argv[1]
        for name in sorted(os.listdir(dest_dir)):
            if not name.endswith('.whl'):
                continue
            path = os.path.join(dest_dir, name)
            print(f'Repacking {name}...')
            repack_wheel(path, path)
            fsize, max_inf = verify_wheel(path)
            print(f'  -> {fsize:,} bytes, max entry inflation={max_inf:.1f}x')
    else:
        print(f'Usage: {sys.argv[0]} WHEEL DEST_DIR', file=sys.stderr)
        print(f'       {sys.argv[0]} DEST_DIR', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
