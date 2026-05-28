/* Portability shim: macOS has no <malloc.h>; malloc/free live in <stdlib.h>.
 * ROM's save.c does an unconditional `#include <malloc.h>`. Rather than edit
 * the untouchable ROM source, we satisfy that include via -Idiff_shim so this
 * header is found first. Additive only — no ROM file is modified. */
#ifndef DIFF_SHIM_MALLOC_H
#define DIFF_SHIM_MALLOC_H
#include <stdlib.h>
#endif
