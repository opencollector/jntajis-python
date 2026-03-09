# Architecture

## Project Overview

jntajis-python is a Python library for transliterating and encoding/decoding characters across three Japanese character set standards: JIS X 0208, JIS X 0213, and Unicode. It also supports transliteration via the MJ (Moji Joho) character table and shrink conversion maps.

## Directory Layout

```
jntajis-python/
  setup.py                        # setuptools + Cython extension build
  setup.cfg                       # Package metadata, dependencies, dev extras
  Makefile                        # Data pipeline: download -> parse -> codegen
  src/jntajis/
    __init__.py                   # Public Python API surface (enums + re-exports)
    _jntajis.pyx                  # Cython implementation (core logic)
    _jntajis.h                    # Generated C header (lookup tables)
    _jntajis.pyi                  # Type stubs for the Cython extension
    _jntajis.c                    # Cython-generated C source (not committed normally)
    gen.py                        # Code generator: Excel/JSON -> _jntajis.h
    py.typed                      # PEP 561 marker
    tests/
      test_encoder.py             # Tests for encoding/decoding and IncrementalEncoder
      test_mj_translit.py         # Tests for MJ shrink candidate transliteration
    xlsx_parser/
      __init__.py                 # Re-exports read_xlsx
      parser.py                   # Streaming OpenXML XLSX reader
      xmlutils.py                 # SAX-style XML parser framework (expat-based)
  docs/
    source/
      api.rst                     # Sphinx API documentation
      conf.py                     # Sphinx configuration
      _static/images/             # SVG diagrams
  .github/workflows/
    main.yml                      # CI entry point (PR + push + tag triggers)
    tests.yml                     # Lint (black, flake8, mypy) + test job
    wheels.yml                    # cibuildwheel multi-platform wheel builds
```

## High-Level Architecture

The system has three distinct phases: **data pipeline** (build-time), **native extension** (compile-time), and **runtime API** (user-facing).

### 1. Data Pipeline (build-time, `Makefile` + `gen.py`)

External data sources are downloaded and processed into a single generated C header file:

```
[JNTA Excel] ---+
[MJ Excel]   ---+--> gen.py (Jinja2 template) --> _jntajis.h (C lookup tables)
[MJ Shrink JSON]+
```

- **JNTA Excel** (`jissyukutaimap1_0_0.xlsx`): NTA shrink conversion map. Downloaded from NTA.
- **MJ Excel** (`mji.00601.xlsx`): MJ character table. Downloaded from CITPC/IPA.
- **MJ Shrink JSON** (`MJShrinkMap.1.2.0.json`): MJ shrink conversion map. Downloaded from CITPC/IPA.

`gen.py` uses a custom `xlsx_parser` to read the Excel files, processes the data into optimized lookup structures, and renders `_jntajis.h` via a Jinja2 template. The generated header contains:

- `tx_mappings[]`: 2*94*94 entries, one per JIS X 0213 codepoint (men-ku-ten)
- `urange_to_jis_mappings[]`: Sorted ranges for Unicode-to-JIS binary search
- `sm_uni_to_jis_mapping()`: State machine for multi-codepoint Unicode-to-JIS mapping
- `urange_to_mj_mappings[]`: Sorted ranges for Unicode-to-MJ-mapping-set binary search
- `mj_shrink_mappings[]`: MJ shrink mapping unicode sets indexed by MJ code

### 2. Native Extension (compile-time, Cython)

`_jntajis.pyx` is a Cython file compiled into a C extension module. It:

- Includes `_jntajis.h` via `cdef extern` to access the generated lookup tables
- Uses CPython internal APIs (`_PyUnicodeWriter`, `_PyBytesWriter`, `PyUnicode_READ`, etc.) directly for high-performance string construction
- Compiles with safety checks disabled (`boundscheck=False`, `wraparound=False`, `cdivision=True`)

The build process is: `_jntajis.pyx` + `_jntajis.h` --> Cython --> `_jntajis.c` --> C compiler --> `_jntajis.so`.

### 3. Runtime API

The public API is exposed via `__init__.py` which re-exports from the Cython extension:

| Symbol | Type | Description |
|--------|------|-------------|
| `jnta_encode()` | function | Unicode -> JIS byte sequence |
| `jnta_decode()` | function | JIS byte sequence -> Unicode |
| `jnta_shrink_translit()` | function | JNTA shrink transliteration (Unicode -> Unicode) |
| `mj_shrink_candidates()` | function | MJ-based shrink transliteration candidates |
| `IncrementalEncoder` | class | Stateful encoder (codec-compatible) |
| `TransliterationError` | exception | Raised on transliteration failure |
| `ConversionMode` | enum | Encoding mode selection |
| `MJShrinkScheme` | enum | Individual MJ shrink scheme identifiers |
| `MJShrinkSchemeCombo` | flag enum | Combinable MJ shrink scheme selectors |

## Key Data Structures

### JIS Code Representation

JIS codepoints are packed into a `uint16_t` as: `(men - 1) * 94 * 94 + (ku - 1) * 94 + (ten - 1)`, where men is 1 or 2 (JIS X 0213 plane), ku is 1-94 (row), ten is 1-94 (column).

### ShrinkingTransliterationMapping

Each JIS X 0213 position has an entry:
- `jis`: packed men-ku-ten code
- `us[2]`: primary Unicode codepoint(s)
- `sus[2]`: secondary (similar glyph) Unicode codepoint(s)
- `class_`: JIS character class (level 1-4, non-kanji, reserved)
- `tx_jis[4]`/`tx_us[4]`: transliterated form (JIS and Unicode)

### Unicode-to-JIS Reverse Lookup

Uses sorted range tables (`URangeToJISMapping`) with binary search. Multi-codepoint sequences (e.g. base + combining mark) use a state machine (`sm_uni_to_jis_mapping()`).

### MJ Mapping Structures

- `MJMapping`: Maps an MJ code to Unicode codepoints + IVS (Ideographic Variation Sequence) pairs
- `MJMappingSet`: A set of MJ mappings for a single Unicode codepoint
- `URangeToMJMappings`: Sorted range table for Unicode-to-MJ binary search
- `MJShrinkMappingUnicodeSet`: Per-MJ-code shrink targets, one array per scheme (4 schemes)

## Component Interactions

```
User code
  |
  v
__init__.py  (Python enums + re-exports)
  |
  v
_jntajis.pyx  (Cython: encoding, decoding, transliteration logic)
  |
  v
_jntajis.h  (Generated C: static lookup tables + state machine)
```

## xlsx_parser Sub-package

A lightweight, streaming, read-only XLSX parser. It avoids heavyweight dependencies like openpyxl by:

1. Opening XLSX as a zip file (`zipfile.ZipFile`)
2. Parsing `xl/sharedStrings.xml` for the shared string table
3. Parsing `xl/worksheets/sheetN.xml` incrementally via SAX-style handlers

The XML parsing framework in `xmlutils.py` provides:
- A hierarchical `Handlers`/`HandlersBase` abstract pattern where each nesting level of XML is handled by a different handler class
- `HandlerShim` wraps handlers to dynamically switch the active handler as XML nesting changes
- `read_xml_incremental()` enables pull-style iteration over worksheet rows

## CI/CD

- **Trigger** (`main.yml`): On PR open, push to main, or version tag push (`v*`)
- **Lint & Test** (`tests.yml`): black + flake8 + mypy on Python 3.11
- **Wheels** (`wheels.yml`): cibuildwheel across Ubuntu, Windows, macOS (11/12/13), excluding PyPy. Only runs on tag push.

## Documentation

Sphinx with `sphinx_rtd_theme`, hosted on Read the Docs. API docs are manually authored in `api.rst` (not autodoc).
