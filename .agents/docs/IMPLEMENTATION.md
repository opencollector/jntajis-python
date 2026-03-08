# Implementation Details

## Code Generation (`gen.py`)

### Entry Point

`gen.py` provides a CLI via `click`:

```
python -m jntajis.gen -- <dest> <src_jnta> <src_mj> <src_mj_shrink>
```

### Input Parsing

Three source data files are read:

1. **`read_jnta_excel_file()`** parses the NTA shrink map Excel:
   - Validates header rows match expected Japanese column names
   - For each row: parses men-ku-ten code, Unicode codepoint(s), JIS character class, transliteration target (single or multi-char)
   - Fills gaps between consecutive JIS codes with `RESERVED` entries
   - Extracts secondary Unicode mappings from memo fields via regex

2. **`read_mj_excel_file()`** parses the MJ character table Excel:
   - Extracts MJ code, corresponding UCS, implemented UCS, IVS pairs (Moji_Joho collection + SVS)
   - Builds `UIVSPair` tuples (Unicode codepoint + variation selector number)
   - Tracks max variant count across all entries

3. **`read_mj_shrink_file()`** parses the MJ shrink map JSON:
   - Reads target Unicode codepoints for each of the 4 shrink schemes
   - Groups by source MJ code

### Data Structure Construction

1. **`build_reverse_mappings()`**: Builds Unicode-to-JIS reverse lookup:
   - Sorts all mappings by primary Unicode codepoint
   - Groups contiguous codepoints into ranges (`URangeToJISMapping`), splitting at gaps >= `gap_thr` (default 256)
   - Separately collects multi-codepoint sequences into `Outer` groups for the state machine

2. **`build_digested_shrink_mappings()`**: Linearizes MJ shrink mappings:
   - Creates a dense array indexed by MJ code
   - Fills gaps with empty tuples
   - Tracks per-scheme maximum array lengths

3. **`build_chunked_mj_mappings()`**: Builds Unicode-to-MJ reverse lookup:
   - Groups all MJ mappings by Unicode codepoint
   - Chunks contiguous ranges, splitting at gaps >= 64
   - Returns `URangeToMJMappings` list + max mapping set size

### Template Rendering

Uses Jinja2 to render the C header from `code_template`. The template generates:

- `JISCharacterClass` enum
- `ShrinkingTransliterationMapping` struct and the `tx_mappings[]` array (2 * 94 * 94 entries)
- Per-range `uint16_t` arrays for Unicode-to-JIS lookup
- `URangeToJISMapping` array for binary search
- `sm_uni_to_jis_mapping()` function: a C switch-based state machine for multi-codepoint Unicode sequences
- MJ-related structs and arrays (`MJMapping`, `MJMappingSet`, `URangeToMJMappings`, `MJShrinkMappingUnicodeSet`)

## Cython Extension (`_jntajis.pyx`)

### Compiler Directives

```cython
# cython: language_level=3, cdivision=True, boundscheck=False, wraparound=False, embedsignature=True
```

All safety checks are disabled for performance. `embedsignature=True` embeds Python signatures in docstrings.

### Core Internal Types

- **`JNTAJISIncrementalEncoder`**: Struct holding encoder state:
  - `encoding`: Python string (ref-counted) for error reporting
  - `replacement`: Fallback JIS code (0xFFFF = no replacement)
  - `put_jis`: Function pointer selecting the output strategy
  - `la[32]`/`lal`: Lookahead buffer for multi-codepoint sequences
  - `shift_state`/`state`: State machine state

- **`JNTAJISIncrementalEncoderContext`**: Per-call context wrapping the encoder + `_PyBytesWriter` for output construction

- **`JNTAJISShrinkingTransliteratorContext`**: Per-call context for `jnta_shrink_translit`, using `_PyUnicodeWriter` for output

- **`MJShrinkCandidates`**: Manages cartesian product enumeration for `mj_shrink_candidates`

### Encoding Flow (`jnta_encode` / `IncrementalEncoder.encode`)

1. Initialize `_PyBytesWriter` with estimated size (2 * input length)
2. For each Unicode codepoint in input:
   a. Feed to `sm_uni_to_jis_mapping()` state machine
   b. If state machine returns a JIS code (state == -1): call `put_jis` function pointer
   c. If state machine is still consuming (state > 0): buffer in lookahead
   d. If state machine returns to state 0 with buffered chars: flush lookahead via reverse table lookup
3. On flush: flush remaining lookahead, emit shift-out if in SISO mode
4. Finalize bytes writer

### Output Strategies (`put_jis` function pointers)

| Function | ConversionMode | Behavior |
|----------|---------------|----------|
| `jis_put_siso` | SISO | Emits SI/SO escape bytes for plane switching + 2-byte JIS |
| `jis_put_men_1` | MEN1 | Only allows plane 1; rejects plane 2 characters |
| `jis_put_jisx0208` | JISX0208 | Only allows level 1/2 kanji and JIS X 0208 non-kanji |
| `jis_put_jisx0208_translit` | JISX0208_TRANSLIT | Like JISX0208, but falls back to `tx_jis[]`/`tx_us[]` transliteration for non-0208 chars |

### Decoding Flow (`jnta_decode`)

1. Initialize `_PyUnicodeWriter`
2. Parse byte pairs as JIS row+column codes
3. Handle SI (0x0E) / SO (0x0F) shift bytes in SISO mode
4. Look up `tx_mappings[jis]` to get Unicode codepoint(s)
5. Write 1 or 2 Unicode codepoints per JIS code

### JNTA Shrink Transliteration (`jnta_shrink_translit`)

1. Initialize `_PyUnicodeWriter`
2. For each Unicode codepoint: use `sm_uni_to_jis_mapping()` to find JIS code
3. If the JIS code maps to a level 3/4 or non-kanji-extended character with a transliteration entry: output the transliterated form (`tx_us[]`)
4. Otherwise: output the original Unicode codepoint(s) from `us[]`
5. If no mapping found: use replacement string or passthrough

### MJ Shrink Candidates (`mj_shrink_candidates`)

This is the most complex function. It:

1. Allocates per-character candidate arrays (`UIVSPair[20]` per position)
2. For each input character (possibly with trailing IVS):
   a. Look up `urange_to_mj_mappings` to find candidate `MJMapping` entries
   b. If IVS present: filter to exact IVS match
   c. If no IVS: collect all non-IVS variants
   d. For each matching MJ code, look up `mj_shrink_mappings` and collect target Unicode codepoints per selected scheme (combo bitmask)
   e. Also include the original Unicode variants from the MJ mapping itself
   f. If no candidates: keep the original character
3. Enumerate the cartesian product of per-character candidates (up to `limit`) using carry-based iteration
4. Build result strings using `_PyUnicodeWriter`

### Binary Search Pattern

Both `lookup_rev_table()` and `lookup_mj_mapping_table()` use the same pattern:
- Binary search over sorted range arrays
- Each range has `start`, `end`, and a pointer to a dense sub-array
- Index into sub-array as `array[u - start]`

### Unicode String Internals Access

The extension directly uses CPython internal APIs for zero-copy string access:
- `PyUnicode_KIND()`: Get the internal storage width (1/2/4 byte)
- `PyUnicode_DATA()`: Get raw buffer pointer
- `PyUnicode_READ()`: Read a codepoint at an index
- `_PyUnicodeWriter` / `_PyBytesWriter`: Internal buffer builders that handle memory allocation and string compaction

This makes the code CPython-specific and incompatible with other Python implementations.

## xlsx_parser Implementation

### xmlutils.py - XML Framework

The framework builds a hierarchical SAX handler system:

- **`Handlers`** (ABC): Defines `start_element()`, `end_element()`, `cdata()` -- each returns `Optional[Handlers]` to signal handler switching
- **`HandlersBase`**: Concrete base with `outer` (parent handler), `parser` ref, `path` tuple for error reporting, and `next()` for creating child handlers
- **`HandlerShim`**: Adapts the handler-switching protocol to expat's flat callback interface; stores the current handler and swaps it when a method returns non-None
- **`wrap_start_element_handler`**: Decorator that splits `namespace\nlocal_name` and converts attlist to `OrderedDict`
- **`read_xml_incremental()`**: Drives expat parsing in 4KB chunks, yielding events from a `pull_events` callback between chunks

### parser.py - XLSX Parser

Layered handler hierarchy for each XML document:

**Shared strings** (`xl/sharedStrings.xml`):
- Level 0 (`SharedStringsReader_0`): Expects `<sst>`
- Level 1 (`SharedStringsReader_1`): Iterates `<si>` elements
- Level 2 (`SharedStringsReader_2`): Extracts text from `<t>` within `<si>`

**Worksheet** (`xl/worksheets/sheetN.xml`):
- Level 0 (`WorksheetReader_0`): Expects `<worksheet>`
- Level 1 (`WorksheetReader_1`): Handles `<dimension>` and `<sheetData>`
- Level 2 (`WorksheetReader_2`): Iterates `<row>` elements
- Level 3 (`WorksheetReader_3`): Iterates `<c>` (cell) elements within a row
- Level 4 (`WorksheetReader_4`): Extracts `<v>` (value) or `<f>` (formula) content

**`StreamingWorksheetReader`**: Resolves shared string references (`t="s"`) and pads sparse rows into dense arrays based on cell references (e.g. "A1", "C3").

**`ReadonlyWorkbook`/`ReadonlyWorksheet`**: Top-level API wrapping zipfile access with lazy shared string loading and incremental row iteration.

## Python API Layer (`__init__.py`)

### Enums

- **`ConversionMode`** (`IntEnum`): SISO=0, MEN1=1, JISX0208=2, JISX0208_TRANSLIT=3
- **`MJShrinkScheme`** (`IntEnum`): Four MJ shrink scheme identifiers (0-3)
- **`MJShrinkSchemeCombo`** (`IntFlag`): Bitmask flags (1, 2, 4, 8) for combining MJ shrink schemes

The Cython extension symbols are imported with a `try/except ImportError` guard so the package can be imported even when the native extension is not built (e.g. for documentation generation).

## Build System

### setup.py / setup.cfg

- Uses `setuptools-scm` for version management (from git tags matching `v*`)
- Declares a single Cython extension: `jntajis._jntajis` from `src/jntajis/_jntajis.pyx`
- Requires Cython >= 0.29 at build time
- No runtime dependencies

### Makefile

Defines the data pipeline with proper dependency tracking:

```
_jntajis.h <-- gen.py + jissyukutaimap1_0_0.xlsx + mji.00601.xlsx + MJShrinkMap.1.2.0.json
jissyukutaimap1_0_0.xlsx <-- syukutaimap1_0_0.zip (curl from NTA)
mji.00601.xlsx <-- mji.00601-xlsx.zip (curl from CITPC)
MJShrinkMap.1.2.0.json <-- MJShrinkMapVer.1.2.0.zip (curl from CITPC)
```

### CI/CD

- Lint + test runs on every PR and push to main
- Wheel builds only on tag push (`v*`)
- Wheels built via `cibuildwheel` on: Ubuntu 20.04, Windows 2019, macOS 11/12/13
- PyPy wheels are skipped (`CIBW_SKIP: pp*`)

## Testing

Two test modules using pytest:

- **`test_encoder.py`**: Tests `jnta_encode()` and `IncrementalEncoder` across all `ConversionMode` values. Covers:
  - Unmapped character encoding errors
  - Single and multi-codepoint sequences (e.g. katakana with combining marks)
  - Transliteration fallback (JISX0208_TRANSLIT mode)
  - Incremental encoding with flush behavior
  - SISO mode with plane switching
  - Supplementary plane characters

- **`test_mj_translit.py`**: Tests `mj_shrink_candidates()` with various:
  - Characters with/without IVS
  - Different shrink scheme combinations
  - Characters with multiple shrink candidates
  - Supplementary plane characters (e.g. U+2AC2A)
