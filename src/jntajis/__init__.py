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
    MEN1 = 1
    JISX0208 = 2
    JISX0208_TRANSLIT = 3


class MJShrinkScheme(enum.IntEnum):
    JIS_INCORPORATION_UCS_UNIFICATION_RULE = 0
    INFERENCE_BY_READING_AND_GLYPH = 1
    MOJ_NOTICE_582 = 2
    MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE = 3


class MJShrinkSchemeCombo(enum.IntFlag):
    JIS_INCORPORATION_UCS_UNIFICATION_RULE = 1
    INFERENCE_BY_READING_AND_GLYPH = 2
    MOJ_NOTICE_582 = 4
    MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE = 8
