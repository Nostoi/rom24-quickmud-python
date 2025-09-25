from mud.agent.character_agent import CharacterAgentAdapter
from mud.registry import mob_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob


def run_agent_demo() -> None:
    room = room_registry.get(3001)
    proto_vnum = next(iter(mob_registry)) if mob_registry else None
    if proto_vnum is None or room is None:
        print("World not initialized or no mobs available")
        return
    mob = spawn_mob(proto_vnum)
    if not mob:
        print("Failed to spawn mob")
        return
    adapter = CharacterAgentAdapter(mob)
    room.add_mob(mob)
    print(adapter.get_observation())
    print(adapter.perform_action("say", ["I", "am", "alive!"]))
