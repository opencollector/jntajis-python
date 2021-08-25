"""
A fast character conversion and transliteration library based on
the scheme defined for Japan National Tax Agency (国税庁) 's
corporate number (法人番号) system.

This library makes use of the data from the following entities:

* JIS shrink conversion map (国税庁: JIS縮退マップ)

    Published by: National Tax Agency
    Author: unknown
    Source: https://www.houjin-bangou.nta.go.jp/download/
    Copyright / license: public domain? (needs to be clarified.)

* MJ character table (文字情報技術促進協議会: MJ文字一覧表)

    Published by: Character Information Technology Promotion
                  Council (CITPC)
    Author: Information-technology Promotion Agency (IPA)
    Source: https://moji.or.jp/mojikiban/mjlist/
    Copyright / license: CC BY-SA 2.1 JP

* MJ shrink conversion map (文字情報技術促進協議会: MJ縮退マップ)
    Published by: Character Information Technology Promotion
                  Council (CITPC)
    Author: Information-technology Promotion Agency (IPA)
    Source: https://moji.or.jp/mojikiban/map/
    Copyright / license: CC BY-SA 2.1 JP

"""

import enum

try:
    from ._jntajis import (  # noqa: F401
        IncrementalEncoder,
        jnta_encode,
        jnta_decode,
        jnta_shrink_translit,
        mj_shrink_candidates,
        TransliterationError,
    )
except ImportError:
    pass


class ConversionMode(enum.IntEnum):
    SISO = 0
    """
    Instructs the encoder to encode the given string into JIS X 0213 with the
    ISO 2022 escape sequences SI (``\x0e``) and SO (``\x0f``) for the extended
    plane selection.
    """
    MEN1 = 1
    """
    Instructs the encoder to encode the given string into JIS X 0213 characters
    designated in the primary plane, which would theoretically contain JIS X
    0208 level 1 and 2 characters.  Characters belonging to the extended plane
    will result in conversion failure.
    """
    JISX0208 = 2
    """
    Instructs it to encode the given string into JIS X 0208 level 1 and 2
    characters.  Non-0208 characters will result in conversion failure.
    """
    JISX0208_TRANSLIT = 3
    """
    Instructs it to encode the given string into JIS X 0208 level 1 and 2
    characters.  Non-0208 characters will be tried the transliteration against.
    """


class MJShrinkScheme(enum.IntEnum):
    JIS_INCORPORATION_UCS_UNIFICATION_RULE = 0
    INFERENCE_BY_READING_AND_GLYPH = 1
    MOJ_NOTICE_582 = 2
    MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE = 3


class MJShrinkSchemeCombo(enum.IntFlag):
    JIS_INCORPORATION_UCS_UNIFICATION_RULE = 1
    """
    Instructs it to transliterate the given characters according to JIS
    incorporation and UCS unification rule (a.k.a. JIS包摂規準・UCS統合規則)
    if applicable.
    """
    INFERENCE_BY_READING_AND_GLYPH = 2
    """
    Instructs it to transliterate the given characters according to the
    CITPC-defined rule based on analogy from readings and glyphs of characters
    (読み・字形による類推.)
    """
    MOJ_NOTICE_582 = 4
    """
    Instructs it to transliterate the given characters according to the
    appendix table proposed in Japan Ministry of Justice (MOJ) notice no. 582
    (法務省告示582号別表第四.)
    """
    MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE = 8
    """
    Instructs it to transliterate the given characters according to the
    Family Register Act (戸籍法) and related MOJ notices
    (法務省戸籍法関連通達・通知.)
    """
