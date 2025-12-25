# QuickMUD Administrator Guide

**Version**: 2.0.0  
**For**: Server Administrators and Immortals  
**Updated**: 2025-12-22

---

## Table of Contents

1. [Admin Overview](#admin-overview)
2. [Installation & Setup](#installation--setup)
3. [Immortal Levels](#immortal-levels)
4. [Admin Commands](#admin-commands)
5. [World Management](#world-management)
6. [Player Management](#player-management)
7. [Security & Access Control](#security--access-control)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Performance Tuning](#performance-tuning)
11. [Troubleshooting](#troubleshooting)

---

## Admin Overview

QuickMUD provides comprehensive administrative tools for managing your MUD server. This guide covers immortal commands, world building, player management, and server maintenance.

### Admin Roles

| Level | Role | Capabilities |
|-------|------|--------------|
| **60** | Implementor | Full server control, all commands |
| **59** | God | Area management, advanced building |
| **58** | Deity | World modification, player management |
| **57** | Angel | Player assistance, limited building |
| **56** | Demi | Helper immortal, basic commands |
| **52+** | Immortal | Visible as staff, basic immortal commands |
| **51** | Hero | Max mortal level |

---

## Installation & Setup

### Initial Server Setup

```bash
# Install QuickMUD
pip install quickmud

# Create server directory
mkdir my-mud-server
cd my-mud-server

# Initialize server (creates data directories)
mud init

# Start server
mud runserver
```

### Directory Structure

```
my-mud-server/
├── data/
│   ├── areas/          # World area files (JSON)
│   ├── players/        # Player save files
│   ├── help.json       # Help system data
│   ├── skills.json     # Skill definitions
│   ├── shops.json      # Shop configurations
│   └── socials.json    # Social commands
├── log/
│   └── server.log      # Server logs
├── .env                # Configuration
└── quickmud.db         # SQLite database
```

### Creating First Immortal

**Method 1: From Player Account**

```bash
# Connect as player, then from server console:
python -c "from mud.models.character import character_registry; \
           from mud.world.world_state import initialize_world; \
           initialize_world(); \
           char = character_registry.get('YourName'); \
           char.level = 60; \
           char.trust = 60; \
           print(f'{char.name} is now Implementor!')"
```

**Method 2: Database Direct Edit** (SQLite)

```bash
sqlite3 quickmud.db
UPDATE characters SET level = 60, trust = 60 WHERE name = 'YourName';
.quit
```

**Method 3: Player File Edit** (JSON)

```bash
# Edit data/players/YourName
{
  "name": "YourName",
  "level": 60,
  "trust": 60,
  ...
}
```

---

## Immortal Levels

### Level Hierarchy

QuickMUD uses ROM's traditional immortal level system:

```
Level 60 - Implementor    (Full control)
Level 59 - God            (World management)
Level 58 - Deity          (Player management)
Level 57 - Angel          (Helper immortal)
Level 56 - Demi           (Basic immortal)
Level 52-55 - Immortal    (Visible staff)
Level 51 - Hero           (Max mortal)
```

### Setting Trust Levels

Trust level determines what commands an immortal can use, even if their character level is lower:

```
# As Implementor (level 60)
advance <player> <level>      # Set character level
trust <player> <level>        # Set trust level (command access)

# Examples
advance Gandalf 57            # Make Gandalf level 57 (Angel)
trust Gandalf 58              # Give Gandalf Deity-level commands
```

### Immortal Visibility

```
# Toggle invisibility
invis                         # Toggle immortal invisibility
invis <level>                 # Invisible to mortals below level

# Wizilist
wizlist                       # Show all immortals
```

---

## Admin Commands

### Movement & Teleportation

```bash
# Teleportation
goto <location>               # Teleport to room/player
goto 3001                     # Teleport to room vnum 3001
goto gandalf                  # Teleport to player
transfer <player>             # Summon player to you
transfer all                  # Summon everyone
transfer all <location>       # Send everyone to location

# Special locations
goto limbo                    # Return to limbo (room 2)
goto temple                   # Go to temple (room 3001)
```

### Object & Mob Management

```bash
# Object commands
oload <vnum>                  # Load object by vnum
oload 1001                    # Load object #1001
ostat <object>                # Show object stats
oset <object> <field> <value> # Modify object

# Mob commands
mload <vnum>                  # Load mobile by vnum
mstat <mobile>                # Show mobile stats
mset <mobile> <field> <value> # Modify mobile

# Area commands
astat                         # Show current area stats
aresets                       # Show area resets
resets                        # Show room resets
```

### Player Management

```bash
# Character modification
advance <player> <level>      # Set player level
trust <player> <level>        # Set trust level
restore <player>              # Fully heal player
restore all                   # Heal everyone online

# Character inspection
pstat <player>                # Show player stats (detailed)
at <location> look            # Look at remote location
at <player> inventory         # See player's inventory

# Player control
freeze <player>               # Freeze player (cannot act)
thaw <player>                 # Unfreeze player
silence <player>              # Mute player
unsilence <player>            # Unmute player
```

### World Modification

```bash
# Room editing (OLC)
redit                         # Edit current room
redit <vnum>                  # Edit room by vnum
redit create <vnum>           # Create new room

# Object editing
oedit <vnum>                  # Edit object prototype
oedit create <vnum>           # Create new object

# Mobile editing
medit <vnum>                  # Edit mobile prototype
medit create <vnum>           # Create new mobile

# Area editing
aedit                         # Edit current area
aedit <area>                  # Edit specific area
aedit create <filename>       # Create new area

# Save changes
asave world                   # Save all areas
asave changed                 # Save modified areas only
asave list                    # List modified areas
```

### Server Management

```bash
# Server control
shutdown                      # Shut down server
shutdown now                  # Immediate shutdown
shutdown <ticks>              # Shutdown in X ticks
save                          # Save all online players

# Locks
wizlock                       # Lock server to immortals only
newlock                       # Prevent new character creation

# Banning
ban <site>                    # Ban site pattern
ban list                      # List banned sites
permban <site>                # Permanent ban
allow <site>                  # Remove ban

# Logging
log all                       # Log all commands
log <player>                  # Log specific player
```

### Communication

```bash
# Immortal channels
immtalk <message>             # Immortal-only chat
imm <message>                 # Shortcut for immtalk
wiznet <message>              # Wiznet channel

# Announcements
echo <message>                # Echo to all players
recho <message>               # Echo to current room
zecho <area> <message>        # Echo to entire area

# Forced actions
force <player> <command>      # Force player to execute command
force all save                # Force all to save
```

---

## World Management

### OLC (Online Creation)

QuickMUD includes a full OLC (Online Creation) system for building worlds without restarting the server.

#### Creating a New Area

```
aedit create myarea.json

# Set area properties
name The Mystical Forest
builders YourName
vnums 10000 10099
security 5

# Save
done
```

#### Creating Rooms

```
redit create 10001

# Basic properties
name A Dark Cave
description You are standing in a dark, damp cave.
sector inside

# Add exits
north 10002
east 10003

# Room flags
flags dark indoors

# Save
done
```

#### Creating Objects

```
oedit create 10001

# Basic properties
name a rusty sword
short a rusty sword
long A rusty sword lies here.

# Object type
type weapon

# Values (weapon-specific)
value0 0       # Weapon class (0 = exotic)
value1 2       # Number of dice
value2 6       # Dice sides (2d6 damage)
value3 0       # Damage type (0 = none)

# Weight and cost
weight 5
cost 100
level 1

# Save
done
```

#### Creating Mobiles

```
medit create 10001

# Basic properties
name a goblin warrior
short a goblin warrior
long A goblin warrior stands here, looking hostile.
description A small, green-skinned goblin wearing crude armor.

# Stats
level 5
alignment -500
hitroll 2
damroll 1

# Actions/Affects
act aggressive scavenger

# Save
done
```

### Area Resets

Resets control how areas repopulate with mobs and objects.

```
# View resets
aresets

# Add mob reset
reset mob <vnum> <max_count> <room>
reset mob 10001 3 10005       # Max 3 goblins in room 10005

# Add object reset
reset obj <vnum> <location>
reset obj 10001 room          # Object in room
reset obj 10002 mob           # Object on mob
reset obj 10003 container     # Object in container

# Add door reset
reset door <direction> <state>
reset door north closed       # North exit closed
reset door south locked       # South exit locked

# Save resets
asave changed
```

### Area Validation

```
# Check area integrity
astat                         # Show area statistics
olccheck                      # Validate OLC syntax
vnum <type> <start> <end>     # List vnums in range
```

---

## Player Management

### Character Administration

```bash
# View player info
who                           # List online players
users                         # Show connection info
pstat <player>                # Detailed character stats

# Modify players
set <player> <field> <value>  # Set character field
set gandalf str 25            # Set strength to 25
set gandalf hit 500           # Set current HP to 500
set gandalf exp 100000        # Set experience

# Experience & Level
advance <player> <level>      # Change level
reclass <player> <class>      # Change class
```

### Punishment Commands

```bash
# Temporary punishment
freeze <player>               # Cannot move or act
silence <player>              # Cannot communicate
lag <player> <seconds>        # Add input lag
slow <player>                 # Slow movement

# Removal
thaw <player>                 # Remove freeze
unsilence <player>            # Remove silence

# Permanent punishment
slay <player>                 # Kill player instantly
purge <player>                # Delete character (DANGEROUS!)
deny <player>                 # Ban from server
```

### Player Assistance

```bash
# Restoration
restore <player>              # Fully heal player
restore all                   # Heal all online

# Assistance
transfer <player>             # Bring player to you
goto <player>                 # Go to player
at <player> <command>         # Execute command at player
peace                         # Stop all fighting in room

# Investigation
inventory <player>            # View inventory (use pstat)
holylight                     # See invisible players/objects
```

---

## Security & Access Control

### Trust System

Trust levels control command access independently of character level:

```bash
# Check trust
pstat <player>                # Shows trust level

# Set trust
trust <player> <level>        # Grant command access
trust gandalf 57              # Angel-level commands

# Trust recommendations
# Level 60 - Only head admin
# Level 59 - Senior builders
# Level 58 - Player moderators
# Level 57 - Helper immortals
# Level 56 - Trial immortals
```

### Access Control

```bash
# Wizlock (immortals only)
wizlock                       # Toggle wizlock
wizlock on                    # Lock to immortals
wizlock off                   # Open to all

# Newlock (no new characters)
newlock                       # Toggle newlock
newlock on                    # Prevent new chars
newlock off                   # Allow new chars

# Site banning
ban <pattern>                 # Ban IP/hostname
ban 192.168.1.*               # Ban subnet
ban *.badsite.com             # Ban domain
ban list                      # Show bans
allow <site>                  # Remove ban
```

### Audit Logging

```bash
# Command logging
log all                       # Log all commands
log <player>                  # Log specific player
log stop                      # Stop logging

# Log files
tail -f log/server.log        # Monitor server log
grep "ADMIN" log/server.log   # Search admin actions
```

---

## Monitoring & Logging

### Server Monitoring

```bash
# Status commands
users                         # Connection info
lag                           # Server lag check
memory                        # Memory usage (if available)

# Performance
dump                          # List all objects
list                          # List areas
wizlist                       # List immortals
```

### Log Files

**log/server.log** - Main server log

```bash
# Monitor live
tail -f log/server.log

# Search logs
grep ERROR log/server.log
grep "player login" log/server.log
grep ADMIN log/server.log
```

**Log Levels** (configured in .env):

```bash
LOG_LEVEL=DEBUG    # Verbose (development)
LOG_LEVEL=INFO     # Normal (default)
LOG_LEVEL=WARNING  # Warnings only
LOG_LEVEL=ERROR    # Errors only
```

### Admin Logging

All immortal commands are logged with:
- **Timestamp**
- **Immortal name**
- **Command executed**
- **Target (if applicable)**

Example log entry:
```
2025-12-22 15:30:45 [ADMIN] Gandalf (60) used: goto midgaard
2025-12-22 15:31:12 [ADMIN] Gandalf (60) used: advance Frodo 10
```

---

## Backup & Recovery

### Automatic Backups

QuickMUD saves player data automatically:
- **On quit** - Player saves when logging out
- **Every 30 minutes** - Auto-save for all online players
- **On shutdown** - All players saved before shutdown

### Manual Backups

```bash
# Force save all players
save

# Backup script (Linux/Mac)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf backups/mud_backup_$DATE.tar.gz data/ quickmud.db
find backups/ -mtime +30 -delete  # Remove backups older than 30 days
```

### Restore from Backup

```bash
# Stop server first!
tar -xzf backups/mud_backup_20251222_153000.tar.gz

# Restart server
mud runserver
```

### Player File Recovery

Player files are in `data/players/<name>` (JSON format):

```bash
# View player file
cat data/players/Gandalf

# Restore corrupt player
cp backups/players/Gandalf data/players/Gandalf

# Delete broken character (last resort)
rm data/players/BrokenChar
```

---

## Performance Tuning

### Server Configuration

**.env file:**

```bash
# Connection limits
MAX_PLAYERS=100                # Max concurrent players
CONNECTION_TIMEOUT=300         # Idle timeout (seconds)

# Performance
TICK_RATE=60                   # Game ticks per minute
SAVE_INTERVAL=1800             # Auto-save interval (seconds)

# Database
DATABASE_URL=sqlite:///quickmud.db
DATABASE_POOL_SIZE=10

# Logging
LOG_LEVEL=INFO                 # INFO, WARNING, ERROR, DEBUG
LOG_FILE=log/server.log
```

### Resource Limits

```bash
# Monitor memory
top                            # Watch memory usage
ps aux | grep mud              # Find MUD process

# Limit resources (systemd)
MemoryLimit=512M
CPUQuota=50%
```

### Optimization Tips

1. **Reduce log verbosity** in production
2. **Clean old player files** (inactive > 1 year)
3. **Optimize area resets** (don't over-populate)
4. **Use connection limits** to prevent overload
5. **Monitor disk space** for databases

---

## Troubleshooting

### Common Issues

#### Server Won't Start

```bash
# Check for port conflicts
netstat -an | grep 4000
lsof -i :4000

# Check permissions
ls -la data/
chmod 755 data/

# Check Python version
python --version  # Must be 3.10+
```

#### Player Can't Log In

```bash
# Check player file
cat data/players/PlayerName

# Check logs
grep "PlayerName" log/server.log

# Restore from backup if corrupt
cp backups/players/PlayerName data/players/
```

#### OLC Changes Not Saving

```bash
# Explicit save
asave changed

# Check file permissions
ls -la data/areas/
chmod 644 data/areas/*.json

# Check disk space
df -h
```

#### Performance Degradation

```bash
# Check online players
who

# Check object/mob count
dump | wc -l

# Purge unused objects
purge

# Restart server (saves everyone first)
shutdown 5
```

### Emergency Procedures

#### Server Crash Recovery

```bash
# 1. Check for core dump
ls -la core*

# 2. Review logs
tail -100 log/server.log

# 3. Restore from backup if needed
tar -xzf backups/latest.tar.gz

# 4. Restart server
mud runserver
```

#### Database Corruption

```bash
# SQLite recovery
sqlite3 quickmud.db
.integrity_check
.quit

# If corrupt, restore from backup
cp backups/quickmud.db quickmud.db
```

---

## Systemd Service

For production deployment, use systemd:

**/etc/systemd/system/quickmud.service:**

```ini
[Unit]
Description=QuickMUD Server
After=network.target

[Service]
Type=simple
User=mudadmin
WorkingDirectory=/home/mudadmin/quickmud
Environment="PATH=/home/mudadmin/quickmud/venv/bin"
ExecStart=/home/mudadmin/quickmud/venv/bin/mud runserver
Restart=always
RestartSec=10

# Resource limits
MemoryLimit=512M
CPUQuota=50%

# Logging
StandardOutput=append:/var/log/quickmud/server.log
StandardError=append:/var/log/quickmud/error.log

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable quickmud
sudo systemctl start quickmud
sudo systemctl status quickmud

# View logs
sudo journalctl -u quickmud -f
```

---

## Best Practices

### Security

1. **Never share Implementor access** - Only 1-2 trusted admins
2. **Use trust levels appropriately** - Don't over-promote
3. **Monitor admin logs regularly** - Check for abuse
4. **Backup frequently** - Daily automated backups minimum
5. **Keep server updated** - `pip install --upgrade quickmud`

### World Building

1. **Plan vnums** - Reserve ranges (10000-19999 = Area1, etc.)
2. **Test thoroughly** - Use test characters before release
3. **Document changes** - Comment in area files
4. **Version control** - Use git for area files
5. **Coordinate builders** - Assign vnum ranges to prevent conflicts

### Player Management

1. **Be fair and consistent** - Apply rules equally
2. **Warn before punishment** - Give players chances
3. **Document incidents** - Keep notes on problem players
4. **Respond to reports** - Address player concerns quickly
5. **Foster community** - Encourage positive gameplay

---

## Quick Reference

### Essential Admin Commands

```
goto <loc>            Transfer <player>         Force <player> <cmd>
Restore <player>      Advance <player> <lvl>    Trust <player> <lvl>
mload/oload <vnum>    Redit/Oedit/Medit         Asave changed
Freeze/Thaw           Wizlock/Newlock           Ban <site>
immtalk <msg>         Echo <msg>                Shutdown
```

### Emergency Commands

```
peace                 Stop all fighting
restore all           Heal everyone
purge                 Remove all objects in room
shutdown now          Immediate shutdown
wizlock on            Lock server to immortals
```

---

## Additional Resources

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Builder Guide**: [BUILDER_MIGRATION_GUIDE.md](BUILDER_MIGRATION_GUIDE.md)
- **ROM API**: [ROM_API_COMPLETION_REPORT.md](../ROM_API_COMPLETION_REPORT.md)
- **GitHub Issues**: Report bugs and request features

---

**Remember**: With great power comes great responsibility. Use admin commands wisely! 🐍✨
