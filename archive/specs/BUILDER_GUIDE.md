# QuickMUD Builder's Guide

Complete guide to Online Creation (OLC) system and builder tools for QuickMUD ROM 2.4.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [OLC Editors](#olc-editors)
3. [Builder Tools](#builder-tools)
4. [Quick Reference](#quick-reference)

---

## Getting Started

### Requirements

- Character level 51+ (LEVEL_HERO)
- Builder permissions for the area you want to edit

### Security Levels

Builder access is granted through:
1. **Security level**: Your security level >= area security level
2. **Builders list**: Your name appears in the area's builders list

Use `@aedit` to manage area builders and security.

---

## OLC Editors

All editors use the same basic pattern:
1. Start editing: `@<editor> <vnum>`
2. Make changes: `<command> <value>`
3. Save and exit: `done`
4. Persist to disk: `@asave <mode>`

### Common Commands (All Editors)

- `show` - Display current state
- `done` / `exit` - Exit editor
- `@asave` - Save from within editor
- Empty input - Show syntax help

---

### @redit - Room Editor

Edit room properties, exits, and resets.

**Starting**:
```
@redit           # Edit current room
@redit <vnum>    # Edit specific room
```

**Basic Commands**:
```
name <text>              # Set room name
desc <text>              # Set room description
sector <type>            # Set sector (inside, city, field, forest, etc.)
owner <name|none>        # Set room owner
heal <number>            # Set heal rate (default 100)
mana <number>            # Set mana rate (default 100)
clan <name>              # Set clan ownership
format                   # Auto-format description text
```

**Room Flags**:
```
room <flag1 flag2...>    # Toggle room flags
                         # Flags: dark, no_mob, indoors, private, safe, etc.
```

**Exits**:
```
<dir> create <vnum>      # Create one-way exit
<dir> link <vnum>        # Create two-way linked exit
<dir> dig <vnum>         # Create room and link to it
<dir> delete             # Remove exit
<dir> keyword <text>     # Set door keywords
<dir> desc <text>        # Set exit description
<dir> key <vnum>         # Set key vnum
<dir> flags <flags>      # Set exit flags (door, closed, locked, etc.)
```

**Extra Descriptions**:
```
ed list                  # List all extra descriptions
ed add <keyword>         # Add extra description
ed desc <keyword> <text> # Set extra description text
ed delete <keyword>      # Remove extra description
```

**Resets**:
```
mreset add <mob vnum>    # Add mob reset to room
oreset add <obj vnum>    # Add object reset to room
```

---

### @aedit - Area Editor

Edit area metadata and builder permissions.

**Starting**:
```
@aedit <area vnum>
```

**Commands**:
```
name <text>              # Set area name
credits <text>           # Set author/credits
security <0-9>           # Set security level
builder add <name>       # Add builder to list
builder remove <name>    # Remove builder from list
vnum <number>            # Set area vnum
lvnum <number>           # Set lower vnum range
uvnum <number>           # Set upper vnum range
filename <file>          # Set filename
show                     # Display area info
done                     # Exit editor
```

**Example**:
```
@aedit 1
name The Enchanted Forest
credits Nostoi
security 5
builder add JohnBuilder
builder add JaneBuilder
done
@asave changed
```

---

### @oedit - Object Editor

Create and edit object prototypes.

**Starting**:
```
@oedit <vnum>            # Edit existing or create new
```

**Basic Commands**:
```
name <keywords>          # Set object keywords (for targeting)
short <text>             # Set short description
long <text>              # Set long description (ground)
type <type>              # Set item type (weapon, armor, treasure, etc.)
level <num>              # Set object level
weight <num>             # Set weight
cost <num>               # Set cost in gold
material <name>          # Set material type
```

**Values** (type-specific):
```
v0 <number>              # Value field 0
v1 <number>              # Value field 1
v2 <number>              # Value field 2
v3 <number>              # Value field 3
v4 <number>              # Value field 4
```

*Note: Value meanings depend on item type (see ROM documentation)*

**Extra Descriptions**:
```
ed list                  # List extra descriptions
ed add <keyword>         # Add extra description
ed desc <keyword> <text> # Set description text
ed delete <keyword>      # Remove extra description
```

**Example** (Creating a sword):
```
@oedit 1050
name sword longsword blade
short a gleaming longsword
long A gleaming longsword has been left here.
type weapon
level 10
weight 8
cost 100
material steel
v0 0                     # Weapon class
v1 2                     # Number of dice
v2 8                     # Size of dice
v3 1                     # Damage type (slash)
done
@asave area
```

---

### @medit - Mobile Editor

Create and edit mobile (NPC) prototypes.

**Starting**:
```
@medit <vnum>            # Edit existing or create new
```

**Basic Commands**:
```
name <text>              # Set player name
short <text>             # Set short description
long <text>              # Set long description (standing)
desc <text>              # Set detailed description (look at mob)
level <num>              # Set mobile level (1+)
align <num>              # Set alignment (-1000 to 1000)
race <name>              # Set race
sex <male|female|neutral|none> # Set sex
```

**Combat Stats**:
```
hitroll <num>            # Set hit bonus
damroll <num>            # Set damage bonus
hit <dice>               # Set HP dice (e.g., 5d8+20)
mana <dice>              # Set mana dice (e.g., 100d10+50)
dam <dice>               # Set damage dice (e.g., 2d6+4)
damtype <type>           # Set damage type (slash, pierce, etc.)
ac <dice>                # Set armor class dice
```

**Other**:
```
wealth <num>             # Set gold (0+)
group <num>              # Set group number
material <name>          # Set material
show                     # Display mobile info
done                     # Exit editor
```

**Example** (Creating a guard):
```
@medit 1001
name guard city soldier
short a city guard
long A city guard stands here watching for trouble.
desc He is wearing chainmail and carrying a sword.
level 15
align 500
race human
sex male
hitroll 10
hit 15d8+50
dam 2d6+3
damtype slash
wealth 200
done
@asave area
```

---

### @hedit - Help Editor

Create and edit help file entries.

**Starting**:
```
@hedit <keyword>         # Edit existing or create new
@hedit new               # Create new entry
```

**Commands**:
```
keywords <word word...>  # Set keywords (searchable terms)
text <content>           # Set help text content
level <num>              # Set minimum level to see (0+ for all)
show                     # Display help entry
done                     # Save to memory (use @hesave to write to disk)
```

**Example**:
```
@hedit magic
keywords magic spells casting
text Magic in QuickMUD requires mana and practice. See 'help spells' for a list.
level 0
done
@hesave
```

---

### @asave - Save System

Persist OLC changes to disk.

**Modes**:
```
@asave <vnum>            # Save specific area by vnum
@asave list              # Save area.lst file
@asave area              # Save currently edited area
@asave changed           # Save all modified areas
@asave world             # Save all areas you have access to
```

**Important**: Changes in editors are only in memory until you `@asave`!

---

## Builder Tools

### @rstat - Room Statistics

Display detailed room information.

```
@rstat                   # Current room
@rstat <vnum>            # Specific room
```

**Shows**: Name, vnum, description, area, sector, flags, heal/mana rates, owner, clan, exits, extra descriptions

---

### @ostat - Object Statistics

Display detailed object prototype information.

```
@ostat <vnum>
```

**Shows**: Name, vnum, keywords, descriptions, type, level, weight, cost, material, values, area, extra descriptions, affects

---

### @mstat - Mobile Statistics

Display detailed mobile prototype information.

```
@mstat <vnum>
```

**Shows**: Name, vnum, descriptions, level, alignment, race, sex, combat stats, dice values, wealth, area, special functions

---

### @goto - Teleport

Teleport to any room by vnum.

```
@goto <vnum>
```

**Example**:
```
@goto 3001               # Teleport to Midgaard Temple
```

---

### @vlist - List Vnums

List all rooms, mobiles, and objects in an area.

```
@vlist                   # Current area
@vlist <area vnum>       # Specific area
```

**Output**: Lists vnums and names (limited to 20 per category, shows totals)

**Useful for**: Finding available vnums, seeing what exists in an area

---

### @hesave - Save Help Files

Write help file changes to disk.

```
@hesave
```

Saves all help entries to `data/help.json`. Use after editing help entries with `@hedit`.

---

## Quick Reference

### Complete Builder Command List

**OLC Editors**:
- `@redit` - Room editor
- `@aedit` - Area editor
- `@oedit` - Object editor
- `@medit` - Mobile editor
- `@hedit` - Help editor

**Save Commands**:
- `@asave` - Save areas
- `@hesave` - Save help files

**Inspection Tools**:
- `@rstat` - Room statistics
- `@ostat` - Object statistics
- `@mstat` - Mobile statistics
- `@vlist` - List area vnums

**Navigation**:
- `@goto` - Teleport to room

---

### Common Workflows

**Creating a New Area**:
1. Use `@aedit <vnum>` to create area metadata
2. Set name, credits, security, builders
3. Create rooms with `@redit <vnum>`
4. Create mobs with `@medit <vnum>`
5. Create objects with `@oedit <vnum>`
6. Add resets to rooms with `@redit` → `mreset`/`oreset`
7. Save everything with `@asave changed`

**Inspecting Existing Content**:
1. Use `@vlist` to see what exists in an area
2. Use `@rstat <vnum>` to examine rooms
3. Use `@ostat <vnum>` to examine objects
4. Use `@mstat <vnum>` to examine mobs
5. Use `@goto <vnum>` to visit locations

**Editing Help Files**:
1. Use `@hedit <keyword>` to edit/create entry
2. Set keywords and text
3. Use `done` to save to memory
4. Use `@hesave` to write to disk

---

### Tips and Best Practices

1. **Always save**: Use `@asave changed` regularly to persist your work
2. **Use @vlist**: Check available vnums before creating new content
3. **Test resets**: After adding mob/object resets, observe a reset cycle
4. **Security**: Set appropriate security levels to control who can edit
5. **Descriptions**: Use `format` in @redit to auto-wrap long descriptions
6. **Linked exits**: Use `link` instead of two separate `create` commands
7. **Inspect first**: Use @stat commands before editing to see current state
8. **Help files**: Keep help entries concise and cross-reference related topics

---

### Troubleshooting

**"Insufficient security"**:
- Check area security level with `@aedit <vnum>` → `show`
- Ask an admin to add you to builders list or raise your security level

**"That vnum is not assigned to an area"**:
- Each area has a vnum range (lvnum to uvnum)
- Check area ranges with `@vlist <area vnum>`
- Use vnums within the area's range

**Changes don't persist after restart**:
- You must use `@asave` to write changes to disk
- Use `@asave changed` to save all modified areas

**Can't find a room/mob/object**:
- Use `@vlist` to see what exists in an area
- Check if vnum is in the correct area's range
- Verify the prototype exists with @stat commands

---

## ROM Parity

All OLC editors maintain full compatibility with ROM 2.4:
- Command syntax matches ROM exactly
- Security model identical to ROM
- Save format compatible with ROM area files (JSON conversion)
- Field validation matches ROM constraints

**ROM C Source References**:
- @redit: `src/olc.c:redit`
- @aedit: `src/olc.c:410-469`
- @oedit: `src/olc.c:532-584`
- @medit: `src/olc.c:588-650`
- @asave: `src/olc_save.c:76-1134`

---

**Happy Building!** 🏗️

For questions or issues, consult the ROM 2.4 documentation or ask your MUD administrators.
