from mud.commands import process_command
from mud.models.character import character_registry
from mud.models.constants import CommFlag, LEVEL_IMMORTAL
from mud.registry import (
    area_registry,
    mob_registry,
    obj_registry,
    room_registry,
)
from mud.world import create_test_character, initialize_world


def setup_function(function):
    room_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    area_registry.clear()
    character_registry.clear()
    initialize_world("area/area.lst")


def test_tell_command():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    out = process_command(alice, "tell Bob hello")
    assert out == "You tell Bob, 'hello'"
    assert "Alice tells you, 'hello'" in bob.messages


def test_shout_respects_mute_and_ban():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    cara = create_test_character("Cara", 3001)
    bob.muted_channels.add("shout")
    out = process_command(alice, "shout hello")
    assert out == "You shout, 'hello'"
    assert "Alice shouts, 'hello'" in cara.messages
    assert all("hello" not in m for m in bob.messages)
    alice.banned_channels.add("shout")
    out = process_command(alice, "shout again")
    assert out == "You are banned from shout."
    assert all("again" not in m for m in cara.messages)


def test_tell_respects_mute_and_ban():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)
    bob.muted_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "They aren't listening."
    assert not bob.messages
    alice.banned_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "You are banned from tell."


def test_shout_and_tell_respect_comm_flags():
    alice = create_test_character("Alice", 3001)
    bob = create_test_character("Bob", 3001)

    out = process_command(alice, "shout")
    assert out == "You will no longer hear shouts."
    assert alice.has_comm_flag(CommFlag.SHOUTSOFF)

    bob.messages.clear()
    out = process_command(alice, "shout hello")
    assert out == "You must turn shouts back on first."
    assert not bob.messages

    out = process_command(alice, "shout")
    assert out == "You can hear shouts again."
    assert not alice.has_comm_flag(CommFlag.SHOUTSOFF)

    alice.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "shout hi")
    assert out == "You must turn off quiet mode first."
    alice.clear_comm_flag(CommFlag.QUIET)

    bob.messages.clear()
    out = process_command(alice, "shout hi")
    assert out == "You shout, 'hi'"
    assert alice.wait == 12
    assert "Alice shouts, 'hi'" in bob.messages

    alice.set_comm_flag(CommFlag.NOTELL)
    bob.messages.clear()
    out = process_command(alice, "tell Bob hi")
    assert out == "Your message didn't get through."
    assert not bob.messages

    alice.clear_comm_flag(CommFlag.NOTELL)
    alice.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "tell Bob hi")
    assert out == "You must turn off quiet mode first."
    alice.clear_comm_flag(CommFlag.QUIET)

    bob.set_comm_flag(CommFlag.QUIET)
    out = process_command(alice, "tell Bob hi")
    assert out == "Bob is not receiving tells."
    assert not bob.messages


def test_clantalk_reaches_clan_members():
    leader = create_test_character("Leader", 3001)
    ally = create_test_character("Ally", 3001)
    outsider = create_test_character("Outsider", 3001)

    leader.clan = 1
    ally.clan = 1
    outsider.clan = 2

    out = process_command(leader, "clan Rally now")
    assert out == "You clan 'Rally now'"
    assert "Leader clans, 'Rally now'" in ally.messages
    assert all("Rally now" not in msg for msg in outsider.messages)

    toggle_off = process_command(leader, "clan")
    assert toggle_off == "Clan channel is now OFF."
    assert leader.has_comm_flag(CommFlag.NOCLAN)
    toggle_on = process_command(leader, "clan")
    assert toggle_on == "Clan channel is now ON."
    assert not leader.has_comm_flag(CommFlag.NOCLAN)

    leader.set_comm_flag(CommFlag.NOCHANNELS)
    denied = process_command(leader, "clan denied")
    assert denied == "The gods have revoked your channel privileges."
    leader.clear_comm_flag(CommFlag.NOCHANNELS)

    ally.messages.clear()
    ally.set_comm_flag(CommFlag.QUIET)
    process_command(leader, "clan hush")
    assert all("hush" not in msg for msg in ally.messages)


def test_clantalk_ignores_quiet_on_speaker():
    leader = create_test_character("Leader", 3001)
    ally = create_test_character("Ally", 3001)
    outsider = create_test_character("Outsider", 3001)

    leader.clan = 1
    ally.clan = 1
    outsider.clan = 2

    leader.set_comm_flag(CommFlag.QUIET)
    out = process_command(leader, "clan hush")
    assert out == "You clan 'hush'"
    assert "Leader clans, 'hush'" in ally.messages
    assert all("hush" not in msg for msg in outsider.messages)


def test_immtalk_restricts_to_immortals():
    mortal = create_test_character("Mortal", 3001)
    immortal = create_test_character("Immortal", 3001)
    watcher = create_test_character("Watcher", 3001)

    immortal.level = LEVEL_IMMORTAL
    watcher.trust = LEVEL_IMMORTAL

    denied = process_command(mortal, "immtalk hello")
    assert denied == "You aren't an immortal."

    out = process_command(immortal, "immtalk Greetings")
    assert out == "[Immortal]: Greetings"
    assert "[Immortal]: Greetings" in watcher.messages
    assert all("Greetings" not in msg for msg in mortal.messages)

    toggle_off = process_command(immortal, "immtalk")
    assert toggle_off == "Immortal channel is now OFF."
    assert immortal.has_comm_flag(CommFlag.NOWIZ)
    toggle_on = process_command(immortal, "immtalk")
    assert toggle_on == "Immortal channel is now ON."
    assert not immortal.has_comm_flag(CommFlag.NOWIZ)

    watcher.messages.clear()

    immortal.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels = process_command(immortal, "immtalk hush")
    assert nochannels == "[Immortal]: hush"
    assert "[Immortal]: hush" in watcher.messages
    immortal.clear_comm_flag(CommFlag.NOCHANNELS)

    watcher.messages.clear()
    immortal.set_comm_flag(CommFlag.QUIET)
    quiet_speaker = process_command(immortal, "immtalk hush2")
    assert quiet_speaker == "[Immortal]: hush2"
    assert "[Immortal]: hush2" in watcher.messages
    immortal.clear_comm_flag(CommFlag.QUIET)

    watcher.messages.clear()
    watcher.set_comm_flag(CommFlag.NOWIZ)
    process_command(immortal, "immtalk Hidden")
    assert all("Hidden" not in msg for msg in watcher.messages)


def test_immtalk_bypasses_nochannels_for_speaker():
    mortal = create_test_character("Mortal", 3001)
    immortal = create_test_character("Immortal", 3001)
    watcher = create_test_character("Watcher", 3001)

    immortal.level = LEVEL_IMMORTAL
    watcher.trust = LEVEL_IMMORTAL

    immortal.set_comm_flag(CommFlag.NOCHANNELS)
    immortal.set_comm_flag(CommFlag.QUIET)

    out = process_command(immortal, "immtalk hush")
    assert out == "[Immortal]: hush"
    assert "[Immortal]: hush" in watcher.messages
    assert all("hush" not in msg for msg in mortal.messages)
