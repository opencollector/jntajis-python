from libc.stdio cimport snprintf
from libc.stdlib cimport malloc, calloc, free
from libc.string cimport memcpy
from cpython.ref cimport PyObject, Py_INCREF, Py_DECREF

import enum

cdef extern from "_jntajis.h":
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
    ctypedef struct MJShrinkMappingUnicodeSet:
        uint32_t[3] _0
        uint32_t[1] _1
        uint32_t[2] _2
        uint32_t[3] _3
    ctypedef struct URangeToMJShrinkMappingUnicodeSets:
        uint32_t start, end
        const MJShrinkMappingUnicodeSet* sm
    const URangeToMJShrinkMappingUnicodeSets[] urange_to_mj_shrink_usets_mappings


cdef extern from "Python.h":
    uint32_t Py_MAX(uint32_t, uint32_t)

    ctypedef struct _PyUnicodeWriter:
        Py_ssize_t min_length
        int overallocate
    ctypedef int Py_UCS4
    void _PyUnicodeWriter_Init(_PyUnicodeWriter*)
    void _PyUnicodeWriter_Dealloc(_PyUnicodeWriter*)
    void _PyUnicodeWriter_WriteChar(_PyUnicodeWriter*, Py_UCS4)
    void _PyUnicodeWriter_WriteStr(_PyUnicodeWriter*, unicode)
    object _PyUnicodeWriter_Finish(_PyUnicodeWriter*)
    int _PyUnicodeWriter_Prepare(_PyUnicodeWriter*, Py_ssize_t, Py_ssize_t)
    int  _PyUnicodeWriter_PrepareKind(_PyUnicodeWriter*, int)

    int PyUnicode_KIND(object)
    void* PyUnicode_DATA(object) 
    Py_ssize_t PyUnicode_GET_LENGTH(object)
    Py_UCS4 PyUnicode_READ(int, void*, Py_ssize_t)

    ctypedef struct _PyBytesWriter:
        int overallocate
    void _PyBytesWriter_Init(_PyBytesWriter*)
    void _PyBytesWriter_Alloc(_PyBytesWriter*, Py_ssize_t)
    void _PyBytesWriter_Dealloc(_PyBytesWriter*)
    object _PyBytesWriter_Finish(_PyBytesWriter*, void*)
    void* _PyBytesWriter_Prepare(_PyBytesWriter*, void*, Py_ssize_t)
    void* _PyBytesWriter_WriteBytes(_PyBytesWriter*, void*, void*, Py_ssize_t)


cdef bint lookup_rev_table(uint16_t* pj, uint32_t u):
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
        return 1
    return 0


cdef bint jis_put_men_1(JNTAJISIncrementalEncoderContext* ctx, uint16_t c):
    cdef unsigned int men = c // (94 * 94)
    cdef unsigned int ku = c // 94 % 94
    cdef unsigned int ten = c % 94
    cdef char* p
    if men != 0:
        return 0

    p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
    if not p:
        raise MemoryError()
    p[0] = 0x21 +  ku
    p[1] = 0x21 + ten
    p += 2
    ctx.p = p
    return 1


cdef bint jis_put_jisx0208(JNTAJISIncrementalEncoderContext* ctx, uint16_t c):
    if c >= sizeof(tx_mappings) // sizeof(tx_mappings[0]):
        return 0
    cdef class_ = tx_mappings[c].class_
    cdef char* p
    if (
        class_ == JISCharacterClass_KANJI_LEVEL_1 or
        class_ == JISCharacterClass_KANJI_LEVEL_2 or
        class_ == JISCharacterClass_JISX0208_NON_KANJI
    ):
        p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
        if not p:
            raise MemoryError()
        p[0] = c // 94 % 94
        p[1] = c % 94
        p += 2
        ctx.p = p
        return 1
    else:
        return 0


cdef bint jis_put_jisx0208_translit(JNTAJISIncrementalEncoderContext* ctx, uint16_t c):
    if c >= sizeof(tx_mappings) // sizeof(tx_mappings[0]):
        return 0
    cdef const ShrinkingTransliterationMapping* m = &tx_mappings[c]
    cdef class_ = m.class_
    cdef char* p
    if (
        class_ == JISCharacterClass_KANJI_LEVEL_1 or
        class_ == JISCharacterClass_KANJI_LEVEL_2 or
        class_ == JISCharacterClass_JISX0208_NON_KANJI
    ):
        p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
        if not p:
            raise MemoryError()
        p[0] = c // 94 % 94
        p[1] = c % 94
        p += 2
        ctx.p = p
        return 1
    else:
        if m.tx_len > 0:
            p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2 * m.tx_len)
            if not p:
                raise MemoryError()
            for i in range(m.tx_len):
                c = m.tx_jis[i]
                p[0] = c // 94 % 94
                p[1] = c % 94
                p += 2
            ctx.p = p
            return 1
        else:
            return 0


ctypedef bint (*jis_put_func)(JNTAJISIncrementalEncoderContext*, uint16_t)


ctypedef struct JNTAJISIncrementalEncoder:
    PyObject* encoding
    uint16_t replacement
    jis_put_func put_jis
    size_t lal
    uint32_t[32] la
    int shift_state
    int state


ctypedef struct JNTAJISIncrementalEncoderContext:
    JNTAJISIncrementalEncoder* e
    _PyBytesWriter writer
    PyObject* u  # borrow
    int ukind
    void* ud
    Py_ssize_t ul
    Py_ssize_t pos
    char* p


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


cdef JNTAJISIncrementalEncoderContext_put_replacement(JNTAJISIncrementalEncoderContext* ctx):
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
            

cdef JNTAJISIncrementalEncoderContext_put_shift(
    JNTAJISIncrementalEncoderContext* ctx,
    int next_shift_state
):
    if next_shift_state != ctx.e.shift_state:
        ctx.e.shift_state = next_shift_state
        ctx.p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 1)
        if not ctx.p:
            raise MemoryError()
        if next_shift_state == 0:
            ctx.p[0] = 0x0e
            ctx.p += 1
        elif next_shift_state == 1:
            ctx.p[0] = 0x0f
            ctx.p += 1
        else:
            raise AssertionError("should never happend")


cdef bint jis_put_siso(
    JNTAJISIncrementalEncoderContext* ctx,
    uint16_t jis
):
    JNTAJISIncrementalEncoderContext_put_shift(ctx, jis // (94 * 94))
    ctx.p = <char *>_PyBytesWriter_Prepare(&ctx.writer, ctx.p, 2)
    if not ctx.p:
        raise MemoryError()
    ctx.p[0] = 0x21 + jis // 94 % 94
    ctx.p[1] = 0x21 + jis % 94
    ctx.p += 2
    return 1


cdef JNTAJISIncrementalEncoderContext_flush_lookahead(
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
            JNTAJISIncrementalEncoderContext_put_replacement(ctx)

    JNTAJISIncrementalEncoder_reset(ctx.e)


cdef JNTAJISIncrementalEncoderContext_encode(
    JNTAJISIncrementalEncoderContext* ctx
):
    cdef jis_put_func put = ctx.e.put_jis
    cdef uint32_t u
    cdef uint16_t jis
    cdef JNTAJISIncrementalEncoder* e = ctx.e

    for ctx.pos in range(0, ctx.ul):
        u = PyUnicode_READ(ctx.ukind, ctx.ud, ctx.pos)
        jis = sm_uni_to_jis_mapping(&e.state, u)
        if e.state == -1:
            if not put(ctx, jis):
                JNTAJISIncrementalEncoderContext_put_replacement(ctx)
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


cdef JNTAJISIncrementalEncoder_reset(JNTAJISIncrementalEncoder* e):
    e.state = 0
    e.lal = 0


cdef JNTAJISIncrementalEncoder_encode(
    JNTAJISIncrementalEncoder* e,
    unicode u,
    bint flush,
):
    cdef JNTAJISIncrementalEncoderContext ctx
    ctx.e = e
    ctx.u = <PyObject*>u  # borrow
    ctx.ukind = PyUnicode_KIND(u)
    ctx.ud = PyUnicode_DATA(u)
    ctx.ul = PyUnicode_GET_LENGTH(u)
    ctx.pos = 0
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


cdef void JNTAJISIncrementalEncoder_init(JNTAJISIncrementalEncoder* e, unicode encoding, int conv_mode):
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
    cdef JNTAJISIncrementalEncoder _impl

    def encoder(self, in_, final):
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


def encode(in_, encoding, conv_mode):
    cdef JNTAJISIncrementalEncoder e
    JNTAJISIncrementalEncoder_init(&e, encoding, conv_mode)
    try:
        return JNTAJISIncrementalEncoder_encode(&e, in_, 1)
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
    writer.min_length = in_sz / 2
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


cdef void JNTAJISDecoder_init(JNTAJISDecoder *d, unicode encoding):
    Py_INCREF(encoding)
    d.encoding = <PyObject*>encoding
    d.siso = 0
    d.shift_offset = 0
    d.upper = 0


def decode(unicode encoding, bytes in_):
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
    int ukind
    void* ud
    Py_ssize_t ul
    Py_ssize_t pos
    int state
    uint32_t[32] la
    size_t lal
    bint finished


cdef void JNTAJISShrinkingTransliteratorContext_put_replacement(
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


cdef bint JNTAJISIncrementalEncoderContext_put(
    JNTAJISShrinkingTransliteratorContext* t,
    uint16_t jis
):
    cdef const ShrinkingTransliterationMapping* m = &tx_mappings[jis]
    cdef size_t i

    if m.class_ == JISCharacterClass_RESERVED:
        return 0
    else:
        if (
            (
                m.class_ == JISCharacterClass_JISX0213_NON_KANJI or
                m.class_ == JISCharacterClass_KANJI_LEVEL_3 or
                m.class_ == JISCharacterClass_KANJI_LEVEL_4
            )
            and m.tx_len > 0
        ):
            if _PyUnicodeWriter_Prepare(&t.writer, m.tx_len, 0x10ffff):
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
        return 1


cdef void JNTAJISShrinkingTransliteratorContext_do(
    JNTAJISShrinkingTransliteratorContext* t,
):
    cdef Py_UCS4 u
    cdef uint16_t jis
    cdef size_t i
    cdef const ShrinkingTransliterationMapping* m

    for t.pos in range(t.ul):
        u = PyUnicode_READ(t.ukind, t.ud, t.pos)
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
                        JNTAJISIncrementalEncoderContext_put(t, jis)
                t.lal = 0


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
    t.ukind = PyUnicode_KIND(in_)
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
    cdef JNTAJISShrinkingTransliteratorContext ctx

    JNTAJISShrinkingTransliteratorContext_init(&ctx, in_, replacement, passthrough)
    try:
        JNTAJISShrinkingTransliteratorContext_do(&ctx)
        return JNTAJISShrinkingTransliteratorContext_get_result(&ctx)
    finally:
        JNTAJISShrinkingTransliteratorContext_fini(&ctx)


cdef bint lookup_mj_shrink_table(const MJShrinkMappingUnicodeSet** psm, uint32_t u):
    cdef size_t l = sizeof(urange_to_mj_shrink_usets_mappings) // sizeof(urange_to_mj_shrink_usets_mappings[0])
    cdef size_t s = 0, e = l
    cdef size_t m
    cdef const URangeToMJShrinkMappingUnicodeSets* mm
    cdef const MJShrinkMappingUnicodeSet* sm
    while s < e and e <= l:
        m = (s + e) // 2
        mm = &urange_to_mj_shrink_usets_mappings[m]
        if u < mm.start:
            e = m
            continue
        elif u > mm.end:
            s = m + 1
            continue
        if u > mm.end:
            break
        sm = &mm.sm[u - mm.start]
        if (
            sm._0[0] == <uint32_t>-1 and
            sm._0[1] == <uint32_t>-1 and
            sm._0[2] == <uint32_t>-1 and
            sm._1[0] == <uint32_t>-1 and
            sm._2[0] == <uint32_t>-1 and
            sm._2[1] == <uint32_t>-1 and
            sm._3[0] == <uint32_t>-1 and
            sm._3[1] == <uint32_t>-1 and
            sm._3[2] == <uint32_t>-1
        ):
            break
        psm[0] = sm
        return 1
    return 0


ctypedef struct MJShrinkCandidates:
    size_t l
    uint32_t[10]* a
    size_t* al
    size_t* is_


cdef void MJShrinkCandidates_append_candidates(MJShrinkCandidates* cands, list l):
    cdef size_t i
    cdef _PyUnicodeWriter w
    cdef void* p

    while True:
        _PyUnicodeWriter_Init(&w)
        if _PyUnicodeWriter_Prepare(&w, <Py_ssize_t>cands.l, <Py_UCS4>0x10ffff):
            raise MemoryError()

        for i in range(0, cands.l):
            _PyUnicodeWriter_WriteChar(&w, cands.a[i][cands.is_[i]])

        l.append(_PyUnicodeWriter_Finish(&w))

        for i in range(0, cands.l):
            cands.is_[i] += 1
            if cands.is_[i] < cands.al[i]:
                break
            cands.is_[i] = 0
        else:
            break


cdef void MJShrinkCandidates_fini(MJShrinkCandidates* cands):
    free(cands.a)
    free(cands.al)
    free(cands.is_)


cdef void MJShrinkCandidates_init(MJShrinkCandidates* cands, unicode in_, int combo):
    cdef int ukind = PyUnicode_KIND(in_)
    cdef int ul = PyUnicode_GET_LENGTH(in_)
    cdef void* ud = PyUnicode_DATA(in_)
    cdef int i, j, k, l
    cdef Py_UCS4 u
    cdef uint32_t uu
    cdef const MJShrinkMappingUnicodeSet* sm
    cdef uint32_t[10] c 
    cdef uint32_t[10]* a
    cdef size_t* al
    cdef size_t* is_

    a = <uint32_t[10]*>calloc(ul, sizeof(uint32_t[10]))
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

    for i in range(0, ul):
        is_[i] = 0
        u = PyUnicode_READ(ukind, ud, i)
        c[0] = u
        l = 1
        if lookup_mj_shrink_table(&sm, u):
            if combo & 1 != 0:
                for j in range(0, 3):
                    uu = sm._0[j]
                    if uu == <uint32_t>-1:
                        break
                    for k in range(l):
                        if c[k] == uu:
                            break
                    else:
                        c[l] = uu
                        l += 1
            if combo & 2 != 0:
                for j in range(0, 1):
                    uu = sm._1[j]
                    if uu == <uint32_t>-1:
                        break
                    for k in range(l):
                        if c[k] == uu:
                            break
                    else:
                        c[l] = uu
                        kl += 1
            if combo & 4 != 0:
                for j in range(0, 2):
                    uu = sm._2[j]
                    if uu == <uint32_t>-1:
                        break
                    for k in range(l):
                        if c[k] == uu:
                            break
                    else:
                        c[l] = uu
                        l += 1
            if combo & 8 != 0:
                for j in range(0, 3):
                    uu = sm._3[j]
                    if uu == <uint32_t>-1:
                        break
                    for k in range(l):
                        if c[k] == uu:
                            break
                    else:
                        c[l] = uu
                        l += 1
        al[i] = l
        memcpy(a[i], c, sizeof(uint32_t[10]))

    cands.l = ul
    cands.a = a
    cands.al = al
    cands.is_ = is_

def mj_shrink_candidates(unicode in_, int combo):
    cdef MJShrinkCandidates cands
    retval = []
    try:
        MJShrinkCandidates_init(&cands, in_, combo)
        MJShrinkCandidates_append_candidates(&cands, retval)
    finally:
        MJShrinkCandidates_fini(&cands)
    return retval
