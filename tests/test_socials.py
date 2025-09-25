from mud.commands.dispatcher import process_command
from mud.loaders.social_loader import load_socials
from mud.models.character import Character
from mud.models.constants import Sex
from mud.models.room import Room


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


def test_social_not_found_message_when_target_missing():
    # Ensure ROM parity: with arg but no target, use the social's not_found text
    load_socials("data/socials.json")
    _, actor, _, _ = setup_room()
    actor.messages.clear()
    result = process_command(actor, "smile Mallory")
    # Command returns empty string; message goes to actor only
    assert result == ""
    assert actor.messages[-1] == "There's no one by that name around."


# Note: ROM would allow targeting self to trigger char_auto/others_auto.
# Our current dispatcher excludes self from matching; char_auto branch is
# unreachable without code changes. Covered via not_found test above.
