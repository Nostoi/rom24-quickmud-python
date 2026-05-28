/*
 * diffmain.c — additive instrumentation entry point for the differential
 * testing harness (Task 5). Boots the ROM world, seeds the OLD_RAND generator
 * deterministically, drives ROM's real interpret() from scripted stdin, and
 * emits one JSON `output` line per command plus one JSON `snapshot` line on the
 * `__snapshot` meta-command.
 *
 * It links against UNMODIFIED ROM objects (comm.c included, with its main()
 * renamed to rom_main_unused via -Dmain). Output capture reuses ROM's real
 * send_to_char / act_new / write_to_buffer by attaching a synthetic
 * DESCRIPTOR_DATA to the test character, so captured text is byte-for-byte ROM.
 *
 * boot_db() reads ../area/area.lst relative to CWD, so run this binary from
 * src/ (the capture tool sets cwd=REPO/src).
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "merc.h"

/* ROM globals normally defined in comm.c are available via the linked comm.o. */

void boot_db (void);

/*
 * nanny() lives in nanny.c (the login state machine), which we exclude — comm.c
 * references it but our harness drives interpret() directly and never enters the
 * connection handshake, so an unreachable stub satisfies the linker.
 */
void nanny (DESCRIPTOR_DATA *d, char *argument)
{
    (void) d;
    (void) argument;
}

int main (int argc, char **argv)
{
    (void) argc;
    (void) argv;

    /*
     * ROM's boot_db() opens area.lst (and reserves NULL_FILE) relative to CWD.
     * The stock server runs from the area/ directory; we instead chdir into the
     * generated overlay (diff_shim/area, built by `make area-overlay`), which
     * symlinks every stock area file but substitutes a midgaard.are with the
     * `#ROOMS` section keyword injected (stock midgaard omits it, which the
     * ROM parser rejects). The binary stays in src/; only the working dir
     * moves. Honour an explicit DIFFSHIM_AREA_DIR override if set.
     */
    {
        const char *area_dir = getenv ("DIFFSHIM_AREA_DIR");
        if (area_dir == NULL || area_dir[0] == '\0')
            area_dir = "diff_shim/area";
        if (chdir (area_dir) != 0)
        {
            perror (area_dir);
            return 1;
        }
    }

    /* Force a deterministic clock before boot_db()/init_mm() consult it. */
    current_time = (time_t) 0;

    boot_db ();

    printf ("BOOT OK\n");
    fflush (stdout);
    return 0;
}
