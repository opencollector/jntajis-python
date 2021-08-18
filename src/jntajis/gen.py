import click
import enum
import re
import typing
import jinja2

import openpyxl  # type: ignore


SHRINKING_MAP_SHEET_NAME = "JIS縮退マップ"

invalid_unicode = 0x7fffffff

memo_regexp = re.compile("類似字形([uU]+[0-9a-fA-F]+)は本文字に変換する。")

class JISCharacterClass(enum.IntEnum):
    RESERVED           = 0
    KANJI_LEVEL_1      = 1
    KANJI_LEVEL_2      = 2
    KANJI_LEVEL_3      = 3
    KANJI_LEVEL_4      = 4
    JISX0208_NON_KANJI = 9
    JISX0213_NON_KANJI = 11


category_name_to_enum_map: typing.Mapping[str, JISCharacterClass] = {
    "非漢字":   JISCharacterClass.JISX0208_NON_KANJI,
    "追加非漢字": JISCharacterClass.JISX0213_NON_KANJI,
    "JIS1水": JISCharacterClass.KANJI_LEVEL_1,
    "JIS2水": JISCharacterClass.KANJI_LEVEL_2,
    "JIS3水": JISCharacterClass.KANJI_LEVEL_3,
    "JIS4水": JISCharacterClass.KANJI_LEVEL_4,
}

class ShrinkingTransliterationMapping(typing.NamedTuple):
    jis: int
    """packed men-ku-ten code"""
    us: typing.Tuple[int, ...]
    """corresponding Unicode character"""
    sus: typing.Tuple[int, ...]
    """corresponding Unicode character (secondary)"""
    class_: JISCharacterClass
    """JIS character class"""
    tx_jis: typing.Tuple[int, ...] = ()
    """transliterated form in packed men-ku-ten code"""
    tx_us: typing.Tuple[int, ...] = ()
    """transliterated form in Unicode"""


class URangeToJISMapping(typing.NamedTuple):
    start: int
    end: int
    jis: typing.Sequence[int]


class Outer(typing.NamedTuple):
    u: int
    n: typing.List[ShrinkingTransliterationMapping]


code_template = """#include <stdint.h>
#include <stddef.h>

typedef enum JISCharacterClass {
{%- for x in JISCharacterClass %}
    JISCharacterClass_{{ x.name }} = {{ x.value }}{% if not loop.last %},{% endif %}
{%- endfor %}
} JISCharacterClass;


typedef struct ShrinkingTransliterationMapping {
    uint16_t jis;
    uint32_t us[2];
    uint32_t sus[2];
    JISCharacterClass class_;
    size_t tx_len:8;
    uint16_t tx_jis[4];
    uint32_t tx_us[4];
} ShrinkingTransliterationMapping;

typedef struct URangeToJISMapping {
    uint32_t start, end;
    size_t jis_len:16;
    const uint16_t *jis;
} URangeToJISMapping;

static const ShrinkingTransliterationMapping tx_mappings[2 * 94 * 94] = {
    {%- for m in tx_mappings %}
    {
        {{m.jis}},
        {{"{"}}{% for e in m.us|iter_pad(2, "(uint32_t)-1") %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
        {{"{"}}{% for e in m.sus|iter_pad(2, "(uint32_t)-1") %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
        JISCharacterClass_{{ m.class_.name }},
        {{ m.tx_jis|length }},
        {{"{"}}{% for e in m.tx_jis %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
        {{"{"}}{% for e in m.tx_us %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
    },
    {%- endfor %}
};

{% for m in uni_range_to_jis_mappings %}
static const uint16_t jis_urange_{{ "%06x"|format(m.start) }}_{{ "%06x"|format(m.end) }}[{{ m.jis|length }}] = {
    {%- for e in m.jis %}
    {{e}}{% if not loop.last %},{% endif %}
    {%- endfor %}
};

{%- endfor %}
static const URangeToJISMapping urange_to_jis_mappings[] = {
    {%- for m in uni_range_to_jis_mappings %}
    {{ "{" }}{{ m.start }}, {{ m.end }}, {{ m.jis|length }}, jis_urange_{{ "%06x"|format(m.start) }}_{{ "%06x"|format(m.end) }}}{% if not loop.last %},{% endif %}
    {%- endfor %}
};

typedef struct SMUniToJISTuple {
    int state;
    uint32_t u;
} SMUniToJISTuple;

static uint16_t sm_uni_to_jis_mapping(int *state, uint32_t u)
{
    uint16_t j = 0;
    int _state = *state;
reenter:
    switch (_state) {
    case 0:
        if (u < {{ uni_pairs_to_jis_mappings[0].u }} || u > {{ uni_pairs_to_jis_mappings[-1].u }}) {
            break;
        }
        switch (u) {
        {%- for m in uni_pairs_to_jis_mappings %}
        case {{m.u}}:
            _state = {{ loop.index }};
            break;
        {%- endfor %}
        }
        break;
    {%- for m in uni_pairs_to_jis_mappings %}
    case {{ loop.index }}:
        switch (u) {
        {%- for e in m.n %}
        case {{ e.us[1] }}:
            j = {{ e.jis }};
            _state = -1;
            break;
        {%- endfor %}
        default:
            _state = 0;
            goto reenter;
        }
        break;
    {%- endfor %}
    }
    *state = _state;
    return j;
}
"""


men_ku_ten_regexp = re.compile(r"(\d+)-(\d+)-(\d+)$")

def parse_men_ku_ten_repr(v: str) -> int:
    m = men_ku_ten_regexp.match(v)
    if m is None:
        raise ValueError(f"invalid men-ku-ten string: {v}")

    men = int(m.group(1))
    ku = int(m.group(2))
    ten = int(m.group(3))

    if men < 1 or men > 2:
        raise ValueError(f"invalid men value: {men}")

    if ku < 1 or ku > 94:
        raise ValueError(f"invalid ku value: {ku}")

    if ten < 1 or ten > 94:
        raise ValueError(f"invalid ten value: {ten}")

    return (men-1)*94*94 + (ku-1)*94 + (ten - 1)


uni_rexpr_regexp = re.compile(r"u\+([0-9a-fA-F]+)$")


def parse_uni_repr(v: str) -> int:
    try:
        m = uni_rexpr_regexp.match(v)
        if m is None:
            raise ValueError()
        ucp = int(m.group(1), 16)
    except ValueError:
        raise ValueError(f"invalid unicode repr: {v}")


    if ucp < 0 or ucp > 0x10ffff:
        raise ValueError(f"invalid unicode code point: {ucp:08x}")

    return ucp


def parse_uni_seq_repr(v: str) -> typing.Tuple[int, ...]:
    return tuple(parse_uni_repr(c) for c in v.split())


def take_until_empty(f: typing.Callable[[str], int], v: typing.Iterable[str]) -> typing.Iterator[int]:
    for c in v:
        if not c:
            break
        yield f(c)


class InvalidFormatError(Exception):
    @property
    def message(self):
        return self.args[0]


def read_excel_file(f: str) -> typing.Sequence[ShrinkingTransliterationMapping]:
    mappings: typing.List[ShrinkingTransliterationMapping] = []

    wb = openpyxl.load_workbook(f)

    ws = wb[SHRINKING_MAP_SHEET_NAME]
    rows = [
        [c.value for c in row]
        for row in ws.rows
    ]

    # assert if it is formatted in the expected manner
    if (
        rows[0][0] != "変換元の文字（JISX0213：1-4水）" or
        rows[0][4] != "コード変換（1対1変換）" or
        rows[0][7] != "文字列変換（追加非漢字や、1対ｎの文字変換を行う）" or
        rows[0][16] != "備考"
    ):
        raise InvalidFormatError("a column of the first row does not match to the expected values")

    if (
        rows[1][0] != "面区点コード" or
        rows[1][1] != "Unicode" or
        rows[1][2] != "字形" or
        rows[1][3] != "JIS区分" or
        rows[1][4] != "面区点コード" or
        rows[1][5] != "Unicode" or
        rows[1][6] != "字形" or
        rows[1][7] != "面区点コード①" or
        rows[1][8] != "面区点コード②" or
        rows[1][9] != "面区点コード③" or
        rows[1][10] != "面区点コード④" or
        rows[1][11] != "Unicode①" or
        rows[1][12] != "Unicode②" or
        rows[1][13] != "Unicode③" or
        rows[1][14] != "Unicode④" or
        rows[1][15] != "字形"
    ):
        raise InvalidFormatError("a column of the second row does not match to the expected values")

    lj = -1
    for ro, row in enumerate(rows[2:]):
        if not row[0]:
            break

        class_ = category_name_to_enum_map.get(row[3])

        if class_ is None:
            raise InvalidFormatError(f"unknown category name: {row[3]}")

        try:
            jis = parse_men_ku_ten_repr(row[0])
        except ValueError as e:
            raise InvalidFormatError(f"failed to parse men-ku-ten at row {ro + 2}") from e

        us: typing.Tuple[int, ...]
        try:
            us = parse_uni_seq_repr(row[1])
            if len(us) > 2:
                raise ValueError()
        except ValueError as e:
            raise InvalidFormatError(f"failed to parse rune at row {ro + 2}")

        sus: typing.Tuple[int, ...] = ()

        tx_len = 0
        tx_jis: typing.Tuple[int, ...] = ()
        tx_us: typing.Tuple[int, ...] = ()
        if lj + 1 < jis:
            for i in range(lj + 1, jis):
                mappings.append(
                    ShrinkingTransliterationMapping(
                        jis=i,
                        us=us,
                        sus=sus,
                        class_=JISCharacterClass.RESERVED,
                    )
                )

        if row[4]:
            tx_len = 1
            if not row[5]:
                raise InvalidFormatError(f"non-empty men-ku-ten code followed by empty Unicode at row {ro + 2}")

            try:
                tx_jis = (parse_men_ku_ten_repr(row[4]),)
            except ValueError as e:
                raise InvalidFormatError(f"failed to parse men-ku-ten at row {ro + 2}") from e

            try:
                tx_us = (parse_uni_repr(row[5]),)
            except ValueError as e:
                raise InvalidFormatError(f"failed to parse rune at row {ro + 2}")
        elif row[7]:
            if not row[11]:
                raise InvalidFormatError(f"empty single-mapping rune followed by empty runes at row {ro + 2}")
            try:
                tx_jis = tuple(take_until_empty(parse_men_ku_ten_repr, row[7:11]))
            except ValueError as e:
                raise InvalidFormatError(f"failed to parse men-ku-ten at row {ro + 2}") from e
            try:
                tx_us = tuple(take_until_empty(parse_uni_repr, row[11:15]))
            except ValueError as e:
                raise InvalidFormatError(f"failed to parse rune at row {ro + 2}") from e

            if len(tx_jis) != len(tx_us):
                raise InvalidFormatError(f"number of characters for the transliteration form does not agree between JIS and Unicode at row {ro + 2}")

        if row[16]:
            m = memo_regexp.match(row[16])
            if m is not None:
                try:
                    sus = (parse_uni_repr(m.group(1)),)
                except ValueError as e:

                    raise InvalidFormatError(f"failed to parse rune in memo ({row[16]}) at row {ro + 2}") from e

        mappings.append(
            ShrinkingTransliterationMapping(
                jis=jis,
                us=us,
                sus=sus,
                class_=class_,
                tx_jis=tx_jis,
                tx_us=tx_us,
            )
        )
        lj = jis

    return mappings


T = typing.TypeVar("T")

def iter_pad(in_: typing.Union[typing.Iterable[T], typing.Iterator[T]], n: int, p: T) -> typing.Iterator[T]:
    c = 0
    for v in iter(in_):
        if c < n:
            yield v
        else:
            yield p
        c += 1
    while c < n:
        yield p
        c += 1


def do_it(dest: str, src: str, gap_thr: int = 256) -> None:
    e = jinja2.Environment()

    e.filters["iter_pad"] = iter_pad

    t = e.from_string(code_template)
    print(f"reading {src}...")

    mappings = read_excel_file(src)

    print("building reverse mappings...")
    rm: typing.List[URangeToJISMapping] = []
    x: typing.List[ShrinkingTransliterationMapping] = []

    for m in mappings:
        x.append(m)
        if m.sus:
            x.append(m._replace(us=m.sus))

    x.sort(key=lambda v: v.us[0])

    lr: int = -1
    sr: int = -1
    js: typing.List[int] = []
    for m in x:
        if m.class_ == JISCharacterClass.RESERVED:
            continue
        if len(m.us) > 1:
            continue

        r = m.us[0]
        if lr == -1:
            sr = r
        else:
            g = r - lr
            if g >= gap_thr:
                rm.append(URangeToJISMapping(start=sr, end=lr, jis=js))
                js = []
                sr = r
            else:
                for _ in range(1, g):
                    js.append(-1)

        js.append(m.jis)
        lr = r

    if lr != -1:
        rm.append(URangeToJISMapping(start=sr, end=lr, jis=js))

    rpm: typing.List[Outer] = []

    for m in x:
        if m.class_ == JISCharacterClass.RESERVED:
            continue
        if len(m.us) < 2:
            continue
        u = m.us[0]

        for i in range(0, len(rpm)):
            if rpm[i].u == u:
                rpm[i].n.append(m)
                break
        else:
            rpm.append(Outer(u=u, n=[m]))

    gen = t.generate(
        JISCharacterClass=JISCharacterClass,
        tx_mappings=mappings,
        uni_range_to_jis_mappings=rm,
        uni_pairs_to_jis_mappings=rpm,
    )
    with open(dest, "w") as f:
        for c in gen:
            f.write(c)


@click.command()
@click.argument("src", required=True)
@click.argument("dest", required=True)
def main(src, dest):
    do_it(dest, src)


if __name__ == "__main__":
    main()
