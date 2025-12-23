"""
Misc info commands - motd, rules, story, socials, skills, spells, rent.

ROM Reference: src/act_info.c, src/skills.c, src/act_comm.c
"""
from __future__ import annotations

from mud.models.character import Character


def do_motd(char: Character, args: str) -> str:
    """
    Display the Message of the Day.
    
    ROM Reference: src/act_info.c do_motd (line 631)
    
    Just calls help motd.
    """
    from mud.commands.help import do_help
    return do_help(char, "motd")


def do_imotd(char: Character, args: str) -> str:
    """
    Display the Immortal Message of the Day.
    
    ROM Reference: src/act_info.c do_imotd (line 636)
    """
    from mud.commands.help import do_help
    return do_help(char, "imotd")


def do_rules(char: Character, args: str) -> str:
    """
    Display the game rules.
    
    ROM Reference: src/act_info.c do_rules (line 641)
    """
    from mud.commands.help import do_help
    return do_help(char, "rules")


def do_story(char: Character, args: str) -> str:
    """
    Display the game backstory.
    
    ROM Reference: src/act_info.c do_story (line 646)
    """
    from mud.commands.help import do_help
    return do_help(char, "story")


def do_socials(char: Character, args: str) -> str:
    """
    List all available social commands.
    
    ROM Reference: src/act_info.c do_socials (lines 606-625)
    """
    # Try to import socials from various locations
    socials = []
    
    try:
        from mud.data.social_data import SOCIALS
        socials = list(SOCIALS.keys())
    except ImportError:
        try:
            from mud import registry
            soc_table = getattr(registry, "social_table", {})
            socials = list(soc_table.keys())
        except (ImportError, AttributeError):
            pass
    
    if not socials:
        return "No socials found."
    
    socials = sorted(socials)
    
    # Format in 6 columns
    lines = []
    row = []
    for i, social in enumerate(socials):
        row.append(f"{social:<12}")
        if len(row) == 6:
            lines.append("".join(row))
            row = []
    
    if row:
        lines.append("".join(row))
    
    return "\n".join(lines)


def do_skills(char: Character, args: str) -> str:
    """
    List character's available skills.
    
    ROM Reference: src/skills.c do_skills (lines 381-480)
    
    Shows skills (non-spell abilities) the character knows or can learn.
    """
    if getattr(char, "is_npc", False):
        return ""
    
    try:
        from mud import registry
        skill_table = getattr(registry, "skill_table", {})
    except (ImportError, AttributeError):
        return "Skills not available."
    
    level = getattr(char, "level", 1)
    char_class = getattr(char, "char_class", None)
    class_idx = 0
    if char_class:
        class_idx = getattr(char_class, "index", 0)
    
    pcdata = getattr(char, "pcdata", None)
    learned = {}
    if pcdata:
        learned = getattr(pcdata, "learned", {})
    
    # Collect skills by level
    skill_by_level = {}
    
    for skill_name, skill_data in skill_table.items():
        # Skip spells (only show skills)
        if hasattr(skill_data, "spell_fun") and skill_data.spell_fun:
            continue
        
        # Get level requirement for this class
        skill_levels = getattr(skill_data, "skill_level", {})
        if isinstance(skill_levels, dict):
            skill_level = skill_levels.get(class_idx, 52)
        elif isinstance(skill_levels, (list, tuple)) and len(skill_levels) > class_idx:
            skill_level = skill_levels[class_idx]
        else:
            skill_level = 52
        
        if skill_level > 51:  # Not available to this class
            continue
        
        # Check if learned
        pct = learned.get(skill_name, 0)
        if pct <= 0 and skill_level > level:
            continue  # Not learned and not available yet
        
        if skill_level not in skill_by_level:
            skill_by_level[skill_level] = []
        
        if pct <= 0:
            skill_by_level[skill_level].append(f"{skill_name:<18} n/a")
        else:
            skill_by_level[skill_level].append(f"{skill_name:<18} {pct:3d}%")
    
    if not skill_by_level:
        return "No skills found."
    
    lines = []
    for lvl in sorted(skill_by_level.keys()):
        skills = skill_by_level[lvl]
        lines.append(f"\nLevel {lvl:2d}:")
        
        # Format in 2 columns
        row = []
        for skill in skills:
            row.append(skill)
            if len(row) == 2:
                lines.append("  " + "  ".join(row))
                row = []
        if row:
            lines.append("  " + "  ".join(row))
    
    return "\n".join(lines)


def do_spells(char: Character, args: str) -> str:
    """
    List character's available spells.
    
    ROM Reference: src/skills.c do_spells (lines 256-380)
    
    Shows spells the character knows or can learn, with mana costs.
    """
    if getattr(char, "is_npc", False):
        return ""
    
    try:
        from mud import registry
        skill_table = getattr(registry, "skill_table", {})
    except (ImportError, AttributeError):
        return "Spells not available."
    
    level = getattr(char, "level", 1)
    char_class = getattr(char, "char_class", None)
    class_idx = 0
    if char_class:
        class_idx = getattr(char_class, "index", 0)
    
    pcdata = getattr(char, "pcdata", None)
    learned = {}
    if pcdata:
        learned = getattr(pcdata, "learned", {})
    
    # Collect spells by level
    spell_by_level = {}
    
    for spell_name, spell_data in skill_table.items():
        # Only show spells (has spell_fun)
        if not hasattr(spell_data, "spell_fun") or not spell_data.spell_fun:
            continue
        
        # Get level requirement for this class
        spell_levels = getattr(spell_data, "skill_level", {})
        if isinstance(spell_levels, dict):
            spell_level = spell_levels.get(class_idx, 52)
        elif isinstance(spell_levels, (list, tuple)) and len(spell_levels) > class_idx:
            spell_level = spell_levels[class_idx]
        else:
            spell_level = 52
        
        if spell_level > 51:  # Not available to this class
            continue
        
        # Check if learned
        pct = learned.get(spell_name, 0)
        if pct <= 0 and spell_level > level:
            continue  # Not learned and not available yet
        
        if spell_level not in spell_by_level:
            spell_by_level[spell_level] = []
        
        # Calculate mana cost
        min_mana = getattr(spell_data, "min_mana", 20)
        if level < spell_level:
            mana_str = "n/a"
        else:
            mana = max(min_mana, 100 // (2 + level - spell_level))
            mana_str = f"{mana:3d} mana"
        
        spell_by_level[spell_level].append(f"{spell_name:<18} {mana_str}")
    
    if not spell_by_level:
        return "No spells found."
    
    lines = []
    for lvl in sorted(spell_by_level.keys()):
        spells = spell_by_level[lvl]
        lines.append(f"\nLevel {lvl:2d}:")
        
        # Format in 2 columns
        row = []
        for spell in spells:
            row.append(spell)
            if len(row) == 2:
                lines.append("  " + "  ".join(row))
                row = []
        if row:
            lines.append("  " + "  ".join(row))
    
    return "\n".join(lines)


def do_rent(char: Character, args: str) -> str:
    """
    Rent message - ROM has no rent system.
    
    ROM Reference: src/act_comm.c do_rent (line 1447)
    
    Just tells players there's no rent.
    """
    return "There is no rent here. Just save and quit."
