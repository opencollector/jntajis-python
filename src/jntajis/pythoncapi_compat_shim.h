#ifndef _PYTHONCAPI_COMPAT_SHIM_H
#define _PYTHONCAPI_COMPAT_SHIM_H

#include "pythoncapi_compat.h"

#if PY_VERSION_HEX < 0x030F00A1
static inline void *PyBytesWriter_Prepare(PyBytesWriter *w, void *p, Py_ssize_t s) {
    const Py_ssize_t ns = w->size + s;
    if (ns < w->size) {
        return NULL;
    }
    const Py_ssize_t offset = (char *)p - (char *)PyBytesWriter_GetData(w);
    if (_PyBytesWriter_Resize_impl(w, ns, 1) < 0) {
        return NULL;
    }
    return (char *)PyBytesWriter_GetData(w) + offset;
}
#endif /* PY_VERSION_HEX < 0x030F00A1 */

#endif /* _PYTHONCAPI_COMPAT_SHIM_H */
