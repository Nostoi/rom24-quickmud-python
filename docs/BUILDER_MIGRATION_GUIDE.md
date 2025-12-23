# QuickMUD Builder Migration Guide

**Version**: 2.0.0  
**For**: ROM Builders Transitioning to QuickMUD  
**Updated**: 2025-12-22

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [QuickMUD vs ROM C](#quickmud-vs-rom-c)
3. [Area File Format](#area-file-format)
4. [Converting ROM Areas](#converting-rom-areas)
5. [OLC Differences](#olc-differences)
6. [Python-Specific Features](#python-specific-features)
7. [ROM API Compatibility](#rom-api-compatibility)
8. [Testing Your Areas](#testing-your-areas)
9. [Best Practices](#best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Migration Checklist](#migration-checklist)

---

## Migration Overview

QuickMUD provides **100% ROM 2.4b behavioral parity**, meaning your ROM knowledge and building experience transfer directly. However, QuickMUD uses **JSON** for area files instead of ROM's traditional text format.

### Why Migrate to QuickMUD?

✅ **100% ROM Compatible** - Same behavior, same commands  
✅ **Modern Platform** - Python 3.10+ with async networking  
✅ **JSON World Data** - Human-readable, easy to edit  
✅ **Version Control Friendly** - Git-friendly JSON format  
✅ **Active Development** - Regular updates and improvements  
✅ **Full OLC Support** - Online creation like ROM  
✅ **ROM API** - C-compatible function names for scripts  

### Migration Paths

| Your Situation | Migration Path |
|----------------|----------------|
| **New Builder** | Start directly in QuickMUD with JSON |
| **ROM Areas** | Use conversion script (see below) |
| **Active ROM Builder** | Keep ROM, export to QuickMUD periodically |
| **ROM Scripter** | Use ROM API for compatibility |

---

## QuickMUD vs ROM C

### What's the Same (100% Parity)

| Feature | ROM C | QuickMUD |
|---------|-------|----------|
| **Combat System** | ✅ Identical | ✅ Identical |
| **Skills/Spells** | ✅ Same mechanics | ✅ Same mechanics |
| **Resets** | ✅ Same behavior | ✅ Same behavior |
| **Shops** | ✅ Same economy | ✅ Same economy |
| **Mobs/Objects** | ✅ Same flags | ✅ Same flags |
| **Area Properties** | ✅ Same fields | ✅ Same fields |
| **OLC Commands** | ✅ Same commands | ✅ Same commands |

### What's Different (Format Only)

| ROM C | QuickMUD |
|-------|----------|
| `.are` text files | `.json` JSON files |
| Custom parsers | Standard JSON |
| Manual editing risky | Validated JSON |
| Hard to version control | Git-friendly |

### What's Enhanced

| Feature | Enhancement |
|---------|-------------|
| **Error Messages** | More helpful validation |
| **OLC Editing** | Real-time validation |
| **Area Backups** | JSON is easier to backup |
| **Scripts** | Python + ROM API available |

---

## Area File Format

### ROM C Format (.are)

Traditional ROM area files use a custom text format:

```
#AREA
Midgaard~
{10 30} Midgaard The Temple of Midgaard~

#ROOMS
#3001
The Temple of Midgaard~
You are in the southern end of the temple hall...
~
0 8 0
D0
~
~
0 0 3002
S

#MOBILES
#3001
cityguard guard~
a cityguard~
A cityguard stands here, watching for trouble.
~
A human warrior wearing the uniform of the city guard.
~
human~
aggressive sentinel~
0 0 0
10 0 100
S
```

### QuickMUD JSON Format (.json)

QuickMUD uses clean, structured JSON:

```json
{
  "area": {
    "name": "Midgaard",
    "credits": "The Temple of Midgaard",
    "level_range": [10, 30],
    "builders": ["Implementor"],
    "security": 9
  },
  "rooms": [
    {
      "vnum": 3001,
      "name": "The Temple of Midgaard",
      "description": "You are in the southern end of the temple hall...",
      "sector": "inside",
      "flags": ["indoors"],
      "exits": [
        {
          "direction": "north",
          "to_room": 3002,
          "keywords": "",
          "description": ""
        }
      ]
    }
  ],
  "mobiles": [
    {
      "vnum": 3001,
      "keywords": "cityguard guard",
      "short_descr": "a cityguard",
      "long_descr": "A cityguard stands here, watching for trouble.",
      "description": "A human warrior wearing the uniform of the city guard.",
      "race": "human",
      "level": 10,
      "alignment": 0,
      "act_flags": ["aggressive", "sentinel"]
    }
  ]
}
```

### Advantages of JSON

1. **Validation** - Syntax errors caught immediately
2. **Editing** - Any text editor with JSON support
3. **Version Control** - Git can merge changes cleanly
4. **Scripts** - Easy to parse in any language
5. **Readability** - Clear structure, no parsing ambiguity

---

## Converting ROM Areas

### Automatic Conversion Script

QuickMUD includes a converter for ROM `.are` files:

```bash
# Convert single area
python scripts/convert_area.py area/midgaard.are data/areas/midgaard.json

# Convert all areas
for file in area/*.are; do
    basename=$(basename "$file" .are)
    python scripts/convert_area.py "$file" "data/areas/${basename}.json"
done
```

### Manual Conversion

If conversion script doesn't exist or needs customization:

#### Step 1: Create JSON Structure

```json
{
  "area": {
    "name": "Your Area Name",
    "credits": "Your Name",
    "level_range": [1, 51],
    "builders": ["YourName"],
    "security": 5,
    "vnums": [10000, 10099]
  },
  "rooms": [],
  "mobiles": [],
  "objects": [],
  "resets": [],
  "shops": []
}
```

#### Step 2: Convert Rooms

ROM C:
```
#3001
The Temple~
You are in the temple.
~
0 8 0
D0
~
~
0 0 3002
S
```

QuickMUD JSON:
```json
{
  "vnum": 3001,
  "name": "The Temple",
  "description": "You are in the temple.",
  "sector": "inside",
  "flags": ["indoors"],
  "exits": [
    {
      "direction": "north",
      "to_room": 3002,
      "keywords": "",
      "description": "",
      "locks": 0
    }
  ]
}
```

#### Step 3: Convert Mobiles

ROM C:
```
#3001
guard~
a guard~
A guard stands here.
~
A human guard.
~
human~
sentinel~
0 0 0
10 0 100
```

QuickMUD JSON:
```json
{
  "vnum": 3001,
  "keywords": "guard",
  "short_descr": "a guard",
  "long_descr": "A guard stands here.",
  "description": "A human guard.",
  "race": "human",
  "level": 10,
  "alignment": 0,
  "hitroll": 0,
  "act_flags": ["sentinel"]
}
```

#### Step 4: Convert Objects

ROM C:
```
#1001
sword~
a sword~
A sword lies here.~
~
weapon~
magic~
0 0 0 0
5 100 0
```

QuickMUD JSON:
```json
{
  "vnum": 1001,
  "keywords": "sword",
  "short_descr": "a sword",
  "long_descr": "A sword lies here.",
  "description": "",
  "item_type": "weapon",
  "extra_flags": ["magic"],
  "wear_flags": ["wield"],
  "value": [0, 2, 6, 0, 0],
  "weight": 5,
  "cost": 100,
  "level": 0
}
```

#### Step 5: Convert Resets

ROM C:
```
M 0 3001 2 3001
G 1 1001 0
```

QuickMUD JSON:
```json
{
  "command": "M",
  "arg1": 3001,
  "arg2": 2,
  "arg3": 3001,
  "comment": "Load mob 3001 (max 2) in room 3001"
},
{
  "command": "G",
  "arg1": 1001,
  "comment": "Give object 1001 to mob"
}
```

### Validation

After conversion, validate your JSON:

```bash
# Validate JSON syntax
python -m json.tool data/areas/myarea.json

# Load in QuickMUD
mud runserver
# Watch for errors during area load
```

---

## OLC Differences

### OLC Commands (Identical to ROM)

QuickMUD supports the same OLC commands as ROM:

```
redit           # Edit rooms
oedit           # Edit objects
medit           # Edit mobiles
aedit           # Edit areas
hedit           # Edit help files
```

### OLC Workflow

```
# Start editing
redit 10001             # Edit room 10001
redit create 10002      # Create new room

# Modify properties
name A Dark Cave
description You are in a dark cave.
sector inside
flags dark

# Add exits
north 10002
east 10003

# Save
done                    # Exit editor and save
asave changed           # Save all modified areas
```

### JSON-Specific Advantages

1. **Instant Validation** - Syntax errors caught immediately
2. **No Corruption** - JSON prevents malformed data
3. **Backup Friendly** - Each save creates valid JSON
4. **Git Integration** - Track changes with version control

---

## Python-Specific Features

### JSON Editing

You can edit areas directly in any text editor:

```bash
# Open in your favorite editor
vim data/areas/myarea.json
code data/areas/myarea.json
nano data/areas/myarea.json
```

**Tip**: Use an editor with JSON syntax highlighting and validation (VS Code, Sublime, etc.)

### Python Scripts

QuickMUD areas can be manipulated with Python scripts:

```python
import json

# Load area
with open('data/areas/myarea.json') as f:
    area = json.load(f)

# Modify all mob levels
for mob in area['mobiles']:
    mob['level'] += 5

# Save
with open('data/areas/myarea.json', 'w') as f:
    json.dump(area, f, indent=2)
```

### Batch Operations

```python
#!/usr/bin/env python3
"""Batch update all areas."""
import json
from pathlib import Path

for area_file in Path('data/areas').glob('*.json'):
    with open(area_file) as f:
        area = json.load(f)
    
    # Your modifications here
    area['area']['security'] = 5
    
    with open(area_file, 'w') as f:
        json.dump(area, f, indent=2)
```

---

## ROM API Compatibility

QuickMUD provides a ROM C-compatible API for scripts and external tools.

### Using ROM API

```python
from mud.rom_api import (
    board_lookup,
    recursive_clone,
    show_skill_cmds,
    do_imotd
)

# ROM C-style function names
board = board_lookup("general")
cloned_obj = recursive_clone(original)
skills = show_skill_cmds()
```

### Available ROM Functions

QuickMUD implements **27 ROM C-compatible wrapper functions**:

- **Board System** (9 functions): `board_lookup`, `do_nlist`, `do_nread`, etc.
- **OLC Helpers** (12 functions): `show_flag_cmds`, `wear_loc_lookup`, `set_obj_values`, etc.
- **Admin Utilities** (4 functions): `do_imotd`, `do_rules`, `do_story`, `get_max_train`
- **Misc Utilities** (3 functions): `check_blind`, `substitute_alias`, `mult_argument`

See [ROM_API_COMPLETION_REPORT.md](../ROM_API_COMPLETION_REPORT.md) for full documentation.

---

## Testing Your Areas

### Test Checklist

Before releasing converted areas:

1. **Load Test**
   ```
   mud runserver
   # Watch console for errors during area load
   ```

2. **Room Connectivity**
   ```
   goto 10001
   exits
   north
   # Test all exits
   ```

3. **Mob Testing**
   ```
   goto 10001
   mload 10001
   mstat guard
   # Verify stats, flags, behavior
   ```

4. **Object Testing**
   ```
   oload 10001
   ostat sword
   # Verify values, flags, weight
   ```

5. **Reset Testing**
   ```
   aresets
   # Verify resets load correctly
   
   # Force reset
   reset area
   # Check repopulation
   ```

6. **Shop Testing**
   ```
   goto <shop_room>
   list
   buy <item>
   sell <item>
   ```

### Debugging Tools

```bash
# Check area statistics
astat

# Validate resets
aresets

# Check vnum range
vnum mob 10000 10099
vnum obj 10000 10099
vnum room 10000 10099

# Find broken references
olccheck
```

---

## Best Practices

### Vnum Management

```json
{
  "area": {
    "vnums": [10000, 10099]
  }
}
```

**Best Practices:**
- Reserve 100-vnum blocks per area
- Document vnum assignments
- Coordinate with other builders
- Leave gaps for future expansion

### Area Organization

```
data/areas/
├── midgaard.json       # Starting area (3000-3099)
├── school.json         # Newbie school (3700-3799)
├── moria.json          # Level 10-20 (4000-4099)
└── olympus.json        # High-level (9000-9099)
```

### JSON Formatting

```bash
# Prettify JSON
python -m json.tool ugly.json > pretty.json

# Format with 2-space indent
jq . ugly.json > pretty.json
```

### Version Control

```bash
# Initialize git
git init
git add data/areas/*.json
git commit -m "Initial area commit"

# Track changes
git diff data/areas/myarea.json
git log data/areas/myarea.json

# Branching for experiments
git checkout -b experimental-dungeon
```

### Documentation

Add comments to JSON (non-standard, but helpful):

```json
{
  "_comment": "Midgaard - The central city",
  "area": {
    "name": "Midgaard"
  }
}
```

**Note**: Standard JSON doesn't support comments, but you can use `"_comment"` fields.

---

## Common Pitfalls

### 1. JSON Syntax Errors

**Problem**: Missing commas, quotes, brackets

```json
// WRONG
{
  "name": "test"
  "vnum": 1001
}

// RIGHT
{
  "name": "test",
  "vnum": 1001
}
```

**Solution**: Use JSON validator or linter

### 2. Incorrect Data Types

**Problem**: Strings where numbers expected

```json
// WRONG
{
  "vnum": "1001",
  "level": "10"
}

// RIGHT
{
  "vnum": 1001,
  "level": 10
}
```

### 3. Flag Names

**Problem**: ROM numeric flags vs QuickMUD string names

```json
// ROM C numeric flags (don't use)
{
  "act_flags": 512
}

// QuickMUD string names (use these)
{
  "act_flags": ["sentinel", "aggressive"]
}
```

### 4. Room Exits

**Problem**: Missing exit fields

```json
// WRONG
{
  "exits": [
    {"direction": "north"}
  ]
}

// RIGHT
{
  "exits": [
    {
      "direction": "north",
      "to_room": 3002,
      "keywords": "",
      "description": ""
    }
  ]
}
```

### 5. Reset Commands

**Problem**: Incorrect reset arguments

```json
// Check reset documentation
// M resets need: mob_vnum, limit, room_vnum
{
  "command": "M",
  "arg1": 3001,     // mob vnum
  "arg2": 2,        // max count
  "arg3": 3001      // room vnum
}
```

---

## Migration Checklist

### Pre-Migration

- [ ] Backup all ROM area files
- [ ] Document custom modifications
- [ ] List non-standard ROM features used
- [ ] Identify dependencies between areas
- [ ] Plan vnum ranges in QuickMUD

### Conversion

- [ ] Convert area metadata
- [ ] Convert all rooms
- [ ] Convert all mobiles
- [ ] Convert all objects
- [ ] Convert all resets
- [ ] Convert shops
- [ ] Validate JSON syntax
- [ ] Load in QuickMUD (check for errors)

### Testing

- [ ] Test room connectivity
- [ ] Test mob spawning
- [ ] Test object creation
- [ ] Test resets
- [ ] Test shops
- [ ] Test special features
- [ ] Playtest the area

### Post-Migration

- [ ] Update area documentation
- [ ] Create builder notes
- [ ] Set up version control
- [ ] Train other builders
- [ ] Establish backup routine

---

## Example Conversion

### ROM C Area

**area/testarea.are:**

```
#AREA
Test Area~
{1 10} Test Test Area~

#ROOMS
#10001
Test Room~
A simple test room.
~
0 0 1
D0
~
~
0 0 10002
S

#MOBILES
#10001
rat~
a rat~
A rat scurries around here.
~
A small brown rat.
~
rodent~
scavenger~
-1000 0 0
1 0 10
S

#OBJECTS
#10001
sword iron~
an iron sword~
An iron sword lies here.~
~
weapon~
take~
2 5 0 0
10 50 5
S

#RESETS
S
M 0 10001 5 10001
S

#SHOPS
0

#$
```

### QuickMUD JSON

**data/areas/testarea.json:**

```json
{
  "area": {
    "name": "Test Area",
    "credits": "Test Area",
    "level_range": [1, 10],
    "builders": ["Implementor"],
    "security": 5,
    "vnums": [10000, 10099]
  },
  "rooms": [
    {
      "vnum": 10001,
      "name": "Test Room",
      "description": "A simple test room.",
      "sector": "inside",
      "flags": [],
      "exits": [
        {
          "direction": "north",
          "to_room": 10002,
          "keywords": "",
          "description": "",
          "locks": 0,
          "key_vnum": 0
        }
      ]
    }
  ],
  "mobiles": [
    {
      "vnum": 10001,
      "keywords": "rat",
      "short_descr": "a rat",
      "long_descr": "A rat scurries around here.",
      "description": "A small brown rat.",
      "race": "rodent",
      "level": 1,
      "alignment": -1000,
      "hitroll": 0,
      "damroll": 0,
      "ac": [0, 0, 0, 0],
      "hit_dice": [0, 0, 10],
      "damage_dice": [0, 0, 0],
      "act_flags": ["scavenger"],
      "affected_by": [],
      "spec_fun": null
    }
  ],
  "objects": [
    {
      "vnum": 10001,
      "keywords": "sword iron",
      "short_descr": "an iron sword",
      "long_descr": "An iron sword lies here.",
      "description": "",
      "item_type": "weapon",
      "extra_flags": [],
      "wear_flags": ["take", "wield"],
      "value": [2, 2, 5, 0, 0],
      "weight": 10,
      "cost": 50,
      "level": 5,
      "condition": 100
    }
  ],
  "resets": [
    {
      "command": "M",
      "arg1": 10001,
      "arg2": 5,
      "arg3": 10001,
      "arg4": 0,
      "comment": "Load rat (max 5) in room 10001"
    }
  ],
  "shops": []
}
```

---

## Getting Help

### Resources

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Admin Guide**: [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
- **ROM API Docs**: [ROM_API_COMPLETION_REPORT.md](../ROM_API_COMPLETION_REPORT.md)
- **GitHub Issues**: Report problems or ask questions

### Community

- **GitHub Discussions**: Ask builder questions
- **Discord** (if available): Real-time help
- **ROM Documentation**: Original ROM docs in `doc/` directory

### Support Channels

For building help:
1. Check this guide first
2. Review example areas in `data/areas/`
3. Use `help <command>` in-game
4. Ask on GitHub Discussions
5. Submit bug reports via GitHub Issues

---

## Conclusion

QuickMUD provides a modern, maintainable platform for ROM building while maintaining **100% behavioral compatibility** with ROM 2.4b. The JSON format is easier to work with, version control, and validate than traditional ROM area files.

**Key Takeaways:**

✅ **Same ROM experience** - 100% parity  
✅ **Better format** - JSON is cleaner  
✅ **Same OLC** - Commands work identically  
✅ **Modern tools** - Python, git, editors  
✅ **ROM API** - C-compatible for scripts  

Welcome to QuickMUD building! 🐍✨

---

**Quick Start**: To begin building, see [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for OLC commands, or jump right in with:

```
redit create 10001
name My First Room
description Welcome to QuickMUD building!
done
asave changed
```

Happy building!
