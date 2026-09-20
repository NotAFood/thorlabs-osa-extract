"""Convert Thorlabs OSA .spf2 files to CSV (metadata as '#' comment lines).

Layout (little-endian, reverse-engineered from 35,284-byte CCS200 files):
    byte    8 : uint32 date YYYYMMDD
    byte   12 : uint32 save time HHMMSScc (local, cc = hundredths)
    byte  258 : NUL-terminated ASCII serial number
    byte  312 : uint32 second local time HHMMSScc (probably acquisition start)
    byte  316 : uint32 same time in UTC (HHMMSScc)
    byte  524 : uint32 pixel count (3648)
    byte  856 : NUL-terminated ASCII device name
    byte  900 : float64 integration time (ms)
    byte  908 : NUL-terminated ASCII model
    byte 6100 : 3648 x float32 wavelengths (nm, air)
    byte 20692: 3648 x float32 intensities (relative intensity)
Usage: python spf2_to_csv.py file1.spf2 [file2.spf2 ...]
"""
import struct
import sys
from pathlib import Path

import numpy as np

N_PIXELS = 3648
WL_OFFSET = 6100
INT_OFFSET = WL_OFFSET + N_PIXELS * 4
EXPECTED_SIZE = INT_OFFSET + N_PIXELS * 4


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _cstr(data: bytes, off: int) -> str:
    return data[off:data.index(b"\0", off)].decode("ascii", "replace")


def _fmt_time(hhmmsscc: int) -> str:
    s = f"{hhmmsscc:08d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}.{s[6:8]}"


def _fmt_date(yyyymmdd: int) -> str:
    s = f"{yyyymmdd:08d}"
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def parse_metadata(data: bytes) -> dict:
    return {
        "instrument": _cstr(data, 908),
        "serial_number": _cstr(data, 258),
        "device_name": _cstr(data, 856),
        "integration_time_ms": struct.unpack_from("<d", data, 900)[0],
        "pixel_count": _u32(data, 524),
        "date": _fmt_date(_u32(data, 8)),
        "save_time_local": _fmt_time(_u32(data, 12)),
        "second_time_local": _fmt_time(_u32(data, 312)),
        "second_time_utc": _fmt_time(_u32(data, 316)),
    }


def parse_spf2(path: Path):
    data = path.read_bytes()
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"{path.name}: {len(data)} bytes, expected {EXPECTED_SIZE}")
    wl = np.frombuffer(data, "<f4", N_PIXELS, WL_OFFSET).astype(float)
    inten = np.frombuffer(data, "<f4", N_PIXELS, INT_OFFSET).astype(float)
    return wl, inten, parse_metadata(data)


def header_lines(path: Path, meta: dict) -> list[str]:
    return [
        f"source_file: {path.name}",
        f"instrument: Thorlabs {meta['instrument']} spectrometer",
        f"serial_number: {meta['serial_number']}",
        f"device_name: {meta['device_name']}",
        f"integration_time_ms: {meta['integration_time_ms']:g}",
        f"pixel_count: {meta['pixel_count']}",
        f"date: {meta['date']}",
        f"save_time_local: {meta['save_time_local']}",
        f"second_time_local: {meta['second_time_local']} (likely acquisition start)",
        f"second_time_utc: {meta['second_time_utc']}",
        "wavelength_units: nm (air)",
        "intensity_units: relative intensity (arbitrary units, not absolute)",
    ]


def convert(path: Path) -> Path:
    wl, inten, meta = parse_spf2(path)
    out = path.with_suffix(".csv")
    np.savetxt(out, np.column_stack((wl, inten)), delimiter=",",
               fmt="%.6f", header="wavelength_nm,intensity", comments="")
    body = out.read_text()
    out.write_text("".join(f"# {line}\n" for line in header_lines(path, meta)) + body)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(convert(Path(p)))
