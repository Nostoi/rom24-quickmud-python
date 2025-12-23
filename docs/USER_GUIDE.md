# QuickMUD User Guide

**Version**: 2.0.0  
**For**: Players and Server Operators  
**Updated**: 2025-12-22

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installing QuickMUD](#installing-quickmud)
3. [Running a Server](#running-a-server)
4. [Connecting as a Player](#connecting-as-a-player)
5. [Character Creation](#character-creation)
6. [Basic Commands](#basic-commands)
7. [Combat System](#combat-system)
8. [Skills and Spells](#skills-and-spells)
9. [Social Features](#social-features)
10. [Server Configuration](#server-configuration)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

QuickMUD is a modern Python implementation of ROM 2.4b6, one of the most popular MUD engines ever created. This guide will help you install, run, and play QuickMUD.

### What is a MUD?

A **Multi-User Dungeon (MUD)** is a text-based multiplayer online role-playing game. Players explore a virtual world by reading descriptions and typing commands like:

```
> look
You are standing in the Temple of Midgaard.
A large fountain is here, with water bubbling up from it.
Exits: north south east west

> north
You walk north.
The Main Street of Midgaard
You are standing on the main street of Midgaard.
Exits: north south
```

### Why QuickMUD?

- ✅ **100% ROM 2.4b Behavioral Parity** - Authentic ROM experience
- ✅ **Modern Python** - Easy to install and extend
- ✅ **Active Development** - Regular updates and bug fixes
- ✅ **Cross-Platform** - Runs on Windows, Mac, Linux
- ✅ **JSON World Data** - Easy-to-edit area files

---

## Installing QuickMUD

### For Players (Quick Install)

If you just want to connect to an existing QuickMUD server, you don't need to install anything! Use any telnet client:

**Windows:**
```cmd
telnet mud.example.com 4000
```

**Mac/Linux:**
```bash
telnet mud.example.com 4000
```

**Modern Alternatives:**
- [MUSHclient](http://www.mushclient.com/) (Windows)
- [TinTin++](https://tintin.mudhalla.net/) (Cross-platform)
- [Mudlet](https://www.mudlet.org/) (Cross-platform, graphical)

### For Server Operators

#### Requirements

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Internet connection** (for initial installation)

#### Quick Install

```bash
# Install from PyPI
pip install quickmud

# Verify installation
mud --version
```

#### From Source (Developers)

```bash
# Clone the repository
git clone https://github.com/Nostoi/rom24-quickmud-python.git
cd rom24-quickmud-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Run tests to verify
pytest
```

---

## Running a Server

### Basic Server Start

```bash
# Start server on default port (4000)
mud runserver

# Start on custom port
mud runserver --port 5000

# Start with specific host
mud runserver --host 0.0.0.0 --port 4000
```

### Server Output

When started successfully, you'll see:

```
✅ Loaded 134 skills from data/skills.json
✅ Loaded 62 shops from data/shops.json
✅ Loaded 89 areas with 3421 rooms
🌐 Server listening on 0.0.0.0:4000
Ready for players!
```

### Server Management

**Graceful Shutdown:**
```bash
# Press Ctrl+C in the server terminal
^C
Server shutting down gracefully...
Saving all players...
✅ Shutdown complete
```

**Background Execution:**
```bash
# Using nohup (Linux/Mac)
nohup mud runserver > server.log 2>&1 &

# Using screen
screen -S mudserver
mud runserver
# Press Ctrl+A then D to detach

# Using systemd (see Admin Guide for service file)
sudo systemctl start quickmud
```

---

## Connecting as a Player

### First Connection

1. **Open telnet client**
2. **Connect to server** (e.g., `telnet localhost 4000`)
3. **You'll see the login screen:**

```
              ____        _      __    __  __  _   _ ____  
             / __ \      (_)    |  \  /  ||  \/  || | | |  \ 
            | |  | |_   _ _  ___| |\\/| || .  . || | | | |  \
            | |  | | | | | |/ __| |  | || |\/| || | | | |  /
            | |__| | |_| | | |__| |  | || |  | || |_| | |_/
             \___\_\\__,_|_|\\___|_|  |_||_|  |_| \___/|____/
                                                              
                    ROM 2.4b - QuickMUD Python Port
                         100% Behavioral Parity
                              
By what name do you wish to be known? 
```

4. **Choose your path:**
   - **New player:** Type a name (e.g., `Gandalf`)
   - **Returning player:** Type your existing character name

### Creating a New Character

```
By what name do you wish to be known? Gandalf
Did I get that right, Gandalf (Y/N)? y

New character. Creating...

Choose your race:
  [Human] Balanced stats, versatile
  [Elf]   High intelligence and dexterity
  [Dwarf] High constitution, tough
  [Giant] High strength, powerful
  ... (and more)

Race: human

Choose your class:
  [Warrior]     Master of weapons and armor
  [Thief]       Skilled in stealth and backstab
  [Cleric]      Divine magic and healing
  [Mage]        Arcane magic and spells
  ... (and more)

Class: warrior

Choose your alignment:
  [Good]    Protector of the innocent
  [Neutral] Balanced between good and evil
  [Evil]    Power at any cost

Alignment: good

Your stats:
  STR: 18  INT: 13  WIS: 13  DEX: 13  CON: 17

Confirm character creation? (Y/N) y

Welcome to QuickMUD!
```

### Logging In (Returning Players)

```
By what name do you wish to be known? Gandalf
Password: ********

Welcome back, Gandalf!

Last login: Thu Dec 22 15:30:00 2025
You have 2 new notes.

The Temple of Midgaard
You are standing in the Temple of Midgaard...
>
```

---

## Basic Commands

### Movement

```bash
# Cardinal directions
north, n           # Move north
south, s           # Move south
east, e            # Move east
west, w            # Move west
up, u              # Move up
down, d            # Move down

# Navigation
look               # Look at current room
look <object>      # Examine something
exits              # Show available exits
where              # Show area map
```

### Communication

```bash
# Channels
say <message>      # Say something in current room
tell <player> <msg> # Private message to player
gossip <message>   # Game-wide chat channel
shout <message>    # Shout across the area
gtell <message>    # Group chat

# Socials
smile              # Smile at everyone
smile <player>     # Smile at specific player
wave               # Wave
bow                # Bow respectfully
# ... 100+ social commands available
```

### Information

```bash
# Character info
score              # Character stats and status
inventory, i       # Show inventory
equipment, eq      # Show worn equipment
affects            # Active spells/affects
who                # List online players

# World info
time               # Game time
weather            # Current weather
help <topic>       # Get help on any topic
```

### Items

```bash
# Getting items
get <item>         # Pick up item
get all            # Pick up everything
get all.coin       # Pick up all coins

# Using items
wear <item>        # Wear/wield equipment
remove <item>      # Remove equipment
eat <item>         # Eat food
drink <container>  # Drink from container
quaff <potion>     # Drink a potion
recite <scroll>    # Read a scroll

# Managing items
drop <item>        # Drop item
give <item> <player> # Give item to player
put <item> <container> # Put item in container
```

### Combat

```bash
# Entering combat
kill <target>      # Attack a target
murder <target>    # Attack a player (PvP)

# During combat
flee               # Attempt to flee
rescue <player>    # Save ally from attacker

# Combat skills (varies by class)
bash               # Warrior: bash opponent
backstab           # Thief: surprise attack
cast 'magic missile' # Mage: cast spell
```

---

## Combat System

QuickMUD uses the classic ROM combat system with 100% behavioral parity to the original.

### How Combat Works

1. **Initiate combat** with `kill <target>`
2. **Automatic rounds** - attacks happen automatically each round
3. **Use skills** - type skill names during combat
4. **Monitor HP** - watch your health
5. **Flee if needed** - use `flee` to escape

### Combat Example

```
> kill orc
You attack an orc!

You hit an orc. (12 damage)
An orc misses you.

You massacre an orc! (24 damage)
An orc hits you. (8 damage)

> bash
You slam into an orc with your shield!
An orc falls to the ground, stunned!

You DEMOLISH an orc! (31 damage)
An orc is DEAD!!
You receive 150 experience points.

The corpse of an orc contains:
  some gold coins
  a rusty sword
```

### Death and Resurrection

If you die:

1. **You lose experience** (10% of current level)
2. **Corpse created** with your equipment
3. **Sent to recall** (Temple of Midgaard)
4. **Can recover corpse** by returning to death location

### PvP (Player vs Player)

- Use `murder <player>` instead of `kill`
- Only works in designated PvP areas
- Subject to server rules and penalties

---

## Skills and Spells

### Learning Skills

```
> practice
You have 5 practice sessions.

Skills you can practice:
  sword         : 75%  (novice)
  bash          : 60%  (apprentice)
  dodge         : 40%  (unskilled)
  parry         : 55%  (beginner)

> practice sword
You practice sword.
Your sword skill improves to 80%!
```

### Using Skills

```bash
# Passive skills (automatic)
dodge              # Automatically avoid attacks
parry              # Automatically deflect attacks

# Active skills (manual)
bash               # Stun opponent
disarm             # Remove opponent's weapon
rescue <player>    # Save ally
berserk            # Rage mode (more damage, less defense)
```

### Casting Spells

```bash
# Check mana
score              # Shows current mana

# Cast spell
cast 'magic missile' orc
cast 'cure light' self
cast 'armor' gandalf
cast 'fireball'    # Area effect

# Spell list
practice           # Shows castable spells
help spells        # Spell documentation
```

### Spell Components

Some spells require components:

- **Portal/Nexus** requires warp-stone (consumed on cast)
- Most other spells only require mana

---

## Social Features

### Communication Channels

| Channel | Syntax | Visibility |
|---------|--------|------------|
| **Say** | `say <message>` | Current room only |
| **Tell** | `tell <player> <msg>` | Private, one player |
| **Gossip** | `gossip <message>` | Everyone online |
| **Shout** | `shout <message>` | Current area |
| **Group** | `gtell <message>` | Group members only |
| **Immtalk** | `immtalk <msg>` | Immortals only |

### Channel Control

```bash
# Toggle channels on/off
channels           # Show current channel settings
deaf gossip        # Turn off gossip
deaf all           # Mute all channels

# Quiet mode
quiet              # Ignore all communication
```

### Groups

```bash
# Create/join group
follow <leader>    # Follow a player
group <player>     # Invite to group
ungroup <player>   # Remove from group

# Group commands
gtell <message>    # Group chat
split              # Split gold with group

# Group benefits
- Shared experience
- Group healing spells
- Follow leader automatically
```

### Social Commands

Over 100 social emotes available:

```
smile, wave, bow, nod, shake, laugh, cry, giggle,
hug, kiss, slap, poke, tackle, comfort, cuddle...

# Usage
smile              # Smile at room
smile gandalf      # Smile at Gandalf
```

---

## Server Configuration

### Environment Variables

Create a `.env` file in the server directory:

```bash
# Server settings
MUD_HOST=0.0.0.0
MUD_PORT=4000

# Database
DATABASE_URL=sqlite:///quickmud.db

# Game settings
MAX_PLAYERS=100
WIZLOCK=false
NEWLOCK=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=server.log
```

### Configuration Files

**data/skills.json** - Skill definitions  
**data/shops.json** - Shop configurations  
**data/areas/** - World area files

### Server Modes

```bash
# Normal mode (default)
mud runserver

# Wizlock mode (immortals only)
# Set WIZLOCK=true in .env

# Newlock mode (no new characters)
# Set NEWLOCK=true in .env

# Debug mode
LOG_LEVEL=DEBUG mud runserver
```

---

## Troubleshooting

### Cannot Connect to Server

**Problem**: "Connection refused" or timeout

**Solutions**:
1. Verify server is running (`ps aux | grep mud`)
2. Check firewall settings (allow port 4000)
3. Verify host/port configuration
4. Try localhost: `telnet localhost 4000`

### Character Won't Load

**Problem**: "Character not found" or load fails

**Solutions**:
1. Check case-sensitivity of name
2. Verify `data/players/` directory exists
3. Check file permissions
4. Look for error messages in server log

### Commands Not Working

**Problem**: "Huh?" or command not recognized

**Solutions**:
1. Check for typos
2. Use `help commands` for command list
3. Ensure sufficient level for command
4. Check if in correct mode (combat/peaceful)

### Server Crashes

**Problem**: Server exits unexpectedly

**Solutions**:
1. Check `server.log` for error messages
2. Verify Python version (3.10+ required)
3. Update to latest version: `pip install --upgrade quickmud`
4. Report bug with error log to GitHub issues

### Performance Issues

**Problem**: Lag or slow responses

**Solutions**:
1. Check server resources (CPU/RAM)
2. Reduce MAX_PLAYERS if needed
3. Optimize area resets
4. Enable logging only for errors: `LOG_LEVEL=ERROR`

### Data Corruption

**Problem**: Corrupted player files or areas

**Solutions**:
1. Restore from backup
2. Delete corrupt file (will lose that character)
3. Validate JSON files: `python -m json.tool data/areas/midgaard.json`
4. Report issue to GitHub

---

## Getting Help

### In-Game Help

```bash
help              # General help index
help commands     # List all commands
help <topic>      # Specific help topic
help skills       # Skill documentation
help spells       # Spell documentation
```

### External Resources

- **GitHub**: https://github.com/Nostoi/rom24-quickmud-python
- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See `docs/` directory
- **ROM 2.4 Docs**: Original documentation in `doc/` directory

### Admin Support

For server administrators:
- See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for advanced configuration
- See [BUILDER_MIGRATION_GUIDE.md](BUILDER_MIGRATION_GUIDE.md) for world building

---

## Quick Reference Card

### Essential Commands

```
Movement:  n, s, e, w, u, d
Look:      look, examine <object>
Items:     get <item>, drop <item>, wear <item>
Combat:    kill <target>, flee
Magic:     cast '<spell>' <target>
Chat:      say, tell, gossip
Info:      score, inventory, equipment, who
Help:      help <topic>
Quit:      quit, save
```

### Function Keys (if supported by client)

Most MUD clients allow macros:

- **F1** = look
- **F2** = inventory
- **F3** = score
- **F4** = exits
- **F5-F8** = Custom spells/skills

---

## Welcome to QuickMUD!

You're now ready to explore the world of QuickMUD. Remember:

- **Be respectful** to other players
- **Read help files** when stuck
- **Ask questions** - the community is helpful
- **Have fun** - it's a game!

For builders and administrators, see the advanced guides:
- [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
- [BUILDER_MIGRATION_GUIDE.md](BUILDER_MIGRATION_GUIDE.md)

Happy adventuring! 🐍✨
