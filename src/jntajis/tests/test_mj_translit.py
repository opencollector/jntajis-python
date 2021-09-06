import pytest
import jntajis


@pytest.mark.parametrize( ("input", "combo", "expected"),
    [
        # 斎
        (
            "\u658e",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u658e"],
        ),
        (
            "\u658e\U000e0102",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u658e"],
        ),
        (
            "\u658e",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u658e"],
        ),
        (
            "\u658e\U000e0102",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u658e"],
        ),
        # 邉
        (
            "\u9089",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u9089"],
        ),
        (
            "\u9089\U000e0102",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u9089\U000e0102"],
        ),
        (
            "\u9089\U000e010f",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u9089"],
        ),
        (
            "\u9089\U000e0109",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u9089\U000e0109"],
        ),
        (
            "\u9089",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u9089"],
        ),
        (
            "\u9089\U000e0102",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u9089\U000e0102"],
        ),
        (
            "\u9089\U000e0109",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u9089\U000e0109"],
        ),
        (
            "\u9089\U000e010f",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u9089"],
        ),
        (
            "\u9089",
            jntajis.MJShrinkSchemeCombo.MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE,
            ["\u8fba", "\u908a", "\u9089"],
        ),
        (
            "\u9089",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE | jntajis.MJShrinkSchemeCombo.MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE,
            ["\u8fba", "\u908a", "\u9089"],
        ),
        # 邊󠄏
        (
            "\u908a",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u908a"],
        ),
        (
            "\u908a\U000e0102",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u908a\U000e0102"],
        ),
        (
            "\u908a\U000e0108",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u908a"],
        ),
        (
            "\u908a\U000e0109",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u908a"],
        ),
        (
            "\u908a",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u908a"],
        ),
        (
            "\u908a\U000e0102",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u908a\U000e0102"],
        ),
        (
            "\u908a\U000e0108",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u908a"],
        ),
        (
            "\u908a\U000e0109",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u908a"],
        ),
        (
            "\u908a",
            jntajis.MJShrinkSchemeCombo.MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE,
            ["\u8fba", "\u908a"],
        ),
        (
            "\u908a",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE | jntajis.MJShrinkSchemeCombo.MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE,
            ["\u8fba", "\u908a"],
        ),
        # 㑐
        (
            "\u3450",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\u3450"],
        ),
        (
            "\u3450",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\u3450"],
        ),
        # あさぼらけ
        (
            "\U0002AC2A",
            jntajis.MJShrinkSchemeCombo.JIS_INCORPORATION_UCS_UNIFICATION_RULE,
            ["\U0002AC2A"],
        ),
        (
            "\U0002AC2A",
            jntajis.MJShrinkSchemeCombo.INFERENCE_BY_READING_AND_GLYPH,
            ["\U0002AC2A"],
        ),
    ],
)
def test_mj_shrink_candidates(input, combo, expected):
    assert jntajis.mj_shrink_candidates(input, combo) == expected
