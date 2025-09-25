from __future__ import annotations

from mud.agent.agent_protocol import AgentInterface
from mud.commands.communication import do_say
from mud.commands.inventory import do_drop, do_get
from mud.models.character import Character
from mud.world.movement import move_character


class CharacterAgentAdapter(AgentInterface):
    def __init__(self, character: Character):
        self.character = character

    def get_observation(self):
        room = self.character.room
        return {
            "name": self.character.name,
            "room": {
                "vnum": room.vnum if room else None,
                "name": getattr(room, "name", None),
                "description": getattr(room, "description", None),
                "npcs": [
                    getattr(npc, "name", None) for npc in getattr(room, "people", []) if npc is not self.character
                ],
                "players": [
                    p.name
                    for p in getattr(room, "people", [])
                    if getattr(p, "name", None) and hasattr(p, "messages") and p is not self.character
                ],
                "exits": [i for i, ex in enumerate(getattr(room, "exits", [])) if ex],
            }
            if room
            else None,
            "inventory": [obj.short_descr or obj.name for obj in self.character.inventory],
            "equipment": {slot: obj.short_descr or obj.name for slot, obj in self.character.equipment.items()},
            "hp": getattr(self.character, "hit", 0),
            "level": getattr(self.character, "level", 0),
        }

    def get_available_actions(self) -> list[str]:
        return ["move", "say", "pickup", "drop", "equip", "attack"]

    def perform_action(self, action: str, args: list[str]) -> str:
        try:
            if action == "move":
                direction = args[0]
                return move_character(self.character, direction)
            elif action == "say":
                return do_say(self.character, " ".join(args))
            elif action == "pickup":
                return do_get(self.character, args[0])
            elif action == "drop":
                return do_drop(self.character, args[0])
            elif action == "equip":
                item_name = args[0]
                slot = args[1] if len(args) > 1 else "wield"
                for obj in list(self.character.inventory):
                    obj_name = (obj.short_descr or obj.name or "").lower()
                    if item_name.lower() in obj_name:
                        self.character.equip_object(obj, slot)
                        return f"Equipped {obj_name} on {slot}"
                return "Item not found."
            elif action == "attack":
                return "Attack not implemented"
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"⚠️ Error: {str(e)}"
