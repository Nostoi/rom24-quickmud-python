from __future__ import annotations

from mud.registry import mob_registry
from .base_loader import BaseTokenizer


def load_specials(tokenizer: BaseTokenizer, area) -> None:
    """Load #SPECIALS section and attach spec_fun names to MobIndex.

    Format (doc/area.txt § #SPECIALS):
      #SPECIALS
      { M <mob-vnum> <spec-fun> <comment-to-eol> }
      S
    """
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        s = line.strip()
        if not s:
            continue
        if s == 'S':
            break
        if not s or s.startswith('*'):
            continue
        if s[0] in '{':
            # Lines may be grouped in braces; consume but ignore braces
            s = s.lstrip('{').rstrip('}')
            s = s.strip()
            if not s:
                continue
        if s.startswith('M '):
            parts = s.split()
            # parts: ['M', '<vnum>', '<spec>'] + optional comments
            if len(parts) >= 3:
                try:
                    vnum = int(parts[1])
                except ValueError:
                    continue
                spec_name = parts[2]
                proto = mob_registry.get(vnum)
                if proto is not None:
                    proto.spec_fun = spec_name
    # No return value needed; registry updated in place


def apply_specials_from_json(entries: list[dict]) -> None:
    """Attach spec_fun names from a JSON "specials" list to mob prototypes.

    Each entry must be a dict with keys: {"mob_vnum": int, "spec": str}.
    Unknown vnums are ignored (matching ROM's tolerant loaders).
    """
    for entry in entries or []:
        try:
            vnum = int(entry.get("mob_vnum"))
        except Exception:
            continue
        spec = entry.get("spec")
        if not spec:
            continue
        proto = mob_registry.get(vnum)
        if proto is not None:
            proto.spec_fun = str(spec)
