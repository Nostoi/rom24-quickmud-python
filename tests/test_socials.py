from mud.models.character import Character
from mud.models.constants import Sex
from mud.models.room import Room
from mud.commands.dispatcher import process_command
from mud.loaders.social_loader import load_socials


def setup_room():
    room = Room(vnum=1)
    actor = Character(name="Alice")
    victim = Character(name="Bob", sex=Sex.MALE)
    onlooker = Character(name="Eve")
    room.add_character(actor)
    room.add_character(victim)
    room.add_character(onlooker)
    return room, actor, victim, onlooker


def test_smile_command_sends_messages():
    load_socials("data/socials.json")
    _, actor, victim, onlooker = setup_room()
    process_command(actor, "smile Bob")
    assert actor.messages[-1] == "You smile at him."
    assert victim.messages[-1] == "Alice smiles at you."
    assert onlooker.messages[-1] == "Alice beams a smile at Bob."
    actor.messages.clear()
    victim.messages.clear()
    onlooker.messages.clear()
    process_command(actor, "smile")
    assert actor.messages[-1] == "You smile happily."
    assert onlooker.messages[-1] == "Alice smiles happily."
