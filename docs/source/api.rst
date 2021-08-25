.. py:module:: jntajis

------------------------------------
JNTA converter functions and classes 
------------------------------------

.. py:class:: ConversionMode

    Specifies the encoding conversion mode.

    .. py:attribute:: SISO

        Instructs it to encode the given string into JIS X 0213 with the ISO 2022 escape sequences SI (``\x0e``) and SO (``\x0f``) for the extended plane selection.

    .. py:attribute:: MEN1

        Instructs it to encode the given string into JIS X 0213 characters designated in the primary plane, which would theoretically contain JIS X 0208 level 1 and 2 characters.  Characters belonging to the extended plane will result in conversion failure.

    .. py:attribute:: JISX0208

        Instructs it to encode the given string into JIS X 0208 level 1 and 2 characters.  Non-0208 characters will result in conversion failure.

    .. py:attribute:: JISX0208_TRANSLIT

        Instructs it to encode the given string into JIS X 0208 level 1 and 2 characters.  Non-0208 characters will be tried the transliteration against.

.. py:function:: jnta_encode(encoding, in_, conv_mode)

    Encode a given Unicode string into JIS X 0208:1997 / JIS X 0213:2012.

    :param str encoding: The encoding name that is to appear in ``UnicodeEncodeError``.
    :param str in_: The string to encode.
    :param int conv_mode: The conversion mode. For the possible values, refer to :py:class:`ConversionMode`.
    :return: The encoded JIS character sequence.

.. py:function:: jnta_decode(encoding, in_)

    Decode a given JIS character sequence into a Unicode string.

    :param str encoding: The encoding name that is to appear in ``UnicodeDecodeError``.
    :param bytes in_: The encoded JIS characters.
    :return: The decoded Unicode string.

.. py:class:: IncrementalEncoder(encoding, conv_mode)

    An ``IncrementalEncoder`` implementation.

    For the description of each method, please see the `Python's codec documentation <https://docs.python.org/3/library/codecs.html#codecs.IncrementalEncoder>`_.

    :param str encoding: The encoding name that is to appear in ``UnicodeEncodeError``.
    :param int conv_mode: The conversion mode. For the possible values, refer to :py:class:`ConversionMode`.

    .. py:method:: encode(in_, final)

    .. py:method:: reset()

    .. py:method:: getstate()

    .. py:method:: setstate(state)


-------------------------
Transliteration functions
-------------------------

Transliteration based on the MJ character table and MJ shrink conversion map
----------------------------------------------------------------------------

The MJ character table (*MJ文字一覧表*) defines a vast set of Kanji (*漢字*) characters used in information processing of Japanese texts initially developed by Information-technology Promotion Agency.

The MJ shrink conversion map (*MJ縮退マップ*) was also developed alongside for the sake of interoperability between MJ-aware systems and systems based on Unicode, which is used to transliterate complex, less-frequently-used character variants to commonly-used, more-used ones.

.. py:class:: MJShrinkSchemeCombo

    Stores constants that specify the transliteration scheme.

    .. py:attribute:: JIS_INCORPORATION_UCS_UNIFICATION_RULE

        Instructs it to transliterate the given characters according to JIS incorporation and UCS unification rule (a.k.a. *JIS包摂規準・UCS統合規則*) if applicable.

    .. py:attribute:: INFERENCE_BY_READING_AND_GLYPH

        Instructs it to transliterate the given characters according to the CITPC-defined rule based on analogy from readings and glyphs of characters (*読み・字形による類推*.)

    .. py:attribute:: MOJ_NOTICE_582

        Instructs it to transliterate the given characters according to the appendix table proposed in Japan Ministry of Justice (MOJ) notice no. 582 (*法務省告示582号別表第四*.)

    .. py:attribute:: MOJ_FAMILY_REGISTER_ACT_RELATED_NOTICE

        Instructs it to transliterate the given characters according to the Family Register Act (戸籍法) and related MOJ notices (*法務省戸籍法関連通達・通知*.)

.. py:function:: mj_shrink_candidates(in_, combo)

    :param str in_: The string to transliterate.
    :param int combo: The transliteration scheme to use. Specify any combination of the members in :py:class:`MJShrinkSchemeCombo`.
    :return: The list of possible transliteration forms built from the cartesian product of candidates for each character.


Transliteration based on NTA shrink mappings
--------------------------------------------

.. py:function:: jnta_shrink_translit(in_, replacement="\ufffe", passthrough=False)

    Transliterate a Unicode string according to the NTA shrink mappings.

    :param str in_: The string to transliterate.
    :param str replacement: The characters that will be placed when the transliteration is not feasible.
    :param bool passthrough: Instructs the transliterator to put the input character occurrence as is when the character does not exist in the mappings, instead of placing the replacement characters.
    :return: The transliterated characters.
