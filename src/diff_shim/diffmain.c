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
void char_update     (void);
void mobile_update   (void);

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
/*
 * Resolve a snapshot char key to a specific instance, scoped to the watched
 * rooms. A keyword like "drunk" can match multiple instances game-wide (a
 * reset-spawned one in its home room plus one __mload'd into the scenario room);
 * a global first-match would snapshot whichever was created most recently, which
 * differs from the Python replay's explicit instance. Scoping to the watched
 * rooms makes the lookup unambiguous: the watched char is the one the scenario
 * is actually observing. No global fallback — if the key is not in a watched
 * room it is omitted (the Python side omits it too).
 */
static CHAR_DATA *find_char_by_key (const char *key, const int *room_vnums, int n_rooms)
{
    CHAR_DATA *ch;
    for (ch = char_list; ch != NULL; ch = ch->next)
    {
        char buf[MAX_INPUT_LENGTH];
        int i, in_watched = 0;

        char_key (ch, buf, sizeof (buf));
        if (str_cmp (buf, key) != 0)
            continue;

        if (n_rooms <= 0)
            return ch;                       /* unscoped: preserve old behavior */
        if (ch->in_room == NULL)
            continue;
        for (i = 0; i < n_rooms; i++)
            if (ch->in_room->vnum == room_vnums[i])
            {
                in_watched = 1;
                break;
            }
        if (in_watched)
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
    printf (",\"level\":%d,\"align\":%d,\"gold\":%ld,\"silver\":%ld",
            ch->level, ch->alignment, ch->gold, ch->silver);
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

    /* inventory: obj->pIndexData->vnum for carried, non-equipped objects in
     * carrying-list order. Equipment is emitted separately below. */
    fputs (",\"inventory\":[", stdout);
    {
        OBJ_DATA *obj;
        int first = 1;
        for (obj = ch->carrying; obj != NULL; obj = obj->next_content)
        {
            if (obj->wear_loc != WEAR_NONE)
                continue;
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

    /* master: first-word key of ch->master, or null.
     * ROM src/act_comm.c:1591 add_follower sets ch->master = master.
     * Emitted so charm-lifecycle scenarios can verify master survives
     * affect expiry (affect_remove does NOT call stop_follower). */
    if (ch->master != NULL)
    {
        char mkey[MAX_INPUT_LENGTH];
        char_key (ch->master, mkey, sizeof (mkey));
        fputs (",\"master\":", stdout);
        json_str (mkey);
    }
    else
    {
        fputs (",\"master\":null", stdout);
    }

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

    /* Parse the watched room vnums into an int array (from a copy, so the
     * destructive strtok below does not clobber rooms_csv, which the rooms
     * output loop re-parses). Used to scope the char-key lookup. */
    int watched_rooms[64];
    int n_watched = 0;
    {
        char rooms_copy[MAX_INPUT_LENGTH];
        char *p, *save;
        strncpy (rooms_copy, rooms_csv, sizeof (rooms_copy) - 1);
        rooms_copy[sizeof (rooms_copy) - 1] = '\0';
        for (p = strtok_r (rooms_copy, ",", &save);
             p != NULL && n_watched < 64;
             p = strtok_r (NULL, ",", &save))
            watched_rooms[n_watched++] = atoi (p);
    }

    fputs ("{\"type\":\"snapshot\",\"chars\":[", stdout);
    {
        char *p, *save;
        int first = 1;
        for (p = strtok_r (chars_csv, ",", &save); p != NULL;
             p = strtok_r (NULL, ",", &save))
        {
            CHAR_DATA *ch = find_char_by_key (p, watched_rooms, n_watched);
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

        /* __hour=<n>: set the in-game hour directly. Shop commands read
         * time_info.hour (src/act_obj.c:find_keeper), while OLD_RAND remains
         * controlled by __seed. */
        if (strncmp (line, "__hour=", 7) == 0)
        {
            time_info.hour = atoi (line + 7);
            continue;
        }

        /* __gold=<n>: set the PC's gold directly (no RNG). */
        if (strncmp (line, "__gold=", 7) == 0)
        {
            if (ch != NULL)
                ch->gold = atol (line + 7);
            continue;
        }

        /* __silver=<n>: set the PC's silver directly (no RNG). */
        if (strncmp (line, "__silver=", 9) == 0)
        {
            if (ch != NULL)
                ch->silver = atol (line + 9);
            continue;
        }

        /* __mana=<n>: set the PC's mana (and max_mana if lower) directly.
         * Needed for multi-spell scenarios where the harness default 100 mana
         * is insufficient (e.g. sanctuary + haste at high level). */
        if (strncmp (line, "__mana=", 7) == 0)
        {
            if (ch != NULL)
            {
                int val = atoi (line + 7);
                ch->mana = val;
                if (ch->max_mana < val)
                    ch->max_mana = val;
            }
            continue;
        }

        /* __hp=<n>: set the PC's hit (and max_hit if lower) directly.
         * Used by regen scenarios that need a character at below-max HP. */
        if (strncmp (line, "__hp=", 5) == 0)
        {
            if (ch != NULL)
            {
                int val = atoi (line + 5);
                ch->hit = val;
                if (ch->max_hit < val)
                    ch->max_hit = val;
            }
            continue;
        }

        /* __move=<n>: set the PC's move (and max_move if lower) directly.
         * Mirrors __hp= and __mana= for the movement resource. */
        if (strncmp (line, "__move=", 7) == 0)
        {
            if (ch != NULL)
            {
                int val = atoi (line + 7);
                ch->move = val;
                if (ch->max_move < val)
                    ch->max_move = val;
            }
            continue;
        }

        /* __level=<n>: set the PC's level directly (no RNG).  Used by
         * generated skill-command scenarios where ROM get_skill gates learned
         * skills by class level. */
        if (strncmp (line, "__level=", 8) == 0)
        {
            if (ch != NULL)
                ch->level = atoi (line + 8);
            continue;
        }

        /* __char_class=<n>: set the PC's class index directly (0=mage,
         * 1=cleric, 2=thief, 3=warrior).  Used by regen scenarios that
         * exercise class-specific hit_gain/mana_gain paths. */
        if (strncmp (line, "__char_class=", 13) == 0)
        {
            if (ch != NULL)
                ch->class = atoi (line + 13);
            continue;
        }

        /* __char_position=<n>: set the PC's position directly (e.g.
         * 4=sleeping, 5=resting, 8=standing).  Used by regen scenarios that
         * exercise position-specific hit_gain/mana_gain/move_gain branches.
         * Mirrors the Python-side __char_position handler in pyreplay.py. */
        if (strncmp (line, "__char_position=", 16) == 0)
        {
            if (ch != NULL)
                ch->position = atoi (line + 16);
            continue;
        }

        /* __goto=<vnum>: move the PC to a room without command output.
         * Harness-only positioning primitive for generated scenarios that need
         * a specific stock fixture (e.g. a keyed door) without replaying a long
         * unrelated walking route. */
        if (strncmp (line, "__goto=", 7) == 0)
        {
            ROOM_INDEX_DATA *room = get_room_index (atoi (line + 7));
            if (ch != NULL && room != NULL)
            {
                char_from_room (ch);
                char_to_room (ch, room);
            }
            continue;
        }

        /* __mob_gold=<n>: set the first NPC in the room's gold directly.
         * Used to control keeper treasury for sell-path differential tests. */
        if (strncmp (line, "__mob_gold=", 11) == 0)
        {
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL; mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        mob->gold = atol (line + 11);
                        break;
                    }
                }
            }
            continue;
        }

        /* __mob_silver=<n>: set the first NPC in the room's silver directly.
         * Companion to __mob_gold for zeroing out a shopkeeper's treasury. */
        if (strncmp (line, "__mob_silver=", 13) == 0)
        {
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL; mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        mob->silver = atol (line + 13);
                        break;
                    }
                }
            }
            continue;
        }

        /* __cond_full=<n>: set the PC's condition[FULL] directly (no RNG). */
        if (strncmp (line, "__cond_full=", 12) == 0)
        {
            if (ch != NULL && ch->pcdata != NULL)
                ch->pcdata->condition[COND_FULL] = atoi (line + 12);
            continue;
        }

        /* __cond_thirst=<n>: set the PC's condition[THIRST] directly (no RNG). */
        if (strncmp (line, "__cond_thirst=", 14) == 0)
        {
            if (ch != NULL && ch->pcdata != NULL)
                ch->pcdata->condition[COND_THIRST] = atoi (line + 14);
            continue;
        }

        /* __cond_hunger=<n>: set the PC's condition[HUNGER] directly (no RNG).
         * Mirrors the Python-side __cond_hunger handler in pyreplay.py. */
        if (strncmp (line, "__cond_hunger=", 14) == 0)
        {
            if (ch != NULL && ch->pcdata != NULL)
                ch->pcdata->condition[COND_HUNGER] = atoi (line + 14);
            continue;
        }

        /* __cond_drunk=<n>: set the PC's condition[DRUNK] directly (no RNG).
         * Mirrors the Python-side __cond_drunk handler in pyreplay.py. */
        if (strncmp (line, "__cond_drunk=", 13) == 0)
        {
            if (ch != NULL && ch->pcdata != NULL)
                ch->pcdata->condition[COND_DRUNK] = atoi (line + 13);
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

        /* __mob_hold=<vnum>: spawn a fresh, empty drink container and equip it
         * to the first NPC in the PC's current room's HOLD slot. The container
         * is emptied (value[1]=0) so the do_pour liquid-type guard passes for
         * any source liquid. */
        if (strncmp (line, "__mob_hold=", 11) == 0)
        {
            int vnum = atoi (line + 11);
            OBJ_INDEX_DATA *oi = get_obj_index (vnum);
            if (oi != NULL && ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people;
                     mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        OBJ_DATA *obj = create_object (oi, 0);
                        obj->value[1] = 0;
                        obj_to_char (obj, mob);
                        equip_char (mob, obj, WEAR_HOLD);
                        break;
                    }
                }
            }
            continue;
        }

        /* __mob_carry=<vnum>: spawn a fresh object and add it to the first
         * NPC's carry list (obj_to_char only — NOT equipped).  Used to stock
         * a shopkeeper's inventory so do_buy can find the item.  Mirrors the
         * Python-side __mob_carry handler in pyreplay.py. */
        if (strncmp (line, "__mob_carry=", 12) == 0)
        {
            int vnum = atoi (line + 12);
            OBJ_INDEX_DATA *oi = get_obj_index (vnum);
            if (oi != NULL && ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people;
                     mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        OBJ_DATA *obj = create_object (oi, 0);
                        obj_to_char (obj, mob);
                        break;
                    }
                }
            }
            continue;
        }

        /* __mob_prog=<trig_name>:<trig_phrase>:<code>: inject a mob program
         * into the first NPC's mprogs list at runtime.  trig_name must match
         * an mprog_flags entry (e.g. "speech").  trig_phrase is the keyword
         * or percent string.  code is the raw interpreter text.  Mirrors the
         * Python-side __mob_prog handler in pyreplay.py. */
        if (strncmp (line, "__mob_prog=", 11) == 0)
        {
            char *rest = line + 11;
            char *colon1, *colon2;
            int trigger;
            CHAR_DATA *mob;
            MPROG_LIST *prog;

            colon1 = strchr (rest, ':');
            if (colon1 == NULL) { continue; }
            colon2 = strchr (colon1 + 1, ':');
            if (colon2 == NULL) { continue; }

            /* isolate trig_name, look up flag value */
            *colon1 = '\0';
            trigger = flag_lookup (rest, mprog_flags);
            *colon1 = ':';
            if (trigger == NO_FLAG) { continue; }

            if (ch == NULL || ch->in_room == NULL) { continue; }
            for (mob = ch->in_room->people; mob != NULL;
                 mob = mob->next_in_room)
                if (IS_NPC (mob)) break;
            if (mob == NULL) { continue; }

            prog = alloc_perm (sizeof (*prog));
            prog->trig_type = trigger;
            /* trig_phrase: from colon1+1 up to (not including) colon2 */
            *colon2 = '\0';
            prog->trig_phrase = str_dup (colon1 + 1);
            *colon2 = ':';
            prog->vnum = 0;
            prog->code = str_dup (colon2 + 1);
            prog->next = mob->pIndexData->mprogs;
            mob->pIndexData->mprogs = prog;
            SET_BIT (mob->pIndexData->mprog_flags, trigger);
            continue;
        }

        /* __oload=<vnum>: spawn a fresh object into the PC's current room
         * (ROM create_object + obj_to_room). */
        if (strncmp (line, "__oload=", 8) == 0)
        {
            int vnum = atoi (line + 8);
            OBJ_INDEX_DATA *oi = get_obj_index (vnum);
            if (oi != NULL && ch != NULL && ch->in_room != NULL)
            {
                OBJ_DATA *obj = create_object (oi, 0);
                obj_to_room (obj, ch->in_room);
            }
            continue;
        }

        /* __learn=<skill/spell name>: teach the PC the skill at 100% so it can
         * be cast/used. Mirrors nanny.c's class group_add (which make_test_char
         * deliberately skips) but scoped per-scenario, so the existing melee
         * scenario keeps an empty skill set. skill_lookup canonicalizes the
         * name on this side; the Python replay resolves the same name through
         * skill_registry. learned == 100 means deterministic success AND no
         * check_improve RNG (src/skills.c:932 early-return), so the only RNG a
         * cast draws is do_cast's number_percent success roll + the spell's own
         * draws — symmetric with Python. No output. */
        if (strncmp (line, "__learn=", 8) == 0)
        {
            if (ch != NULL && ch->pcdata != NULL)
            {
                int sn = skill_lookup (line + 8);
                if (sn >= 0)
                    ch->pcdata->learned[sn] = 100;
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

        /* __aggr_update: run one aggr_update() pulse (src/update.c:1077) —
         * wakes AGGRESSIVE mobs and launches multi_hit at an eligible PC in
         * the room.  Mirrors the Python-side __aggr_update handler in
         * pyreplay.py (mud.ai.aggressive.aggressive_update).  Captures the
         * mob's opening combat output. */
        if (strncmp (line, "__aggr_update", 13) == 0)
        {
            shim_reset_output ();
            aggr_update ();
            emit_output ();
            continue;
        }

        /* __char_update: run one char_update() pulse (regen, conditions,
         * affect ticks, idle timer) for all characters.  Mirrors the Python-
         * side __char_update handler in pyreplay.py. */
        if (strncmp (line, "__char_update", 13) == 0)
        {
            shim_reset_output ();
            char_update ();
            emit_output ();
            continue;
        }

        /* __mob_position=<pos>: set the first NPC in the room's position to
         * <pos> (integer, e.g. 5=resting, 8=standing).  Used to place a mob
         * in a non-default position so that TRIG_EXIT and TRIG_GREET are
         * gated out (they check mob->position == pIndexData->default_pos)
         * while TRIG_EXALL and TRIG_GRALL still fire.  Never touches
         * pIndexData->default_pos so the gate remains meaningful.  Mirrors
         * the Python-side __mob_position handler in pyreplay.py. */
        if (strncmp (line, "__mob_position=", 15) == 0)
        {
            int new_pos = atoi (line + 15);
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        mob->position = new_pos;
                        break;
                    }
                }
            }
            continue;
        }

        /* __mob_hp=<n>: set the first NPC in the room's current hit points to
         * <n>.  Used to stage a mob below an HPCNT threshold without relying
         * on combat RNG to whittle it down.  Only touches ch->hit — max_hit
         * is unchanged so the percent formula still has a meaningful denominator.
         * Mirrors the Python-side __mob_hp handler in pyreplay.py. */
        if (strncmp (line, "__mob_hp=", 9) == 0)
        {
            int new_hp = atoi (line + 9);
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        mob->hit = new_hp;
                        break;
                    }
                }
            }
            continue;
        }

        /* __instant_kill: deliver a killing blow to the first NPC in the room
         * through ROM's damage() at dam = mob->hit + 1.  This ensures the full
         * ROM death path fires (TRIG_DEATH, group_gain, raw_kill, corpse) even
         * when the PC's attack-roll would miss.  Mirrors the Python-side
         * __instant_kill handler in pyreplay.py. */
        if (strncmp (line, "__instant_kill", 14) == 0)
        {
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        shim_reset_output ();
                        damage (ch, mob, mob->hit + 1, TYPE_HIT, DAM_BASH,
                                TRUE);
                        emit_output ();
                        break;
                    }
                }
            }
            continue;
        }

        /* __mobile_update: run one mobile_update() pulse (NPC AI, mprog
         * TRIG_RANDOM, TRIG_DELAY).  Mirrors the Python-side __mobile_update
         * handler in pyreplay.py.  ROM src/update.c:408. */
        if (strncmp (line, "__mobile_update", 15) == 0)
        {
            shim_reset_output ();
            mobile_update ();
            emit_output ();
            continue;
        }

        /* __mob_delay=N: set the first NPC in the room's mprog_delay to N.
         * Used to prime the TRIG_DELAY countdown before calling
         * __mobile_update.  Mirrors the Python-side __mob_delay handler in
         * pyreplay.py.  ROM src/mob_prog.c:mp_delay_trigger. */
        if (strncmp (line, "__mob_delay=", 12) == 0)
        {
            int new_delay = atoi (line + 12);
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        mob->mprog_delay = new_delay;
                        break;
                    }
                }
            }
            continue;
        }

        /* __add_affect=<bit>: OR the given bitmask into ch->affected_by.
         * Used to set a single AFF_* bit without a full spell AFFECT_DATA
         * entry, so the regen divisor branch fires without triggering the
         * spell-affect tick loop.  Mirrors the Python-side __add_affect
         * handler in pyreplay.py. */
        if (strncmp (line, "__add_affect=", 13) == 0)
        {
            long bit = atol (line + 13);
            if (ch != NULL)
                SET_BIT (ch->affected_by, (int) bit);
            continue;
        }

        /* __set_heal_rate=N: set the room's heal_rate multiplier (default 100).
         * hit_gain and move_gain use: gain * in_room->heal_rate / 100.
         * Mirrors the Python-side __set_heal_rate handler in pyreplay.py. */
        if (strncmp (line, "__set_heal_rate=", 16) == 0)
        {
            int rate = atoi (line + 16);
            if (ch != NULL && ch->in_room != NULL)
                ch->in_room->heal_rate = (sh_int) rate;
            continue;
        }

        /* __set_mana_rate=N: set the room's mana_rate multiplier (default 100).
         * mana_gain uses: gain * in_room->mana_rate / 100.
         * Mirrors the Python-side __set_mana_rate handler in pyreplay.py. */
        if (strncmp (line, "__set_mana_rate=", 16) == 0)
        {
            int rate = atoi (line + 16);
            if (ch != NULL && ch->in_room != NULL)
                ch->in_room->mana_rate = (sh_int) rate;
            continue;
        }

        /* __set_on=<vnum>: create a furniture object with the given vnum, place
         * it in the PC's room, and set ch->on to it.  Mirrors the Python-side
         * __set_on handler in pyreplay.py.
         * ROM src/update.c:217-218 (hit_gain), :299-300 (mana_gain),
         * :350-351 (move_gain). */
        if (strncmp (line, "__set_on=", 9) == 0)
        {
            int vnum = atoi (line + 9);
            OBJ_INDEX_DATA *oi = get_obj_index (vnum);
            if (oi != NULL && ch != NULL && ch->in_room != NULL)
            {
                OBJ_DATA *obj = create_object (oi, 0);
                obj_to_room (obj, ch->in_room);
                ch->on = obj;
            }
            continue;
        }

        /* __set_on_val3=<n>: set ch->on->value[3] (furniture HP/move bonus %).
         * Mirrors the Python-side __set_on_val3 handler in pyreplay.py. */
        if (strncmp (line, "__set_on_val3=", 14) == 0)
        {
            int val = atoi (line + 14);
            if (ch != NULL && ch->on != NULL)
                ch->on->value[3] = val;
            continue;
        }

        /* __set_on_val4=<n>: set ch->on->value[4] (furniture mana bonus %).
         * Mirrors the Python-side __set_on_val4 handler in pyreplay.py. */
        if (strncmp (line, "__set_on_val4=", 14) == 0)
        {
            int val = atoi (line + 14);
            if (ch != NULL && ch->on != NULL)
                ch->on->value[4] = val;
            continue;
        }

        /* __charm_mob=<duration>: charm the first NPC in the room — applies
         * add_follower(mob, ch) and an AFF_CHARM affect with the given duration.
         * Bypasses the spell's cast path and immunity checks so any mob can be
         * used.  Mirrors the Python-side __charm_mob handler in pyreplay.py.
         * ROM src/magic.c:1347-1390 spell_charm_person. */
        if (strncmp (line, "__charm_mob=", 12) == 0)
        {
            int dur = atoi (line + 12);
            if (ch != NULL && ch->in_room != NULL)
            {
                CHAR_DATA *mob;
                for (mob = ch->in_room->people; mob != NULL;
                     mob = mob->next_in_room)
                {
                    if (IS_NPC (mob))
                    {
                        AFFECT_DATA af;
                        add_follower (mob, ch);
                        mob->leader = ch;
                        af.where    = TO_AFFECTS;
                        af.type     = gsn_charm_person;
                        af.level    = ch->level;
                        af.duration = dur;
                        af.location = APPLY_NONE;
                        af.modifier = 0;
                        af.bitvector = AFF_CHARM;
                        affect_to_char (mob, &af);
                        break;
                    }
                }
            }
            continue;
        }

        /* __set_affect_duration=N: set duration of every active affect on the
         * test character to N.  Harness fixture to shorten ROM's fixed-duration
         * spells (e.g. armor=24) for expiration tests without 25+ ticks. */
        if (strncmp (line, "__set_affect_duration=", 22) == 0)
        {
            int dur = atoi (line + 22);
            AFFECT_DATA *paf;
            if (ch != NULL)
                for (paf = ch->affected; paf != NULL; paf = paf->next)
                    paf->duration = dur;
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
