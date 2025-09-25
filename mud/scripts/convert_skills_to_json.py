#!/usr/bin/env python3
"""
Convert ROM 2.4 skill_table from const.c to JSON format.
"""

import json
import re
from pathlib import Path
from typing import Any


def parse_skill_table(const_c_path: Path) -> list[dict[str, Any]]:
    """Parse the skill_table from src/const.c and convert to JSON format."""

    content = const_c_path.read_text(encoding="latin-1")

    # Find the skill_table definition
    start_match = re.search(r"const struct skill_type skill_table\[MAX_SKILL\] = \{", content)
    if not start_match:
        raise ValueError("Could not find skill_table definition")

    # Extract the skill table content
    start_pos = start_match.end()
    brace_count = 1
    pos = start_pos

    while pos < len(content) and brace_count > 0:
        if content[pos] == "{":
            brace_count += 1
        elif content[pos] == "}":
            brace_count -= 1
        pos += 1

    if brace_count != 0:
        raise ValueError("Could not find end of skill_table")

    table_content = content[start_pos : pos - 1]

    # Parse individual skill entries
    skills = []

    # Split by skill entries (each starts with {)
    skill_pattern = r'\{\s*"([^"]+)",\s*\{([^}]+)\},\s*\{([^}]+)\},\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+),\s*([^,\n]+),\s*"([^"]*)",\s*"([^"]*)"(?:,\s*"([^"]*)")?\s*\}'

    for match in re.finditer(skill_pattern, table_content, re.MULTILINE | re.DOTALL):
        name = match.group(1)
        skill_levels = match.group(2).strip()
        ratings = match.group(3).strip()
        spell_fun = match.group(4).strip()
        target = match.group(5).strip()
        position = match.group(6).strip()
        gsn = match.group(7).strip()
        slot = match.group(8).strip()
        min_mana = match.group(9).strip()
        beats = match.group(10).strip()
        noun_damage = match.group(11).strip()
        msg_off = match.group(12).strip()
        msg_obj = match.group(13).strip() if match.group(13) else ""

        # Skip reserved entry
        if name == "reserved":
            continue

        # Determine if this is a spell or skill
        is_spell = "spell_" in spell_fun and spell_fun != "spell_null"
        skill_type = "spell" if is_spell else "skill"

        # Extract function name
        function_name = name.replace(" ", "_")
        if is_spell:
            function_name = spell_fun.replace("spell_", "") if spell_fun.startswith("spell_") else function_name

        # Parse mana cost
        try:
            mana_cost = int(min_mana) if min_mana.isdigit() else 0
        except ValueError:
            mana_cost = 0

        # Parse lag (beats)
        try:
            lag = int(beats) if beats.isdigit() else 0
        except ValueError:
            lag = 0

        # Determine target type
        target_mapping = {
            "TAR_IGNORE": "ignore",
            "TAR_CHAR_OFFENSIVE": "victim",
            "TAR_CHAR_DEFENSIVE": "friendly",
            "TAR_CHAR_SELF": "self",
            "TAR_OBJ_INV": "object",
            "TAR_OBJ_CHAR_DEF": "character_or_object",
            "TAR_OBJ_CHAR_OFF": "character_or_object",
        }
        target_type = target_mapping.get(target, "victim")

        skill_entry = {
            "name": name,
            "type": skill_type,
            "function": function_name,
            "target": target_type,
            "mana_cost": mana_cost,
            "lag": lag,
            "cooldown": 0,  # Default cooldown
            "failure_rate": 0.0,  # Default failure rate
            "messages": {"damage": noun_damage, "wear_off": msg_off},
        }

        # Add object message if present
        if msg_obj:
            skill_entry["messages"]["object"] = msg_obj

        skills.append(skill_entry)

    return skills


def main():
    """Convert ROM 2.4 skills to JSON."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert ROM 2.4 skill_table to JSON")
    parser.add_argument(
        "--const-c", type=Path, default=Path("src/const.c"), help="Path to const.c file (default: src/const.c)"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/skills.json"), help="Output JSON file (default: data/skills.json)"
    )

    args = parser.parse_args()

    if not args.const_c.exists():
        print(f"Error: {args.const_c} not found")
        return 1

    try:
        skills = parse_skill_table(args.const_c)

        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with nice formatting
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(skills, f, indent=2, ensure_ascii=False)

        print(f"✅ Converted {len(skills)} skills to {args.output}")
        print(f"Sample skills: {[s['name'] for s in skills[:5]]}")

        return 0

    except Exception as e:
        print(f"Error converting skills: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
