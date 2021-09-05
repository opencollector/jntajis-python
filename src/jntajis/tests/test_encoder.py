import pytest
import jntajis


@pytest.mark.parametrize(
    ("case",),
    [
        ("\u0000",),
        ("\u309a",),
        ("\u298c6",),
        ("✋",),
    ],
)
def test_encode_jisx0213_unmapped(case):
    with pytest.raises(UnicodeEncodeError):
        jntajis.jnta_encode("jis", case, jntajis.ConversionMode.MEN1)


@pytest.mark.parametrize(
    ("expected", "err", "mode", "input"),
    [
        (
            b"\x21\x24",
            None,
            jntajis.ConversionMode.MEN1,
            "，",
        ),
        (
            b"\x21\x24",
            None,
            jntajis.ConversionMode.JISX0208,
            "，",
        ),
        (
            b"\x21\x24",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "，",
        ),
        (
            b"\x24\x74\x24\x75\x24\x76",
            None,
            jntajis.ConversionMode.MEN1,
            "ゔゕゖ",
        ),
        (
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "ゔゕゖ",
        ),
        (
            b"\x25\x74\x25\x75\x25\x76",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "ゔゕゖ",
        ),
        (
            b"\x28\x41",
            None,
            jntajis.ConversionMode.MEN1,
            "㉑",
        ),
        (
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "㉑",
        ),
        (
            b"\x23\x32\x23\x31",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "㉑",
        ),
        (
            b"\x7e\x7e",
            None,
            jntajis.ConversionMode.MEN1,
            "\u7e6b",
        ),
        (
            b"",
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "\u7e6b",
        ),
        (
            b"\x37\x52",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "\u7e6b",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73\x25\x2f\x25\x6d\x21\x3c\x25\x49\x25\x74\x25\x21\x25\x73\x25\x40\x25\x60",
            None,
            jntajis.ConversionMode.MEN1,
            "ジャンクロードヴァンダム",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73\x25\x2f\x25\x6d\x21\x3c\x25\x49\x25\x74\x25\x21\x25\x73\x25\x40\x25\x60",
            None,
            jntajis.ConversionMode.JISX0208,
            "ジャンクロードヴァンダム",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73\x25\x2f\x25\x6d\x21\x3c\x25\x49\x25\x74\x25\x21\x25\x73\x25\x40\x25\x60",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "ジャンクロードヴァンダム",
        ),
    ],
)
def test_encode_seqs(expected, err, mode, input):
    if err is None:
        assert expected == jntajis.jnta_encode("jis", input, mode)
    else:
        with pytest.raises(UnicodeEncodeError) as e:
            jntajis.jnta_encode("jis", input, mode)
        assert e.value.reason == err


@pytest.mark.parametrize(
    ("expected", "expected_at_flush", "err", "mode", "input"),
    [
        (
            b"\x21\x24",
            b"",
            None,
            jntajis.ConversionMode.MEN1,
            "，",
        ),
        (
            b"\x21\x24",
            b"",
            None,
            jntajis.ConversionMode.JISX0208,
            "，",
        ),
        (
            b"\x21\x24",
            b"",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "，",
        ),
        (
            b"\x24\x74\x24\x75\x24\x76",
            b"",
            None,
            jntajis.ConversionMode.MEN1,
            "ゔゕゖ",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "ゔゕゖ",
        ),
        (
            b"\x25\x74\x25\x75\x25\x76",
            b"",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "ゔゕゖ",
        ),
        (
            b"\x28\x41",
            b"",
            None,
            jntajis.ConversionMode.MEN1,
            "㉑",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "㉑",
        ),
        (
            b"\x23\x32\x23\x31",
            b"",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "㉑",
        ),
        (
            b"\x7e\x7e",
            b"",
            None,
            jntajis.ConversionMode.MEN1,
            "\u7e6b",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "\u7e6b",
        ),
        (
            b"\x37\x52",
            b"",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "\u7e6b",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73",
            b"\x25\x2f",
            None,
            jntajis.ConversionMode.MEN1,
            "ジャンク",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73",
            b"\x25\x2f",
            None,
            jntajis.ConversionMode.JISX0208,
            "ジャンク",
        ),
        (
            b"\x25\x38\x25\x63\x25\x73",
            b"\x25\x2f",
            None,
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "ジャンク",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.MEN1,
            "\U00020089",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208,
            "\U00020089",
        ),
        (
            None,
            None,
            "not convertible to JISX0208",
            jntajis.ConversionMode.JISX0208_TRANSLIT,
            "\U00020089",
        ),
        (
            b"\x0f\x21\x21",
            b"\x0e",
            None,
            jntajis.ConversionMode.SISO,
            "\U00020089",
        ),
    ],
)
def test_incremental_encoder(expected, expected_at_flush, err, mode, input):
    enc = jntajis.IncrementalEncoder("jis", mode)
    if err is None:
        assert enc.encode(input, False) == expected
        assert enc.encode("", True) == expected_at_flush
    else:
        with pytest.raises(UnicodeEncodeError) as e:
            enc.encode(input, True)
        assert e.value.reason == err
