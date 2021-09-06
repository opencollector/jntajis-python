# cython: language_level=3, cdivision=True, boundscheck=False, wraparound=False, embedsignature=True
from libc.stdio cimport snprintf
from libc.stdlib cimport malloc, calloc, free
from libc.string cimport memcpy
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF

import enum

cdef extern from "_jntajis.h":
    ctypedef unsigned short uint8_t
    ctypedef unsigned short uint16_t
    ctypedef unsigned int uint32_t
    ctypedef enum JISCharacterClass:
        JISCharacterClass_RESERVED
        JISCharacterClass_KANJI_LEVEL_1
        JISCharacterClass_KANJI_LEVEL_2
        JISCharacterClass_KANJI_LEVEL_3
        JISCharacterClass_KANJI_LEVEL_4
        JISCharacterClass_JISX0208_NON_KANJI
        JISCharacterClass_JISX0213_NON_KANJI
    ctypedef struct ShrinkingTransliterationMapping:
        uint16_t jis
        uint32_t[2] us
        uint32_t[2] sus
        JISCharacterClass class_
        size_t tx_len
        uint16_t[4] tx_jis
        uint32_t[4] tx_us
    ctypedef struct URangeToJISMapping:
        uint32_t start, end
        uint16_t* jis
    ctypedef struct SMUniToJISTuple:
        pass
    const ShrinkingTransliterationMapping[] tx_mappings
    const URangeToJISMapping[] urange_to_jis_mappings
    uint16_t sm_uni_to_jis_mapping(int *state, uint32_t u) nogil
    ctypedef struct UIVSPair:
        uint32_t u
        bint v
        bint sv
        uint8_t s
    ctypedef struct MJMapping:
        uint32_t mj
        UIVSPair[4] v
    ctypedef struct MJShrinkMappingUnicodeSet:
        uint32_t[2] _0
        uint32_t[1] _1
        uint32_t[2] _2
        uint32_t[3] _3
    ctypedef struct MJMappingSet:
        size_t l
        MJMapping[64] ms
    ctypedef struct URangeToMJMappings:
        uint32_t start, end
        const MJMappingSet* mss
    const URangeToMJMappings[] urange_to_mj_mappings
    const MJShrinkMappingUnicodeSet[] mj_shrink_mappings


cdef extern from "Python.h":
    uint32_t Py_MAX(uint32_t, uint32_t)

    ctypedef struct _PyUnicodeWriter:
        Py_ssize_t min_length
        int overallocate
    ctypedef int Py_UCS4
    cdef enum PyUnicode_Kind:
        PyUnicode_1BYTE_KIND
        PyUnicode_2BYTE_KIND
        PyUnicode_4BYTE_KIND
    void _PyUnicodeWriter_Init(_PyUnicodeWriter*) nogil
    void _PyUnicodeWriter_Dealloc(_PyUnicodeWriter*) nogil
    void _PyUnicodeWriter_WriteChar(_PyUnicodeWriter*, Py_UCS4) nogil
    void _PyUnicodeWriter_WriteStr(_PyUnicodeWriter*, unicode)
    object _PyUnicodeWriter_Finish(_PyUnicodeWriter*) nogil
    int _PyUnicodeWriter_Prepare(_PyUnicodeWriter*, Py_ssize_t, Py_ssize_t) nogil
    int  _PyUnicodeWriter_PrepareKind(_PyUnicodeWriter*, int) nogil

    PyUnicode_Kind PyUnicode_KIND(object)
    void* PyUnicode_DATA(object) 
    Py_ssize_t PyUnicode_GET_LENGTH(object)
    Py_UCS4 PyUnicode_READ(int, void*, Py_ssize_t)

    ctypedef struct _PyBytesWriter:
        int overallocate
    void _PyBytesWriter_Init(_PyBytesWriter*) nogil
    void _PyBytesWriter_Alloc(_PyBytesWriter*, Py_ssize_t) nogil
    void _PyBytesWriter_Dealloc(_PyBytesWriter*) nogil
    object _PyBytesWriter_Finish(_PyBytesWriter*, void*) nogil
    void* _PyBytesWriter_Prepare(_PyBytesWriter*, void*, Py_ssize_t) nogil
    void* _PyBytesWriter_WriteBytes(_PyBytesWriter*, void*, void*, Py_ssize_t) nogil


ctypedef bint (*jis_put_func)(JNTAJISIncrementalEncoderContext*, uint16_t)


ctypedef struct JNTAJISIncrementalEncoder:
    PyObject* encoding
    uint16_t replacement
    jis_put_func put_jis
    size_t lal
    uint32_t[32] la
    int shift_state
    int state


ctypedef enum JNTAJISError:
    JNTAJISError_Success = 0
    JNTAJISError_MemoryError = 1
    JNTAJISError_AssertionError = 2


ctypedef struct JNTAJISIncrementalEncoderContext:
    JNTAJISIncrementalEncoder* e
    _PyBytesWriter writer
    PyObject* u  # borrow
    PyUnicode_Kind uk
    void* ud
    Py_ssize_t ul
    Py_ssize_t pos
    char* p
    JNTAJISError err


cdef bint lookup_rev_table(uint16_t* pj, uint32_t u) nogil:
    cdef size_t l = sizeof(urange_to_jis_mappings) // sizeof(urange_to_jis_mappings[0])
    cdef size_t s = 0, e = l
    cdef size_t m
    cdef const URangeToJISMapping* mm
    cdef uint16_t jis
    while s < e and e <= l:
        m = (s + e) // 2
        mm = &urange_to_jis_mappings[m]
        if u < mm.start:
            e = m
            continue
        elif u > mm.end:
            s = m + 1
            continue
        if u > mm.end:
            break
        jis = mm.jis[u - mm.start]
        if jis == <uint16_t>-1:
            break
        pj[0] = jis
        return True
    return False


cdef bint jis_put_men_1(JNTAJISIncrementalEncoderContext* ctx, uint16_t c) nogil:
    cdef unsigned int men = c // (94 * 94)
    cdef unsigned int ku = c // 94 % 94
    cdef unsigned int ten = c % 94
    cdef char* p
    if men != 0:
        return False

    p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
    if not p:
        ctx.err = JNTAJISError_MemoryError
        return False
    p[0] = 0x21 +  ku
    p[1] = 0x21 + ten
    p += 2
    ctx.p = p
    return True


cdef bint jis_put_jisx0208(JNTAJISIncrementalEncoderContext* ctx, uint16_t c) nogil:
    if c >= sizeof(tx_mappings) // sizeof(tx_mappings[0]):
        return False
    cdef JISCharacterClass class_ = tx_mappings[c].class_
    cdef char* p
    if (
        class_ == JISCharacterClass_KANJI_LEVEL_1 or
        class_ == JISCharacterClass_KANJI_LEVEL_2 or
        class_ == JISCharacterClass_JISX0208_NON_KANJI
    ):
        p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
        if not p:
            ctx.err = JNTAJISError_MemoryError
            return False
        p[0] = 0x21 + c // 94 % 94
        p[1] = 0x21 + c % 94
        p += 2
        ctx.p = p
        return True
    else:
        return False


cdef bint jis_put_jisx0208_translit(JNTAJISIncrementalEncoderContext* ctx, uint16_t c) nogil:
    if c >= sizeof(tx_mappings) // sizeof(tx_mappings[0]):
        return False
    cdef const ShrinkingTransliterationMapping* m = &tx_mappings[c]
    cdef JISCharacterClass class_ = m.class_
    cdef char* p
    if (
        class_ == JISCharacterClass_KANJI_LEVEL_1 or
        class_ == JISCharacterClass_KANJI_LEVEL_2 or
        class_ == JISCharacterClass_JISX0208_NON_KANJI
    ):
        p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
        if not p:
            ctx.err = JNTAJISError_MemoryError
            return False
        p[0] = 0x21 + c // 94 % 94
        p[1] = 0x21 + c % 94
        p += 2
        ctx.p = p
        return True
    else:
        if m.tx_len > 0:
            p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2 * m.tx_len)
            if not p:
                ctx.err = JNTAJISError_MemoryError
                return False
            for i in range(m.tx_len):
                c = m.tx_jis[i]
                p[0] = 0x21 + c // 94 % 94
                p[1] = 0x21 + c % 94
                p += 2
            ctx.p = p
            return True
        else:
            return False


cdef object JNTAJISIncrementalEncoderContext_raise(JNTAJISIncrementalEncoderContext* ctx):
    if ctx.err == JNTAJISError_MemoryError:
        raise MemoryError()
    elif ctx.err == JNTAJISError_AssertionError:
        raise AssertionError()


cdef object JNTAJISIncrementalEncoderContext_createUnicodeEncodeError(
    JNTAJISIncrementalEncoderContext* ctx,
    char *reason
):
    return UnicodeEncodeError(
        <object>ctx.e.encoding,
        <object>ctx.u,
        ctx.pos,
        ctx.pos + 1,
        (<bytes>reason).decode("ascii"),
    )


cdef object JNTAJISIncrementalEncoderContext_put_replacement(JNTAJISIncrementalEncoderContext* ctx):
    cdef uint16_t jis = ctx.e.replacement

    if jis == <uint16_t>-1:
        raise JNTAJISIncrementalEncoderContext_createUnicodeEncodeError(
            ctx, "not convertible to JISX0208",
        )
    else:
        if not jis_put_men_1(ctx, jis):
            raise JNTAJISIncrementalEncoderContext_createUnicodeEncodeError(
                ctx, "replacement character is neither convertible to JISX0208",
            )
            

cdef bint JNTAJISIncrementalEncoderContext_put_shift(
    JNTAJISIncrementalEncoderContext* ctx,
    int next_shift_state
) nogil:
    if next_shift_state != ctx.e.shift_state:
        ctx.e.shift_state = next_shift_state
        ctx.p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 1)
        if not ctx.p:
            ctx.err = JNTAJISError_MemoryError
            return False
        if next_shift_state == 0:
            ctx.p[0] = 0x0e
            ctx.p += 1
        elif next_shift_state == 1:
            ctx.p[0] = 0x0f
            ctx.p += 1
        else:
            ctx.err = JNTAJISError_AssertionError
            return False
    return True


cdef bint jis_put_siso(
    JNTAJISIncrementalEncoderContext* ctx,
    uint16_t jis
) nogil:
    if not JNTAJISIncrementalEncoderContext_put_shift(ctx, jis // (94 * 94)):
        return False
    ctx.p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
    if not ctx.p:
        ctx.err = JNTAJISError_MemoryError
        return False
    ctx.p[0] = 0x21 + jis // 94 % 94
    ctx.p[1] = 0x21 + jis % 94
    ctx.p += 2
    return True


cdef object JNTAJISIncrementalEncoderContext_flush_lookahead(
    JNTAJISIncrementalEncoderContext* ctx
):
    cdef jis_put_func put = ctx.e.put_jis
    cdef size_t i
    cdef uint32_t u
    cdef uint16_t jis
    cdef bint ok

    for i in range(ctx.e.lal):
        u = ctx.e.la[i]
        ok = lookup_rev_table(&jis, u)
        if ok:
            ok = put(ctx, jis)
        if not ok:
            if ctx.err == JNTAJISError_Success:
                JNTAJISIncrementalEncoderContext_put_replacement(ctx)
            else:
                JNTAJISIncrementalEncoderContext_raise(ctx)

    JNTAJISIncrementalEncoder_reset(ctx.e)


cdef object JNTAJISIncrementalEncoderContext_encode(
    JNTAJISIncrementalEncoderContext* ctx
):
    cdef jis_put_func put = ctx.e.put_jis
    cdef uint32_t u
    cdef uint16_t jis
    cdef JNTAJISIncrementalEncoder* e = ctx.e

    for ctx.pos in range(ctx.ul):
        u = PyUnicode_READ(ctx.uk, ctx.ud, ctx.pos)
        jis = sm_uni_to_jis_mapping(&e.state, u)
        if e.state == -1:
            if not put(ctx, jis):
                if ctx.err == JNTAJISError_Success:
                    JNTAJISIncrementalEncoderContext_put_replacement(ctx)
                else:
                    JNTAJISIncrementalEncoderContext_raise(ctx)
            e.lal = 0
            e.state = 0
        else:
            if e.lal >= sizeof(e.la) // sizeof(e.la[0]):
                raise JNTAJISIncrementalEncoderContext_createUnicodeEncodeError(
                    ctx, "lookahead buffer overflow"
                )
            e.la[e.lal] = u
            e.lal += 1
            if e.state == 0:
                JNTAJISIncrementalEncoderContext_flush_lookahead(ctx)


cdef void JNTAJISIncrementalEncoder_reset(JNTAJISIncrementalEncoder* e) nogil:
    e.state = 0
    e.lal = 0


cdef object JNTAJISIncrementalEncoder_encode(
    JNTAJISIncrementalEncoder* e,
    unicode u,
    bint flush,
):
    cdef JNTAJISIncrementalEncoderContext ctx
    ctx.e = e
    ctx.u = <PyObject*>u  # borrow
    ctx.uk = PyUnicode_KIND(u)
    ctx.ud = PyUnicode_DATA(u)
    ctx.ul = PyUnicode_GET_LENGTH(u)
    ctx.pos = 0
    ctx.err = JNTAJISError_Success
    _PyBytesWriter_Init(&ctx.writer)
    ctx.p = <char *>_PyBytesWriter_Alloc(&ctx.writer, ctx.ul * 2)
    if not ctx.p:
        raise MemoryError()
    ctx.writer.overallocate = 1
    try:
        JNTAJISIncrementalEncoderContext_encode(&ctx)
        if flush:
            JNTAJISIncrementalEncoderContext_flush_lookahead(&ctx)
            JNTAJISIncrementalEncoderContext_put_shift(&ctx, 0)
        return _PyBytesWriter_Finish(&ctx.writer, ctx.p)
    except:
        _PyBytesWriter_Dealloc(&ctx.writer)
        raise


ctypedef enum ConversionMode:
    ConversionMode_SISO              = 0
    ConversionMode_MEN1              = 1
    ConversionMode_JISX0208          = 2
    ConversionMode_JISX0208_TRANSLIT = 3


cdef jis_put_func jis_put_func_for_conversion_mode(int conv_mode):
    if conv_mode == ConversionMode_SISO:
        return jis_put_siso
    elif conv_mode == ConversionMode_MEN1:
        return jis_put_men_1
    elif conv_mode == ConversionMode_JISX0208:
        return jis_put_jisx0208
    elif conv_mode == ConversionMode_JISX0208_TRANSLIT:
        return jis_put_jisx0208_translit
    else:
        return NULL


cdef void JNTAJISIncrementalEncoder_fini(JNTAJISIncrementalEncoder* e):
    Py_DECREF(<object>e.encoding)


cdef object JNTAJISIncrementalEncoder_init(JNTAJISIncrementalEncoder* e, unicode encoding, int conv_mode):
    if len(encoding) == 0:
        raise ValueError("encoding cannot be empty")
    Py_INCREF(encoding)
    e.encoding = <PyObject*>encoding
    e.replacement = <uint16_t>-1
    e.put_jis = jis_put_func_for_conversion_mode(<int>conv_mode)
    if not e.put_jis:
        raise ValueError(f"unknown conversion mode: {conv_mode}")
    e.lal = 0
    e.shift_state = 0
    e.state = 0


cdef class IncrementalEncoder:
    """
    An IncrementalEncoder implementation.

    For the description of each method, please see the Python's
    codec documentation: https://docs.python.org/3/library/codecs.html#codecs.IncrementalEncoder
    """
    cdef JNTAJISIncrementalEncoder _impl

    def encode(self, in_, final):
        return JNTAJISIncrementalEncoder_encode(&self._impl, in_, final)

    def reset(self):
        JNTAJISIncrementalEncoder_reset(&self._impl)

    def getstate(self):
        return self._impl.state * 2 + self._impl.shift_state

    def setstate(self, state):
        self._impl.shift_state = state % 2
        self._impl.state = state // 2

    def __del__(self):
        JNTAJISIncrementalEncoder_fini(&self._impl)

    def __init__(self, unicode encoding, int conv_mode):
        JNTAJISIncrementalEncoder_init(&self._impl, encoding, conv_mode)


def jnta_encode(unicode encoding, unicode in_, int conv_mode):
    """
    Encode a given Unicode string into JIS X 0208:1997 / JIS X 0213:2012.
    """

    cdef JNTAJISIncrementalEncoder e
    JNTAJISIncrementalEncoder_init(&e, encoding, conv_mode)
    try:
        return JNTAJISIncrementalEncoder_encode(&e, in_, True)
    finally:
        JNTAJISIncrementalEncoder_fini(&e)


ctypedef struct JNTAJISDecoder:
    PyObject* encoding
    int siso
    int shift_offset
    int upper


cdef object JNTAJISDecoder_createUnicodeDecodeError(
    JNTAJISDecoder *d,
    object underlying,
    Py_ssize_t in_size,
    Py_ssize_t pos,
    char *reason
):
    return UnicodeDecodeError(
        <object>d.encoding,
        underlying,
        in_size,
        pos,
        pos + 1,
        (<bytes>reason).decode("ascii"),
    )


cdef object JNTAJISDecoder_decode(
    JNTAJISDecoder *d,
    object underlying,
    void* in_bytes,
    Py_ssize_t in_sz
):
    cdef unsigned char* in_ = <unsigned char *>in_bytes
    cdef unsigned char* p = in_
    cdef unsigned char* e = in_ + in_sz
    cdef unsigned int c0, c1
    cdef uint16_t jis
    cdef const ShrinkingTransliterationMapping* m
    cdef _PyUnicodeWriter writer
    cdef char[256] reason

    _PyUnicodeWriter_Init(&writer)
    writer.min_length = in_sz // 2
    writer.overallocate = 1

    try:
        while p < e:
            if d.upper > 0:
                c0 = d.upper
                d.upper = 0
            else:
                c0 = p[0]
                p += 1

            if c0 >= 0x21 and c0 <= 0x7e:
                if p >= e:
                    d.upper = c0
                    break
                c1 = p[0]
                p += 1
                if c1 >= 0x21 and c1 <= 0x7e:
                    jis = d.shift_offset + (c0 - 0x21)  *94 + (c1 - 0x21)
                    m = &tx_mappings[jis]
                    if m.class_ == JISCharacterClass_RESERVED:
                        snprintf(
                            reason, sizeof(reason),
                            "JIS character %d-%d-%d does not have a corresponding unicode codepoint",
                            <int>(d.shift_offset // 94 // 94 + 1),
                            c0 + 1,
                            c1 + 1,
                        )
                        raise JNTAJISDecoder_createUnicodeDecodeError(
                            d,
                            underlying,
                            in_sz,
                            p - in_ - 2,
                            reason,
                        )
                    else:
                        if m.us[1] == <uint32_t>-1:
                            if _PyUnicodeWriter_Prepare(&writer, 1, <Py_UCS4>m.us[0]):
                                raise MemoryError()
                            _PyUnicodeWriter_WriteChar(&writer, <Py_UCS4>m.us[0])
                        else:
                            if _PyUnicodeWriter_Prepare(&writer, 2, <Py_UCS4>Py_MAX(m.us[0], m.us[1])):
                                raise MemoryError()
                            _PyUnicodeWriter_WriteChar(&writer, <Py_UCS4>m.us[0])
                            _PyUnicodeWriter_WriteChar(&writer, <Py_UCS4>m.us[1])
                else:
                    snprintf(
                        reason, sizeof(reason),
                        "unexpected byte \\x%02x after \\x%02x",
                        c1, c0,
                    )
                    raise JNTAJISDecoder_createUnicodeDecodeError(
                        d,
                        underlying,
                        in_sz,
                        p - in_ - 2,
                        reason,
                    )
            else:
                siso = d.siso
                if c0 == 0x0e and siso:
                    d.shift_offset = 0
                elif c0 == 0x0f and siso:
                    d.shift_offset = 94 * 94
                else:
                    snprintf(
                        reason, sizeof(reason),
                        "unexpected byte \\x%02x",
                        c0,
                    )
                    raise JNTAJISDecoder_createUnicodeDecodeError(
                        d,
                        underlying,
                        in_sz,
                        p - in_ - 2,
                        reason,
                    )
        return _PyUnicodeWriter_Finish(&writer)
    except:
        _PyUnicodeWriter_Dealloc(&writer)
        raise


cdef void JNTAJISDecoder_fini(JNTAJISDecoder *d):
    Py_DECREF(<object>d.encoding)


cdef object JNTAJISDecoder_init(JNTAJISDecoder *d, unicode encoding):
    if len(encoding) == 0:
        raise ValueError("encoding cannot be empty")
    Py_INCREF(encoding)
    d.encoding = <PyObject*>encoding
    d.siso = 0
    d.shift_offset = 0
    d.upper = 0


def jnta_decode(unicode encoding, bytes in_):
    """
    Decode a given JIS character sequence into a Unicode string.
    """

    cdef JNTAJISDecoder d
    JNTAJISDecoder_init(&d, encoding)
    try:
        retval = JNTAJISDecoder_decode(&d, in_, <char *>in_, len(in_))
        if d.upper > 0:
            raise JNTAJISDecoder_createUnicodeDecodeError(
                &d, in_, len(in_), len(in_) - 1,
                "incomplete multibyte character",
            )
        return retval
    finally:
        JNTAJISDecoder_fini(&d)


class TransliterationError(Exception):
    pass


ctypedef struct JNTAJISShrinkingTransliteratorContext:
    _PyUnicodeWriter writer 
    PyObject *replacement
    bint passthrough
    PyObject *in_
    int uk
    void* ud
    Py_ssize_t ul
    Py_ssize_t pos
    int state
    uint32_t[32] la
    size_t lal
    bint finished


cdef object JNTAJISShrinkingTransliteratorContext_put_replacement(
    JNTAJISShrinkingTransliteratorContext* t,
    Py_UCS4 u,
):
    if t.passthrough:
        if _PyUnicodeWriter_Prepare(&t.writer, 1, u):
            raise MemoryError()
        _PyUnicodeWriter_WriteChar(&t.writer, u)
    else:
        if len(<object>t.replacement) == 0:
            raise TransliterationError(f"transliteration failed at position {t.pos}")
        _PyUnicodeWriter_WriteStr(&t.writer, <object>t.replacement)


cdef object JNTAJISIncrementalEncoderContext_put(
    JNTAJISShrinkingTransliteratorContext* t,
    uint16_t jis
):
    cdef const ShrinkingTransliterationMapping* m = &tx_mappings[jis]
    cdef size_t i
    cdef Py_UCS4 u = 0

    if m.class_ == JISCharacterClass_RESERVED:
        return False
    else:
        if (
            (
                m.class_ == JISCharacterClass_JISX0213_NON_KANJI or
                m.class_ == JISCharacterClass_KANJI_LEVEL_3 or
                m.class_ == JISCharacterClass_KANJI_LEVEL_4
            )
            and m.tx_len > 0
        ):
            for i in range(m.tx_len):
                u = Py_MAX(u, m.tx_us[i])
            if _PyUnicodeWriter_Prepare(&t.writer, m.tx_len, u):
                raise MemoryError()
            for i in range(m.tx_len):
                _PyUnicodeWriter_WriteChar(&t.writer, <Py_UCS4>m.tx_us[i])
        else:
            if m.us[1] == <uint32_t>-1:
                if _PyUnicodeWriter_Prepare(&t.writer, 1, <Py_UCS4>m.us[0]):
                    raise MemoryError()
                _PyUnicodeWriter_WriteChar(&t.writer, <Py_UCS4>m.us[0])
            else:
                if _PyUnicodeWriter_Prepare(&t.writer, 2, <Py_UCS4>Py_MAX(m.us[0], m.us[1])):
                    raise MemoryError()
                _PyUnicodeWriter_WriteChar(&t.writer, <Py_UCS4>m.us[0])
                _PyUnicodeWriter_WriteChar(&t.writer, <Py_UCS4>m.us[1])
        return True


cdef object JNTAJISShrinkingTransliteratorContext_do(
    JNTAJISShrinkingTransliteratorContext* t,
):
    cdef Py_UCS4 u
    cdef uint16_t jis
    cdef size_t i
    cdef const ShrinkingTransliterationMapping* m

    for t.pos in range(t.ul):
        u = PyUnicode_READ(t.uk, t.ud, t.pos)
        jis = sm_uni_to_jis_mapping(&t.state, u)
        if t.state == -1:
            if not JNTAJISIncrementalEncoderContext_put(t, jis):
                JNTAJISShrinkingTransliteratorContext_put_replacement(t, u)
            t.state = 0
        else:
            t.la[t.lal] = u
            t.lal += 1
            if t.state == 0:
                for i in range(t.lal):
                    if not lookup_rev_table(&jis, t.la[i]):
                        JNTAJISShrinkingTransliteratorContext_put_replacement(t, u)
                        continue
                    else:
                        if not JNTAJISIncrementalEncoderContext_put(t, jis):
                            JNTAJISShrinkingTransliteratorContext_put_replacement(t, u)
                t.lal = 0

    return True

cdef unicode JNTAJISShrinkingTransliteratorContext_get_result(
    JNTAJISShrinkingTransliteratorContext* t,
):
    t.finished = 1
    return _PyUnicodeWriter_Finish(&t.writer)


cdef void JNTAJISShrinkingTransliteratorContext_fini(
    JNTAJISShrinkingTransliteratorContext* t,
):
    if not t.finished:
        _PyUnicodeWriter_Dealloc(&t.writer)
    Py_DECREF(<object>t.in_)
    Py_DECREF(<object>t.replacement)


cdef JNTAJISShrinkingTransliteratorContext_init(
    JNTAJISShrinkingTransliteratorContext* t,
    unicode in_,
    unicode replacement,
    bint passthrough,
):
    Py_INCREF(in_)
    t.in_ = <PyObject*>in_
    Py_INCREF(replacement)
    t.replacement = <PyObject*>replacement
    t.uk = PyUnicode_KIND(in_)
    t.ud = PyUnicode_DATA(in_)
    t.ul = PyUnicode_GET_LENGTH(in_)
    _PyUnicodeWriter_Init(&t.writer)
    t.writer.min_length = len(in_)
    t.writer.overallocate = 1
    t.state = 0
    t.lal = 0
    t.finished = 0
    t.passthrough = passthrough


def jnta_shrink_translit(unicode in_, unicode replacement=u"\ufffe", bint passthrough=False):
    """
    Transliterate a Unicode string according to the NTA shrink mappings.
    """

    cdef JNTAJISShrinkingTransliteratorContext ctx

    JNTAJISShrinkingTransliteratorContext_init(&ctx, in_, replacement, passthrough)
    try:
        JNTAJISShrinkingTransliteratorContext_do(&ctx)
        return JNTAJISShrinkingTransliteratorContext_get_result(&ctx)
    finally:
        JNTAJISShrinkingTransliteratorContext_fini(&ctx)


cdef bint MJShrinkMappingUnicodeSet_valid(const MJShrinkMappingUnicodeSet *sm) nogil:
    cdef size_t i
    for i in range(sizeof(sm._0) // sizeof(sm._0[0])):
        if sm._0[i] != <uint32_t>-1:
            return 1
    for i in range(sizeof(sm._1) // sizeof(sm._1[0])):
        if sm._1[i] != <uint32_t>-1:
            return 1
    for i in range(sizeof(sm._2) // sizeof(sm._2[0])):
        if sm._2[i] != <uint32_t>-1:
            return 1
    for i in range(sizeof(sm._3) // sizeof(sm._3[0])):
        if sm._3[i] != <uint32_t>-1:
            return 1
    return 0


cdef bint lookup_mj_mapping_table(const MJMappingSet** pms, uint32_t u) nogil:
    cdef size_t l = sizeof(urange_to_mj_mappings) // sizeof(urange_to_mj_mappings[0])
    cdef size_t s = 0, e = l
    cdef size_t m, i
    cdef const URangeToMJMappings* um
    cdef const MJMappingSet* ms
    while s < e and e <= l:
        m = (s + e) // 2
        um = &urange_to_mj_mappings[m]
        if u < um.start:
            e = m
            continue
        elif u > um.end:
            s = m + 1
            continue
        if u > um.end:
            break
        ms = &um.mss[u - um.start]
        if ms.l == 0:
            break
        pms[0] = ms
        return True
    return False


ctypedef struct MJShrinkCandidates:
    size_t l
    UIVSPair[20]* a
    size_t* al
    size_t* is_


cdef Py_UCS4 to_ivs(int n) nogil:
    if n < 16:
        return 0xfe00 + n
    else:
        return 0xe00f0 + n


cdef object MJShrinkCandidates_append_candidates(MJShrinkCandidates* cands, list li, int limit):
    cdef size_t i
    cdef Py_ssize_t l
    cdef _PyUnicodeWriter w
    cdef UIVSPair* c
    cdef Py_UCS4 u

    while True:
        if limit >= 0:
            limit -= 1
            if limit < 0:
                break
        _PyUnicodeWriter_Init(&w)
        u = 0
        l = 0
        for i in range(cands.l):
            c = &cands.a[i][cands.is_[i]]
            u = Py_MAX(u, c.u)
            l += 1
            if c.sv:
                u = Py_MAX(u, to_ivs(c.s))
                l += 1

        if _PyUnicodeWriter_Prepare(&w, l, u):
            _PyUnicodeWriter_Dealloc(&w)
            raise MemoryError()

        for i in range(cands.l):
            c = &cands.a[i][cands.is_[i]]
            _PyUnicodeWriter_WriteChar(&w, c.u)
            if c.sv:
                _PyUnicodeWriter_WriteChar(&w, to_ivs(c.s))

        li.append(_PyUnicodeWriter_Finish(&w))

        for i in range(cands.l):
            cands.is_[i] += 1
            if cands.is_[i] < cands.al[i]:
                break
            cands.is_[i] = 0
        else:
            break


cdef void MJShrinkCandidates_fini(MJShrinkCandidates* cands) nogil:
    if cands.a != NULL:
        free(cands.a)
    if cands.al != NULL:
        free(cands.al)
    if cands.is_ != NULL:
        free(cands.is_)


cdef int resolve_ivs_no(Py_UCS4 n) nogil:
    # VS1 to VS16
    if n >= 0xfe00 and n < 0xfe10:
        return <int>n - <int>0xfe00
    # VS17 to VS256
    if n >= 0xe0100 and n < 0xe01f0:
        return <int>n - <int>0xe00f0
    return -1


cdef MJShrinkCandidates_init(MJShrinkCandidates* cands, unicode in_, int combo):
    cdef int uk = PyUnicode_KIND(in_)
    cdef Py_ssize_t ul = PyUnicode_GET_LENGTH(in_)
    cdef void* ud = PyUnicode_DATA(in_)
    cdef Py_ssize_t i = 0
    cdef size_t k, j, l, p
    cdef int iv
    cdef Py_UCS4 u, nu
    cdef uint32_t uu
    cdef const MJShrinkMappingUnicodeSet* sm
    cdef const MJMappingSet* ms
    cdef const MJMapping* cmm[64]
    cdef const MJMapping* mm
    cdef const MJMapping** cmmp
    cdef const MJMapping** cmme
    cdef UIVSPair[20] c 
    cdef UIVSPair[20]* a
    cdef size_t* al
    cdef size_t* is_

    a = <UIVSPair[20]*>calloc(ul, sizeof(UIVSPair[20]))
    if a == NULL:
        raise MemoryError()
    al = <size_t*>calloc(ul, sizeof(size_t))
    if al == NULL:
        free(a)
        raise MemoryError()
    is_ = <size_t*>calloc(ul, sizeof(size_t))
    if is_ == NULL:
        free(al)
        free(a)
        raise MemoryError()

    p = 0
    while i < ul:
        is_[p] = 0
        l = 0
        iv = -1
        u = PyUnicode_READ(uk, ud, i)
        i += 1
        if i < ul:
            nu = PyUnicode_READ(uk, ud, i)
            iv = resolve_ivs_no(nu)
            if iv >= 0:
                i += 1

        cmme = cmm
        if lookup_mj_mapping_table(&ms, u):
            if iv >= 0:
                # expecting exact match
                for j in range(ms.l):
                    mm = &ms.ms[j]
                    for k in range(sizeof(mm.v) / sizeof(mm.v[0])):
                        if not mm.v[k].v:
                            mm = NULL
                            break
                        if mm.v[k].u == u and mm.v[k].sv and mm.v[k].s == iv:
                            break
                    else:
                        mm = NULL
                    if mm != NULL:
                        cmmp = cmm
                        while cmmp < cmme:
                            if cmmp[0] == mm:
                                break
                            cmmp += 1
                        else:
                            cmme[0] = mm
                            cmme += 1
                            if cmme >= cmm + sizeof(cmm) / sizeof(cmm[0]):
                                raise MemoryError()
                        break
            else:
                # search for all candidates
                for j in range(ms.l):
                    mm = &ms.ms[j]
                    for k in range(sizeof(mm.v) / sizeof(mm.v[0])):
                        if not mm.v[k].v:
                            mm = NULL
                            break
                        if mm.v[k].u == u and not mm.v[k].sv:
                            break
                    else:
                        mm = NULL
                    if mm != NULL:
                        cmmp = cmm
                        while cmmp < cmme:
                            if cmmp[0] == mm:
                                break
                            cmmp += 1
                        else:
                            cmme[0] = mm
                            cmme += 1
                            if cmme >= cmm + sizeof(cmm) / sizeof(cmm[0]):
                                raise MemoryError()

        cmmp = cmm
        while cmmp < cmme:
            mm = cmmp[0]

            sm = &mj_shrink_mappings[mm.mj]
            if MJShrinkMappingUnicodeSet_valid(sm):
                if combo & 1 != 0:
                    for j in range(sizeof(sm._0) // sizeof(sm._0[0])):
                        uu = sm._0[j]
                        if uu == <uint32_t>-1:
                            break
                        if uu == u and iv < 0:
                            break
                        for k in range(l):
                            if c[k].u == uu and not c[k].sv:
                                break
                        else:
                            c[l].u = uu
                            c[l].v = True
                            c[l].sv = False
                            c[l].s = 0
                            l += 1
                if combo & 2 != 0:
                    for j in range(sizeof(sm._1) // sizeof(sm._1[0])):
                        uu = sm._1[j]
                        if uu == <uint32_t>-1:
                            break
                        if uu == u and iv < 0:
                            break
                        for k in range(l):
                            if c[k].u == uu and not c[k].sv:
                                break
                        else:
                            c[l].u = uu
                            c[l].v = True
                            c[l].sv = False
                            c[l].s = 0
                            l += 1
                if combo & 4 != 0:
                    for j in range(sizeof(sm._2) // sizeof(sm._2[0])):
                        uu = sm._2[j]
                        if uu == <uint32_t>-1:
                            break
                        if uu == u and iv < 0:
                            break
                        for k in range(l):
                            if c[k].u == uu and not c[k].sv:
                                break
                        else:
                            c[l].u = uu
                            c[l].v = True
                            c[l].sv = False
                            c[l].s = 0
                            l += 1
                if combo & 8 != 0:
                    for j in range(sizeof(sm._3) // sizeof(sm._3[0])):
                        uu = sm._3[j]
                        if uu == <uint32_t>-1:
                            break
                        if uu == u and iv < 0:
                            break
                        for k in range(l):
                            if c[k].u == uu and not c[k].sv:
                                break
                        else:
                            c[l].u = uu
                            c[l].v = True
                            c[l].sv = False
                            c[l].s = 0
                            l += 1
            cmmp += 1

        cmmp = cmm
        while cmmp < cmme:
            mm = cmmp[0]

            for j in range(sizeof(mm.v) / sizeof(mm.v[0])):
                if not mm.v[j].v:
                    break
                if not mm.v[j].sv:
                    uu = mm.v[j].u
                    for k in range(l):
                        if c[k].u == uu and not c[k].sv:
                            break
                    else:
                        c[l].u = uu
                        c[l].v = True
                        c[l].sv = False
                        c[l].s = 0
                        l += 1

            cmmp += 1

        if l == 0:
            c[0].u = u
            c[0].v = True
            c[0].sv = iv >= 0
            c[0].s = iv
            l = 1
        al[p] = l
        memcpy(a[p], c, sizeof(UIVSPair[20]))
        p += 1

    cands.l = p
    cands.a = a
    cands.al = al
    cands.is_ = is_


def mj_shrink_candidates(unicode in_, int combo, int limit = 100):
    cdef MJShrinkCandidates cands
    cands.a = cands.al = cands.is_ = NULL
    retval = []
    try:
        MJShrinkCandidates_init(&cands, in_, combo)
        MJShrinkCandidates_append_candidates(&cands, retval, limit)
    finally:
        MJShrinkCandidates_fini(&cands)
    return retval
