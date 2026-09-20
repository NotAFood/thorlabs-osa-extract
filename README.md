# thorlabs-osa-extract

Convert Thorlabs OSA `.spf2` spectrum files (e.g. from a CCS200 spectrometer) to CSV, keeping the file metadata as `#` comment lines.

## Usage

```bash
uv venv && uv pip install numpy
.venv/bin/python spf2_to_csv.py *.spf2
```

Each `foo.spf2` produces a `foo.csv` next to it:

```
# source_file: foo.spf2
# instrument: Thorlabs CCS200 spectrometer
# serial_number: ...
# integration_time_ms: 1
# ...
# wavelength_units: nm (air)
# intensity_units: relative intensity (arbitrary units, not absolute)
wavelength_nm,intensity
192.417969,0.000953
...
```

Load it with `pandas.read_csv(path, comment="#")`.

## File layout

Reverse-engineered from CCS200 files (little-endian, 35,284 bytes):

| Offset | Type | Field |
|---|---|---|
| 8 | uint32 | date, `YYYYMMDD` |
| 12 | uint32 | save time, `HHMMSScc` (local) |
| 258 | C string | serial number |
| 312 / 316 | uint32 | second time field, local / UTC (likely acquisition start) |
| 524 | uint32 | pixel count (3648) |
| 856 | C string | device name |
| 900 | float64 | integration time (ms) |
| 908 | C string | model |
| 6100 | 3648 × float32 | wavelengths (nm, air) |
| 20692 | 3648 × float32 | intensities (relative intensity) |

The header contains more fields that are not decoded. The script rejects files that are not exactly 35,284 bytes, so other instruments or firmware may need different offsets.

## Credit

The parser in [chnlqsray/ganpl-analysis](https://github.com/chnlqsray/ganpl-analysis) (`parse_spf2` in `GaN_PL.py`) was the starting point. Its payload offsets did not match my files, so they were re-derived here.
