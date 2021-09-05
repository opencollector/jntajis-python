import click
import enum
import json
import re
import typing
import jinja2

from .xlsx_parser import read_xlsx


invalid_unicode = 0x7FFFFFFF

memo_regexp = re.compile("類似字形([uU]+[0-9a-fA-F]+)は本文字に変換する。")


class JISCharacterClass(enum.IntEnum):
    RESERVED = 0
    KANJI_LEVEL_1 = 1
    KANJI_LEVEL_2 = 2
    KANJI_LEVEL_3 = 3
    KANJI_LEVEL_4 = 4
    JISX0208_NON_KANJI = 9
    JISX0213_NON_KANJI = 11


category_name_to_enum_map: typing.Mapping[str, JISCharacterClass] = {
    "非漢字": JISCharacterClass.JISX0208_NON_KANJI,
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
    uint32_t start:24, end:24;
    const uint16_t *jis;
} URangeToJISMapping;

static const ShrinkingTransliterationMapping tx_mappings[2 * 94 * 94] = {
    {%- for m in tx_mappings %}
    {{ "{" }}
        {{m.jis}},
        {{"{"}}{% for e in m.us|iter_pad(2, "-1") %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
        {{"{"}}{% for e in m.sus|iter_pad(2, "-1") %}{% if not loop.first %}, {% endif %}{{ e }}{% endfor %}},
        JISCharacterClass_{{ m.class_.name }},
        {{ m.tx_jis|length }},
        {{"{"}}{% for e in m.tx_jis %}{% if not loop.first %}, {% endif %}{{ e }}{% else %}0{% endfor %}},
        {{"{"}}{% for e in m.tx_us %}{% if not loop.first %}, {% endif %}{{ e }}{% else %}0{% endfor %}}
    }{% if not loop.last %},{% endif %}
    {%- endfor %}
};

{% for m in uni_range_to_jis_mappings %}
static const uint16_t jis_urange_{{ "%06x"|format(m.start) }}_{{ "%06x"|format(m.end) }}[{{ m.jis|length }}] = {
    {%- for e in m.jis %}
    {{ e }}{% if not loop.last %},{% endif %}
    {%- endfor %}
};
{%- endfor %}

static const URangeToJISMapping urange_to_jis_mappings[] = {
    {%- for m in uni_range_to_jis_mappings %}
    {{ "{" }}{{ m.start }}, {{ m.end }}, jis_urange_{{ "%06x"|format(m.start) }}_{{ "%06x"|format(m.end) }}}{% if not loop.last %},{% endif %}
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

typedef enum MJShrinkScheme {
{%- for x in MJShrinkScheme %}
    JISCharacterClass_{{ x.name }} = {{ x.value }}{% if not loop.last %},{% endif %}
{%- endfor %}
} MJShrinkScheme;

typedef struct UIVSPair {
    uint32_t u:22;
    unsigned int v:1;
    unsigned int sv:1;
    uint8_t s;
} UIVSPair;

typedef struct MJMapping {
    uint32_t mj:24;
    UIVSPair v[{{ max_variants + 1 }}];
} MJMapping;

typedef struct MJMappingSet {
    size_t l:8;
    MJMapping ms[{{ max_mss }}];
} MJMappingSet;

typedef struct URangeToMJMappings {
    uint32_t start:24, end:24;
    const MJMappingSet* mss;
} URangeToMJMappings;

typedef struct MJShrinkMappingUnicodeSet {
{%- for x in MJShrinkScheme %}
    uint32_t _{{ x|int }}[{{ digested_shrink_mappings.max_lens[x] }}];
{%- endfor %}
} MJShrinkMappingUnicodeSet;

{% for cm in chunked_mj_mappings %}
static const MJMappingSet chunked_mj_mappings_{{ "%06x"|format(cm.start) }}_{{ "%06x"|format(cm.end) }}[{{ cm.mss|length }}] = {
    {%- for ms in cm.mss %}
    {{ "{" -}}
        {{- ms|length -}}, {{ "{" -}}
            {%- for m in ms -%}
            {{ "{" }}{{ m.mj }}, {{"{"}}
                {%- for v in m.v -%}
                    {{- "{" }}{{ v.u }}, 1, {{ "1" if v.s >= 0 else "0" }}, {{ v.s if v.s >= 0 else 0 }}{{ "}" }}{% if not loop.last %},{% endif %}
                {%- endfor -%}{{ ", {0, 0, 0, 0}}}" }}{% if not loop.last %},{% endif %}
            {%- else -%}
            {-1, {{ "{{0, 0, 0, 0}}}" -}}
            {%- endfor -%}
        {{- "}" -}}
    {{- "}" -}}{% if not loop.last %},{% endif -%}
    {%- endfor %}
};
{% endfor %}
static const URangeToMJMappings urange_to_mj_mappings[{{ chunked_mj_mappings|length }}] = {
{%- for cm in chunked_mj_mappings %}
    {{ "{" }}{{ cm.start }}, {{ cm.end }}, chunked_mj_mappings_{{ "%06x"|format(cm.start) }}_{{ "%06x"|format(cm.end) }}}{% if not loop.last %},{% endif %}
{%- endfor %}
};

static const MJShrinkMappingUnicodeSet mj_shrink_mappings[{{ digested_shrink_mappings.mje + 1 }}] = {
    {%- for sms in digested_shrink_mappings.smss %}
    {{ "{" }}
        {%- for us in sms %}
        {{ "{" }}{% for u in us|iter_pad(digested_shrink_mappings.max_lens[loop.index0], "-1") %}{{u}}{% if not loop.last %},{% endif %}{%- endfor %}}{% if not loop.last %},{% endif %}
        {%- endfor %}
    }{% if not loop.last %},{% endif %}
    {%- endfor %}
};
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

    return (men - 1) * 94 * 94 + (ku - 1) * 94 + (ten - 1)


uni_repr_regexp = re.compile(r"[uU]\+([0-9a-fA-F]+)$")


def parse_uni_repr(v: str) -> int:
    try:
        m = uni_repr_regexp.match(v)
        if m is None:
            raise ValueError()
        ucp = int(m.group(1), 16)
    except ValueError:
        raise ValueError(f"invalid unicode repr: {v}")

    if ucp < 0 or ucp > 0x10FFFF:
        raise ValueError(f"invalid unicode code point: {ucp:08x}")

    return ucp


def parse_uni_seq_repr(v: str) -> typing.Tuple[int, ...]:
    return tuple(parse_uni_repr(c) for c in v.split())


def parse_underscore_delimited_uni_hex_repr(v: str) -> typing.Tuple[int, ...]:
    return tuple(int(c, 16) for c in v.split("_"))


def take_until_empty(
    f: typing.Callable[[str], int], v: typing.Iterable[str]
) -> typing.Iterator[int]:
    for c in v:
        if not c:
            break
        yield f(c)


class InvalidFormatError(Exception):
    @property
    def message(self):
        return self.args[0]


def none_as_empty(v: typing.Optional[str]) -> str:
    if v is None:
        return ""
    else:
        return v


def read_jnta_excel_file(f: str) -> typing.Sequence[ShrinkingTransliterationMapping]:
    mappings: typing.List[ShrinkingTransliterationMapping] = []

    wb = read_xlsx(f)

    ws = wb.get_worksheet_by_index(1)
    ri = ws.iter_rows()

    try:
        row = next(ri)
    except StopIteration:
        raise InvalidFormatError("too few rows")

    # assert if it is formatted in the expected manner
    if (
        row[0] != "変換元の文字（JISX0213：1-4水）"
        or row[4] != "コード変換（1対1変換）"
        or row[7] != "文字列変換（追加非漢字や、1対ｎの文字変換を行う）"
        or row[16] != "備考"
    ):
        raise InvalidFormatError(
            "a column of the first row does not match to the expected values"
        )

    try:
        row = next(ri)
    except StopIteration:
        raise InvalidFormatError("too few rows")
    if (
        row[0] != "面区点コード"
        or row[1] != "Unicode"
        or row[2] != "字形"
        or row[3] != "JIS区分"
        or row[4] != "面区点コード"
        or row[5] != "Unicode"
        or row[6] != "字形"
        or row[7] != "面区点コード①"
        or row[8] != "面区点コード②"
        or row[9] != "面区点コード③"
        or row[10] != "面区点コード④"
        or row[11] != "Unicode①"
        or row[12] != "Unicode②"
        or row[13] != "Unicode③"
        or row[14] != "Unicode④"
        or row[15] != "字形"
    ):
        raise InvalidFormatError(
            "a column of the second row does not match to the expected values"
        )

    lj = -1
    for ro, row in enumerate(ri):
        if not row[0]:
            break

        _row = [none_as_empty(c) for c in row]

        class_ = category_name_to_enum_map.get(_row[3])

        if class_ is None:
            raise InvalidFormatError(f"unknown category name: {_row[3]}")

        try:
            jis = parse_men_ku_ten_repr(_row[0])
        except ValueError as e:
            raise InvalidFormatError(
                f"failed to parse men-ku-ten at row {ro + 2}"
            ) from e

        us: typing.Tuple[int, ...]
        try:
            us = parse_uni_seq_repr(_row[1])
            if len(us) > 2:
                raise ValueError()
        except ValueError:
            raise InvalidFormatError(f"failed to parse rune at row {ro + 2}")

        sus: typing.Tuple[int, ...] = ()

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

        if _row[4]:
            if not _row[5]:
                raise InvalidFormatError(
                    f"non-empty men-ku-ten code followed by empty Unicode at row {ro + 2}"
                )

            try:
                tx_jis = (parse_men_ku_ten_repr(_row[4]),)
            except ValueError as e:
                raise InvalidFormatError(
                    f"failed to parse men-ku-ten at row {ro + 2}"
                ) from e

            try:
                tx_us = (parse_uni_repr(_row[5]),)
            except ValueError:
                raise InvalidFormatError(f"failed to parse rune at row {ro + 2}")
        elif _row[7]:
            if not _row[11]:
                raise InvalidFormatError(
                    f"empty single-mapping rune followed by empty runes at row {ro + 2}"
                )
            try:
                tx_jis = tuple(take_until_empty(parse_men_ku_ten_repr, _row[7:11]))
            except ValueError as e:
                raise InvalidFormatError(
                    f"failed to parse men-ku-ten at row {ro + 2}"
                ) from e
            try:
                tx_us = tuple(take_until_empty(parse_uni_repr, _row[11:15]))
            except ValueError as e:
                raise InvalidFormatError(f"failed to parse rune at row {ro + 2}") from e

            if len(tx_jis) != len(tx_us):
                raise InvalidFormatError(
                    f"number of characters for the transliteration form does not agree between JIS and Unicode at row {ro + 2}"
                )

        if _row[16]:
            m = memo_regexp.match(_row[16])
            if m is not None:
                try:
                    sus = (parse_uni_repr(m.group(1)),)
                except ValueError as e:

                    raise InvalidFormatError(
                        f"failed to parse rune in memo ({_row[16]}) at row {ro + 2}"
                    ) from e

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


MJ_FIELDS = [
    "図形",
    "font",
    "MJ文字図形名",
    "対応するUCS",
    "実装したUCS",
    "実装したMoji_JohoコレクションIVS",
    "実装したSVS",
    "戸籍統一文字番号",
    "住基ネット統一文字コード",
    "入管正字コード",
    "入管外字コード",
    "漢字施策",
    "対応する互換漢字",
    "X0213",
    "X0213 包摂連番",
    "X0213 包摂区分",
    "X0212",
    "MJ文字図形バージョン",
    "登記統一文字番号(参考)",
    "部首1(参考)",
    "内画数1(参考)",
    "部首2(参考)",
    "内画数2(参考)",
    "部首3(参考)",
    "内画数3(参考)",
    "部首4(参考)",
    "内画数4(参考)",
    "総画数(参考)",
    "読み(参考)",
    "大漢和",
    "日本語漢字辞典",
    "新大字典",
    "大字源",
    "大漢語林",
    "更新履歴",
    "備考",
]


class UIVSPair(typing.NamedTuple):
    u: int
    s: int


class MJMapping(typing.NamedTuple):
    mj: int
    v: typing.Tuple[UIVSPair, ...]


mj_repr_regexp = re.compile(r"MJ([0-9]+)$")


def parse_mj_repr(v: str) -> int:
    try:
        m = mj_repr_regexp.match(v)
        if m is None:
            raise ValueError()
        return int(m.group(1))
    except ValueError:
        raise ValueError(f"invalid MJ repr: {v}")


def resolve_ivs_no(n: int) -> int:
    # VS1 to VS16
    if n >= 0xFE00 and n < 0xFE10:
        return n - 0xFE00
    # VS17 to VS256
    if n >= 0xE0100 and n < 0xE01F0:
        return n - 0xE00F0
    raise ValueError(f"U+{n:06x} is not an IVS")


def read_mj_excel_file(f: str) -> typing.Tuple[typing.Sequence[MJMapping], int]:
    mappings: typing.List[MJMapping] = []

    wb = read_xlsx(f)
    ws = wb.get_worksheet_by_index(1)
    ri = ws.iter_rows()

    try:
        row = next(ri)
    except StopIteration:
        raise InvalidFormatError("too few rows")

    # assert if it is formatted in the expected manner
    if not all(c == f for c, f in zip(row, MJ_FIELDS)):
        raise InvalidFormatError(
            "a column of the first row does not match to the expected values"
        )

    max_variants = 0

    for row in ri:
        if not row[2]:
            continue
        mj = parse_mj_repr(none_as_empty(row[2]))
        if not row[3]:
            continue
        uivps: typing.Set[UIVSPair] = set()
        u = parse_uni_repr(none_as_empty(row[3]))
        uivps.add(UIVSPair(u, -1))
        if row[4]:
            iu = parse_uni_repr(none_as_empty(row[4]))
            uivps.add(UIVSPair(iu, -1))
        if row[5]:
            useqs = none_as_empty(row[5]).split(";")
            for r in useqs:
                us = parse_underscore_delimited_uni_hex_repr(r)
                assert len(us) == 2
                ivn = resolve_ivs_no(us[1])
                uivps.add(
                    UIVSPair(us[0], ivn),
                )
        if row[6]:
            useqs = none_as_empty(row[6]).split(";")
            for r in useqs:
                us = parse_underscore_delimited_uni_hex_repr(r)
                assert len(us) == 2
                ivn = resolve_ivs_no(us[1])
                uivps.add(
                    UIVSPair(us[0], ivn),
                )
        max_variants = max(max_variants, len(uivps))
        mappings.append(
            MJMapping(
                mj=mj,
                v=tuple(sorted(uivps, key=lambda uivp: (uivp.u, uivp.s))),
            ),
        )

    return (mappings, max_variants)


MJShrinkMappingUnicodeSet = typing.Tuple[
    typing.Sequence[int],
    typing.Sequence[int],
    typing.Sequence[int],
    typing.Sequence[int],
]


class MJShrinkMapping(typing.NamedTuple):
    src_mj: int
    us: MJShrinkMappingUnicodeSet


class MJShrinkScheme(enum.IntEnum):
    JIS_INCORPORATION_UCS_UNIFICATION_RULE = 0
    INFERENCE_BY_READING_AND_GLYPH = 1
    MOJ_NOTICE_582 = 2
    MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE = 3


enum_to_shrink_scheme_name_map: typing.Mapping[MJShrinkScheme, str] = {
    MJShrinkScheme.JIS_INCORPORATION_UCS_UNIFICATION_RULE: "JIS包摂規準・UCS統合規則",
    MJShrinkScheme.INFERENCE_BY_READING_AND_GLYPH: "読み・字形による類推",
    MJShrinkScheme.MOJ_NOTICE_582: "法務省告示582号別表第四",
    MJShrinkScheme.MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE: "法務省戸籍法関連通達・通知",
}


def read_mj_shrink_file(src: str) -> typing.Sequence[MJShrinkMapping]:
    data: typing.Dict[str, typing.Any]
    with open(src) as f:
        data = json.load(f)

    content = typing.cast(typing.List[typing.Dict[str, typing.Any]], data["content"])

    mappings: typing.List[MJShrinkMapping] = []
    scheme_names = [enum_to_shrink_scheme_name_map[k] for k in MJShrinkScheme]

    for entry in content:
        us = typing.cast(
            MJShrinkMappingUnicodeSet,
            tuple(
                tuple(
                    set(parse_uni_repr(x["UCS"]) for x in entry[k])
                    if k in entry
                    else ()
                )
                for k in scheme_names
            ),
        )
        if not any(u for u in us):
            continue
        mappings.append(
            MJShrinkMapping(
                src_mj=parse_mj_repr(entry["MJ文字図形名"]),
                us=us,
            ),
        )

    return mappings


T = typing.TypeVar("T")


def iter_pad(
    in_: typing.Union[typing.Iterable[T], typing.Iterator[T]], n: int, p: T
) -> typing.Iterator[T]:
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


def build_reverse_mappings(
    mappings: typing.Sequence[ShrinkingTransliterationMapping],
    gap_thr: int,
) -> typing.Tuple[typing.Sequence[URangeToJISMapping], typing.Sequence[Outer]]:
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

    return rm, rpm


class ShrinkMappings(typing.NamedTuple):
    smss: typing.Sequence[MJShrinkMappingUnicodeSet]
    mje: int
    max_lens: typing.Tuple[int, int, int, int]


def build_digested_shrink_mappings(
    shrink_mappings: typing.Sequence[MJShrinkMapping],
) -> ShrinkMappings:
    smss: typing.List[MJShrinkMappingUnicodeSet] = []
    max_lens: typing.List[int] = [0, 0, 0, 0]

    s = 0
    for sm in sorted(shrink_mappings, key=lambda sm: sm.src_mj):
        for i in range(s, sm.src_mj):
            smss.append(((), (), (), ()))
        else:
            for i, us in enumerate(sm.us):
                max_lens[i] = max(max_lens[i], len(us))
            smss.append(sm.us)
        s = sm.src_mj + 1

    return ShrinkMappings(
        smss=smss,
        mje=s,
        max_lens=typing.cast(typing.Tuple[int, int, int, int], tuple(max_lens)),
    )


class URangeToMJMappings(typing.NamedTuple):
    start: int
    end: int
    mss: typing.Sequence[typing.Sequence[MJMapping]]


def build_chunked_mj_mappings(
    mappings: typing.Sequence[MJMapping],
    gap_thr: int = 64,
) -> typing.Tuple[typing.Sequence[URangeToMJMappings], int]:
    uni_to_mj_mappings = typing.DefaultDict[int, typing.List[MJMapping]](list)

    max_mss = 0
    for m in mappings:
        for uivp in m.v:
            li = uni_to_mj_mappings[uivp.u]
            li.append(m)
            max_mss = max(max_mss, len(li))

    retval: typing.List[URangeToMJMappings] = []
    s = -1
    e = -1
    chunk: typing.List[typing.List[MJMapping]] = []
    for u, ms in sorted(uni_to_mj_mappings.items(), key=lambda pair: pair[0]):
        if u - e >= gap_thr:
            if chunk:
                retval.append(
                    URangeToMJMappings(
                        start=s,
                        end=e,
                        mss=chunk,
                    ),
                )
                chunk = []
            s = u
        else:
            for uu in range(e, u - 1):
                chunk.append([])
        chunk.append(ms)
        e = u
    if chunk:
        retval.append(
            URangeToMJMappings(
                start=s,
                end=e,
                mss=chunk,
            ),
        )
    return (retval, max_mss)


def do_jnta(
    dest: str, src_jnta: str, src_mj: str, src_mj_shrink: str, gap_thr: int = 256
) -> None:
    e = jinja2.Environment()
    e.filters["iter_pad"] = iter_pad
    t = e.from_string(code_template)

    print(f"reading {src_jnta}...")
    mappings = read_jnta_excel_file(src_jnta)

    print(f"reading {src_mj}...")
    mj_mappings, max_variants = read_mj_excel_file(src_mj)

    print(f"reading {src_mj_shrink}...")
    mj_shrink_mappings = read_mj_shrink_file(src_mj_shrink)

    print("building digested shrink mappings from MJ Shrink mappings...")
    digested_shrink_mappings = build_digested_shrink_mappings(mj_shrink_mappings)

    print("chunking MJ mappings...")
    chunked_mj_mappings, max_mss = build_chunked_mj_mappings(mj_mappings)

    print("building reverse mappings...")
    rm, rpm = build_reverse_mappings(mappings, gap_thr)

    gen = t.generate(
        JISCharacterClass=JISCharacterClass,
        tx_mappings=mappings,
        uni_range_to_jis_mappings=rm,
        uni_pairs_to_jis_mappings=rpm,
        MJShrinkScheme=MJShrinkScheme,
        max_variants=max_variants,
        digested_shrink_mappings=digested_shrink_mappings,
        chunked_mj_mappings=chunked_mj_mappings,
        max_mss=max_mss,
    )
    with open(dest, "w") as f:
        for c in gen:
            f.write(c)


@click.command()
@click.argument("dest", required=True)
@click.argument("src_jnta", required=True)
@click.argument("src_mj", required=True)
@click.argument("src_mj_shrink", required=True)
def main(dest, src_jnta, src_mj, src_mj_shrink):
    do_jnta(dest, src_jnta, src_mj, src_mj_shrink)


if __name__ == "__main__":
    main()
