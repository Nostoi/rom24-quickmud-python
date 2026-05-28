/* Portability shim: macOS has no <endian.h> (Linux/glibc only). ROM's sha256.c
 * `#include <endian.h>` on the non-FreeBSD path but only needs be32dec/be32enc,
 * which it defines itself under `#if __FreeBSD_version < 500111` (true here, as
 * __FreeBSD_version is undefined → 0). So an empty header satisfies the include
 * without pulling ROM's macros. Found first via -Idiff_shim. Additive only. */
#ifndef DIFF_SHIM_ENDIAN_H
#define DIFF_SHIM_ENDIAN_H
#endif
