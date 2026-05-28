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
 * boot_db() reads area.lst relative to CWD; main() chdirs into the generated
 * diff_shim/area overlay first (see Makefile.diffshim).
 *
 * Protocol (line-oriented over stdin):
 *   boot seed=<n> start_room=<v> char=<name>   (first line)
 *   <any ROM command>                          -> {"type":"output","lines":[...]}
 *   __snapshot chars=<a,b> rooms=<v,v>         -> {"type":"snapshot",...}
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "merc.h"
#include "tables.h"    /* struct flag_type + affect_flags[] for affect_flags */
#include "recycle.h"   /* new_char / new_pcdata prototypes (else ptr truncates) */

/* ROM functions we call (some lack prototypes in merc.h — declared here). */
void boot_db (void);
void init_mm (void);
void reset_char (CHAR_DATA *ch);
void violence_update (void);

/* ---- synthetic descriptor: ROM's output funcs write here ------------------ */

#define SHIM_OUTBUF_SIZE (256 * 1024)

static DESCRIPTOR_DATA shim_desc;
static char shim_outbuf[SHIM_OUTBUF_SIZE];

/* Reset the capture buffer before each command. */
static void shim_reset_output (void)
{
    shim_outbuf[0] = '\0';
    shim_desc.outtop = 0;
}

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

/* ---- tiny hand-rolled JSON helpers (no JSON lib) -------------------------- */

/* Print a JSON string literal (with surrounding quotes), escaping per RFC8259. */
static void json_str (const char *s)
{
    putchar ('"');
    if (s != NULL)
    {
        for (; *s != '\0'; s++)
        {
            unsigned char c = (unsigned char) *s;
            switch (c)
            {
                case '"':  fputs ("\\\"", stdout); break;
                case '\\': fputs ("\\\\", stdout); break;
                case '\n': fputs ("\\n", stdout); break;
                case '\r': fputs ("\\r", stdout); break;
                case '\t': fputs ("\\t", stdout); break;
                default:
                    if (c < 0x20)
                        printf ("\\u%04x", c);
                    else
                        putchar (c);
                    break;
            }
        }
    }
    putchar ('"');
}

/* Emit the captured output buffer as {"type":"output","lines":[...]}.
 * Split on '\n'; a trailing '\r' on each line is dropped (ROM uses "\n\r"). */
static void emit_output (void)
{
    /* ROM's write_to_buffer() appends via strncpy without terminating at
     * outtop, so null-terminate the captured region before scanning it. */
    int top = shim_desc.outtop;
    if (top < 0)
        top = 0;
    if (top >= SHIM_OUTBUF_SIZE)
        top = SHIM_OUTBUF_SIZE - 1;
    shim_outbuf[top] = '\0';

    fputs ("{\"type\":\"output\",\"lines\":[", stdout);

    const char *p = shim_outbuf;
    int first = 1;
    while (*p != '\0')
    {
        const char *nl = strchr (p, '\n');
        size_t len = (nl != NULL) ? (size_t) (nl - p) : strlen (p);

        if (!first)
            putchar (',');
        first = 0;

        /* Copy the line, dropping a trailing '\r', and JSON-escape it. */
        char line[2 * MAX_STRING_LENGTH];
        size_t n = len;
        if (n > 0 && p[n - 1] == '\r')
            n--;
        if (n >= sizeof (line))
            n = sizeof (line) - 1;
        memcpy (line, p, n);
        line[n] = '\0';
        json_str (line);

        if (nl == NULL)
            break;
        p = nl + 1;
    }

    fputs ("]}\n", stdout);
    fflush (stdout);
}

/* ---- snapshot ------------------------------------------------------------- */

static const char *position_name (int pos)
{
    switch (pos)
    {
        case POS_DEAD:     return "DEAD";
        case POS_MORTAL:   return "MORTAL";
        case POS_INCAP:    return "INCAP";
        case POS_STUNNED:  return "STUNNED";
        case POS_SLEEPING: return "SLEEPING";
        case POS_RESTING:  return "RESTING";
        case POS_SITTING:  return "SITTING";
        case POS_FIGHTING: return "FIGHTING";
        case POS_STANDING: return "STANDING";
        default:           return "UNKNOWN";
    }
}

/* First word of ch->name (ROM keys/searches characters by their first word). */
static void char_key (const CHAR_DATA *ch, char *buf, size_t cap)
{
    const char *src = (ch->name != NULL) ? ch->name : "";
    size_t i = 0;
    while (src[i] != '\0' && !isspace ((unsigned char) src[i]) && i + 1 < cap)
    {
        buf[i] = src[i];
        i++;
    }
    buf[i] = '\0';
}

/* Find a connected/loaded character by name's first word, searching char_list. */
static CHAR_DATA *find_char_by_key (const char *key)
{
    CHAR_DATA *ch;
    for (ch = char_list; ch != NULL; ch = ch->next)
    {
        char buf[MAX_INPUT_LENGTH];
        char_key (ch, buf, sizeof (buf));
        if (str_cmp (buf, key) == 0)
            return ch;
    }
    return NULL;
}

static void emit_char_snapshot (CHAR_DATA *ch)
{
    char key[MAX_INPUT_LENGTH];
    char_key (ch, key, sizeof (key));

    fputs ("{\"key\":", stdout);
    json_str (key);

    if (ch->in_room != NULL)
        printf (",\"room\":%d", ch->in_room->vnum);
    else
        fputs (",\"room\":null", stdout);

    fputs (",\"position\":", stdout);
    json_str (position_name (ch->position));

    printf (",\"hp\":%d,\"max_hp\":%d,\"mana\":%d,\"move\":%d",
            ch->hit, ch->max_hit, ch->mana, ch->move);
    printf (",\"level\":%d,\"align\":%d,\"gold\":%ld",
            ch->level, ch->alignment, ch->gold);
    printf (",\"eff_hitroll\":%d", GET_HITROLL (ch));
    printf (",\"eff_damroll\":%d", GET_DAMROLL (ch));
    printf (",\"eff_ac\":[%d,%d,%d,%d]",
            GET_AC (ch, AC_PIERCE), GET_AC (ch, AC_BASH),
            GET_AC (ch, AC_SLASH), GET_AC (ch, AC_EXOTIC));

    /* fighting: target's first-word name, or null. */
    if (ch->fighting != NULL)
    {
        char fkey[MAX_INPUT_LENGTH];
        char_key (ch->fighting, fkey, sizeof (fkey));
        fputs (",\"fighting\":", stdout);
        json_str (fkey);
    }
    else
    {
        fputs (",\"fighting\":null", stdout);
    }

    /* affects: skill_table[paf->type].name for each affect (unsorted). */
    fputs (",\"affects\":[", stdout);
    {
        AFFECT_DATA *paf;
        int first = 1;
        for (paf = ch->affected; paf != NULL; paf = paf->next)
        {
            const char *name = NULL;
            if (paf->type >= 0 && paf->type < MAX_SKILL)
                name = skill_table[paf->type].name;
            if (!first)
                putchar (',');
            first = 0;
            json_str (name);
        }
    }
    putchar (']');

    /* affect_flags: names of bits set in ch->affected_by (via affect_flags[]). */
    fputs (",\"affect_flags\":[", stdout);
    {
        int i, first = 1;
        for (i = 0; affect_flags[i].name != NULL; i++)
        {
            if (IS_SET (ch->affected_by, affect_flags[i].bit))
            {
                if (!first)
                    putchar (',');
                first = 0;
                json_str (affect_flags[i].name);
            }
        }
    }
    putchar (']');

    /* inventory: obj->pIndexData->vnum in carrying-list order. */
    fputs (",\"inventory\":[", stdout);
    {
        OBJ_DATA *obj;
        int first = 1;
        for (obj = ch->carrying; obj != NULL; obj = obj->next_content)
        {
            if (!first)
                putchar (',');
            first = 0;
            printf ("%d", obj->pIndexData->vnum);
        }
    }
    putchar (']');

    /* equipment: {str(iWear): vnum} for each occupied wear slot. */
    fputs (",\"equipment\":{", stdout);
    {
        int iWear, first = 1;
        for (iWear = 0; iWear < MAX_WEAR; iWear++)
        {
            OBJ_DATA *obj = get_eq_char (ch, iWear);
            if (obj != NULL)
            {
                if (!first)
                    putchar (',');
                first = 0;
                printf ("\"%d\":%d", iWear, obj->pIndexData->vnum);
            }
        }
    }
    putchar ('}');

    putchar ('}');
}

static void emit_room_snapshot (int vnum)
{
    ROOM_INDEX_DATA *room = get_room_index (vnum);

    printf ("{\"vnum\":%d,\"people\":[", vnum);
    if (room != NULL)
    {
        CHAR_DATA *ch;
        int first = 1;
        for (ch = room->people; ch != NULL; ch = ch->next_in_room)
        {
            char key[MAX_INPUT_LENGTH];
            char_key (ch, key, sizeof (key));
            if (!first)
                putchar (',');
            first = 0;
            json_str (key);
        }
    }
    fputs ("],\"contents\":[", stdout);
    if (room != NULL)
    {
        OBJ_DATA *obj;
        int first = 1;
        for (obj = room->contents; obj != NULL; obj = obj->next_content)
        {
            if (!first)
                putchar (',');
            first = 0;
            printf ("%d", obj->pIndexData->vnum);
        }
    }
    fputs ("]}", stdout);
}

/* __snapshot chars=<a,b> rooms=<v,v> */
static void handle_snapshot (char *args)
{
    char chars_csv[MAX_INPUT_LENGTH] = "";
    char rooms_csv[MAX_INPUT_LENGTH] = "";

    /* Parse `chars=...` and `rooms=...` tokens (order-independent). */
    char *tok;
    for (tok = strtok (args, " \t"); tok != NULL; tok = strtok (NULL, " \t"))
    {
        if (strncmp (tok, "chars=", 6) == 0)
            strncpy (chars_csv, tok + 6, sizeof (chars_csv) - 1);
        else if (strncmp (tok, "rooms=", 6) == 0)
            strncpy (rooms_csv, tok + 6, sizeof (rooms_csv) - 1);
    }

    fputs ("{\"type\":\"snapshot\",\"chars\":[", stdout);
    {
        char *p, *save;
        int first = 1;
        for (p = strtok_r (chars_csv, ",", &save); p != NULL;
             p = strtok_r (NULL, ",", &save))
        {
            CHAR_DATA *ch = find_char_by_key (p);
            if (ch == NULL)
                continue;
            if (!first)
                putchar (',');
            first = 0;
            emit_char_snapshot (ch);
        }
    }
    fputs ("],\"rooms\":[", stdout);
    {
        char *p, *save;
        int first = 1;
        for (p = strtok_r (rooms_csv, ",", &save); p != NULL;
             p = strtok_r (NULL, ",", &save))
        {
            if (!first)
                putchar (',');
            first = 0;
            emit_room_snapshot (atoi (p));
        }
    }
    fputs ("]}\n", stdout);
    fflush (stdout);
}

/* ---- character bootstrap -------------------------------------------------- */

/*
 * Create a fresh PC in `start_room` named `name`. Mirrors the minimal new-player
 * finalization from nanny.c CON_READ_MOTD (reset_char → level/hp/mana → room),
 * but places the char in the scenario's start room instead of the school.
 */
static CHAR_DATA *make_test_char (const char *name, int start_room, int level)
{
    CHAR_DATA *ch = new_char ();
    ROOM_INDEX_DATA *room;

    ch->pcdata = new_pcdata ();
    ch->name = str_dup (name);
    ch->id = 0;
    ch->race = race_lookup ("human");
    ch->level = 0;             /* triggers the "new player" init below */
    ch->trust = 0;
    ch->sex = SEX_MALE;
    ch->class = 0;             /* mage (class_table[0]) */
    ch->act = PLR_NOSUMMON;
    ch->comm = COMM_COMBINE | COMM_PROMPT;
    ch->prompt = str_dup ("<%hhp %mm %vmv> ");
    ch->pcdata->pwd = str_dup ("");
    ch->pcdata->bamfin = str_dup ("");
    ch->pcdata->bamfout = str_dup ("");
    ch->pcdata->title = str_dup ("");
    {
        int stat;
        for (stat = 0; stat < MAX_STATS; stat++)
            ch->perm_stat[stat] = 13;
        ch->perm_stat[class_table[ch->class].attr_prime] += 3;
    }
    ch->pcdata->condition[COND_THIRST] = 48;
    ch->pcdata->condition[COND_FULL]   = 48;
    ch->pcdata->condition[COND_HUNGER] = 48;

    /* Attach the synthetic descriptor so ROM output funcs capture into us. */
    memset (&shim_desc, 0, sizeof (shim_desc));
    shim_desc.connected = CON_PLAYING;
    shim_desc.outbuf    = shim_outbuf;
    shim_desc.outsize   = SHIM_OUTBUF_SIZE;
    shim_desc.outtop    = 0;
    shim_desc.ansi      = FALSE;
    shim_desc.character = ch;
    shim_desc.host      = str_dup ("diffshim");
    ch->desc = &shim_desc;

    ch->next = char_list;
    char_list = ch;

    reset_char (ch);

    /* New-player level-1 init (subset of nanny.c). */
    ch->level   = 1;
    ch->exp     = exp_per_level (ch, ch->pcdata->points);
    ch->hit     = ch->max_hit;
    ch->mana    = ch->max_mana;
    ch->move    = ch->max_move;
    ch->train   = 3;
    ch->practice = 5;

    if (level > 1)
        ch->level = (sh_int) level;

    room = get_room_index (start_room);
    if (room == NULL)
        room = get_room_index (ROOM_VNUM_TEMPLE);
    char_to_room (ch, room);

    return ch;
}

/* ---- main ----------------------------------------------------------------- */

int main (int argc, char **argv)
{
    char line[4 * MAX_INPUT_LENGTH];
    CHAR_DATA *ch = NULL;

    (void) argc;
    (void) argv;

    /* boot_db() (and the OLD_RAND init_mm) read area.lst / current_time from
     * CWD; chdir into the repaired area overlay (see Makefile.diffshim). */
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

    /* Deterministic clock before boot_db()/init_mm() consult it. */
    current_time = (time_t) 0;
    boot_db ();

    /* Drive scripted commands from stdin. */
    while (fgets (line, sizeof (line), stdin) != NULL)
    {
        /* Strip trailing newline(s). */
        size_t len = strlen (line);
        while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r'))
            line[--len] = '\0';

        if (line[0] == '\0')
            continue;

        if (strncmp (line, "boot ", 5) == 0)
        {
            long seed = 0;
            int start_room = ROOM_VNUM_TEMPLE;
            int level = 1;
            char name[MAX_INPUT_LENGTH] = "Tester";
            char *tok;

            for (tok = strtok (line + 5, " \t"); tok != NULL;
                 tok = strtok (NULL, " \t"))
            {
                if (strncmp (tok, "seed=", 5) == 0)
                    seed = atol (tok + 5);
                else if (strncmp (tok, "start_room=", 11) == 0)
                    start_room = atoi (tok + 11);
                else if (strncmp (tok, "level=", 6) == 0)
                    level = atoi (tok + 6);
                else if (strncmp (tok, "char=", 5) == 0)
                    strncpy (name, tok + 5, sizeof (name) - 1);
            }

            /* Seed OLD_RAND deterministically: init_mm() seeds from
             * current_time (piState[0] = current_time & ((1<<30)-1)), which
             * matches the Python seed_mm(seed) convention exactly. */
            current_time = (time_t) seed;
            init_mm ();

            ch = make_test_char (name, start_room, level);
            continue;
        }

        if (strncmp (line, "__snapshot", 10) == 0)
        {
            char *args = line + 10;
            while (*args == ' ' || *args == '\t')
                args++;
            handle_snapshot (args);
            continue;
        }

        /* __seed=<n>: reseed OLD_RAND mid-run, same convention as boot
         * (init_mm seeds piState from current_time). Scopes the next
         * commands' RNG to a known stream position. */
        if (strncmp (line, "__seed=", 7) == 0)
        {
            current_time = (time_t) atol (line + 7);
            init_mm ();
            continue;
        }

        /* __mload=<vnum>: spawn a fresh mob into the PC's current room
         * (ROM create_mobile + char_to_room). */
        if (strncmp (line, "__mload=", 8) == 0)
        {
            int vnum = atoi (line + 8);
            MOB_INDEX_DATA *mi = get_mob_index (vnum);
            if (mi != NULL && ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob = create_mobile (mi);
                char_to_room (mob, ch->in_room);
            }
            continue;
        }

        /* __tick: run one violence_update() pulse (combat round only),
         * capturing the PC's combat output. */
        if (strncmp (line, "__tick", 6) == 0)
        {
            shim_reset_output ();
            violence_update ();
            emit_output ();
            continue;
        }

        /* Ordinary ROM command: capture its output. */
        if (ch == NULL)
            continue;
        shim_reset_output ();
        interpret (ch, line);
        emit_output ();
    }

    return 0;
}
