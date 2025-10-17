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


def make_player(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.desc = object()
    return char


def test_tell_command():
    alice = make_player("Alice", 3001)
    bob = make_player("Bob", 3001)
    out = process_command(alice, "tell Bob hello")
    assert out == "You tell Bob, 'hello'"
    assert "Alice tells you, 'hello'" in bob.messages


def test_shout_respects_mute_and_ban():
    alice = make_player("Alice", 3001)
    bob = make_player("Bob", 3001)
    cara = make_player("Cara", 3001)
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
    alice = make_player("Alice", 3001)
    bob = make_player("Bob", 3001)
    bob.muted_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "They aren't listening."
    assert not bob.messages
    alice.banned_channels.add("tell")
    out = process_command(alice, "tell Bob hi")
    assert out == "You are banned from tell."


def test_shout_and_tell_respect_comm_flags():
    alice = make_player("Alice", 3001)
    bob = make_player("Bob", 3001)

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


def test_question_channel_toggle_and_broadcast():
    asker = make_player("Asker", 3001)
    listener = make_player("Listener", 3001)
    muted = make_player("Muted", 3001)
    quiet = make_player("Quiet", 3001)

    muted.muted_channels.add("question")
    quiet.set_comm_flag(CommFlag.QUIET)

    out = process_command(asker, "question Where are the guildmasters?")
    assert out == "{qYou question '{QWhere are the guildmasters?{q'{x"
    assert "{qAsker questions '{QWhere are the guildmasters?{q'{x" in listener.messages
    assert all("guildmasters" not in msg for msg in muted.messages)
    assert all("guildmasters" not in msg for msg in quiet.messages)

    toggle_off = process_command(asker, "question")
    assert toggle_off == "Q/A channel is now OFF."
    assert asker.has_comm_flag(CommFlag.NOQUESTION)
    toggle_on = process_command(asker, "question")
    assert toggle_on == "Q/A channel is now ON."
    assert not asker.has_comm_flag(CommFlag.NOQUESTION)


def test_answer_channel_respects_comm_flags():
    responder = make_player("Responder", 3001)
    listener = make_player("Listener", 3001)
    blocked = make_player("Blocked", 3001)

    blocked.set_comm_flag(CommFlag.NOQUESTION)

    responder.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(responder, "answer I'm here.")
    assert quiet_msg == "You must turn off quiet mode first."
    responder.clear_comm_flag(CommFlag.QUIET)

    responder.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(responder, "answer Check the quad.")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    responder.clear_comm_flag(CommFlag.NOCHANNELS)

    out = process_command(responder, "answer Ask the guard to help.")
    assert out == "{fYou answer '{FAsk the guard to help.{f'{x"
    assert "{fResponder answers '{FAsk the guard to help.{f'{x" in listener.messages
    assert all("guard" not in msg for msg in blocked.messages)


def test_music_channel_toggle_and_broadcast():
    bard = make_player("Bard", 3001)
    fan = make_player("Fan", 3001)
    muted = make_player("Muted", 3001)
    critic = make_player("Critic", 3001)

    muted.muted_channels.add("music")
    critic.set_comm_flag(CommFlag.NOMUSIC)

    out = process_command(bard, "music A hymn to Midgaard")
    assert out == "{eYou MUSIC: '{EA hymn to Midgaard{e'{x"
    assert "{eBard MUSIC: '{EA hymn to Midgaard{e'{x" in fan.messages
    assert all("Midgaard" not in msg for msg in muted.messages)
    assert all("Midgaard" not in msg for msg in critic.messages)

    toggle_off = process_command(bard, "music")
    assert toggle_off == "Music channel is now OFF."
    assert bard.has_comm_flag(CommFlag.NOMUSIC)
    toggle_on = process_command(bard, "music")
    assert toggle_on == "Music channel is now ON."
    assert not bard.has_comm_flag(CommFlag.NOMUSIC)

    bard.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(bard, "music Quiet ballad")
    assert quiet_msg == "You must turn off quiet mode first."
    bard.clear_comm_flag(CommFlag.QUIET)

    bard.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(bard, "music Loud ballad")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    bard.clear_comm_flag(CommFlag.NOCHANNELS)


def test_auction_channel_toggle_and_broadcast():
    seller = make_player("Seller", 3001)
    bidder = make_player("Bidder", 3001)
    muted = make_player("Muted", 3001)
    quiet = make_player("Quiet", 3001)
    noauction = make_player("NoAuction", 3001)

    muted.muted_channels.add("auction")
    quiet.set_comm_flag(CommFlag.QUIET)
    noauction.set_comm_flag(CommFlag.NOAUCTION)

    out = process_command(seller, "auction Rare blade")
    assert out == "{aYou auction '{ARare blade{a'{x"
    assert "{aSeller auctions '{ARare blade{a'{x" in bidder.messages
    assert all("Rare blade" not in msg for msg in muted.messages)
    assert all("Rare blade" not in msg for msg in quiet.messages)
    assert all("Rare blade" not in msg for msg in noauction.messages)
    assert not seller.has_comm_flag(CommFlag.NOAUCTION)

    toggle_off = process_command(seller, "auction")
    assert toggle_off == "{aAuction channel is now OFF.{x"
    assert seller.has_comm_flag(CommFlag.NOAUCTION)

    toggle_on = process_command(seller, "auction")
    assert toggle_on == "{aAuction channel is now ON.{x"
    assert not seller.has_comm_flag(CommFlag.NOAUCTION)

    seller.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(seller, "auction hush")
    assert quiet_msg == "You must turn off quiet mode first."
    seller.clear_comm_flag(CommFlag.QUIET)

    seller.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(seller, "auction hush")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    seller.clear_comm_flag(CommFlag.NOCHANNELS)

    seller.banned_channels.add("auction")
    banned_msg = process_command(seller, "auction hush")
    assert banned_msg == "You are banned from auction."


def test_gossip_channel_toggle_and_broadcast():
    gossiper = make_player("Gossiper", 3001)
    listener = make_player("Listener", 3001)
    muted = make_player("Muted", 3001)
    quiet = make_player("Quiet", 3001)
    nogossip = make_player("NoGossip", 3001)

    muted.muted_channels.add("gossip")
    quiet.set_comm_flag(CommFlag.QUIET)
    nogossip.set_comm_flag(CommFlag.NOGOSSIP)

    out = process_command(gossiper, "gossip Have you heard?")
    assert out == "{dYou gossip '{tHave you heard?{d'{x"
    assert "{dGossiper gossips '{tHave you heard?{d'{x" in listener.messages
    assert all("heard" not in msg for msg in muted.messages)
    assert all("heard" not in msg for msg in quiet.messages)
    assert all("heard" not in msg for msg in nogossip.messages)

    toggle_off = process_command(gossiper, "gossip")
    assert toggle_off == "Gossip channel is now OFF."
    assert gossiper.has_comm_flag(CommFlag.NOGOSSIP)
    toggle_on = process_command(gossiper, "gossip")
    assert toggle_on == "Gossip channel is now ON."
    assert not gossiper.has_comm_flag(CommFlag.NOGOSSIP)

    gossiper.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(gossiper, "gossip hush")
    assert quiet_msg == "You must turn off quiet mode first."
    gossiper.clear_comm_flag(CommFlag.QUIET)

    gossiper.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(gossiper, "gossip hush")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    gossiper.clear_comm_flag(CommFlag.NOCHANNELS)


def test_grats_channel_respects_mutes():
    celebrant = make_player("Celebrant", 3001)
    listener = make_player("Listener", 3001)
    muted = make_player("Muted", 3001)
    quiet = make_player("Quiet", 3001)
    nograts = make_player("NoGrats", 3001)

    muted.muted_channels.add("grats")
    quiet.set_comm_flag(CommFlag.QUIET)
    nograts.set_comm_flag(CommFlag.NOGRATS)

    out = process_command(celebrant, "grats Great victory!")
    assert out == "{tYou grats 'Great victory!'{x"
    assert "{tCelebrant grats 'Great victory!'{x" in listener.messages
    assert all("victory" not in msg for msg in muted.messages)
    assert all("victory" not in msg for msg in quiet.messages)
    assert all("victory" not in msg for msg in nograts.messages)

    toggle_off = process_command(celebrant, "grats")
    assert toggle_off == "Grats channel is now OFF."
    assert celebrant.has_comm_flag(CommFlag.NOGRATS)
    toggle_on = process_command(celebrant, "grats")
    assert toggle_on == "Grats channel is now ON."
    assert not celebrant.has_comm_flag(CommFlag.NOGRATS)

    celebrant.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(celebrant, "grats hush")
    assert quiet_msg == "You must turn off quiet mode first."
    celebrant.clear_comm_flag(CommFlag.QUIET)

    celebrant.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(celebrant, "grats hush")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    celebrant.clear_comm_flag(CommFlag.NOCHANNELS)


def test_quote_channel_toggle_and_broadcast():
    quoter = make_player("Quoter", 3001)
    listener = make_player("Listener", 3001)
    muted = make_player("Muted", 3001)
    quiet = make_player("Quiet", 3001)
    noquote = make_player("NoQuote", 3001)

    muted.muted_channels.add("quote")
    quiet.set_comm_flag(CommFlag.QUIET)
    noquote.set_comm_flag(CommFlag.NOQUOTE)

    out = process_command(quoter, "quote Knowledge is power")
    assert out == "{hYou quote '{HKnowledge is power{h'{x"
    assert "{hQuoter quotes '{HKnowledge is power{h'{x" in listener.messages
    assert all("power" not in msg for msg in muted.messages)
    assert all("power" not in msg for msg in quiet.messages)
    assert all("power" not in msg for msg in noquote.messages)

    toggle_off = process_command(quoter, "quote")
    assert toggle_off == "{hQuote channel is now OFF.{x"
    assert quoter.has_comm_flag(CommFlag.NOQUOTE)
    toggle_on = process_command(quoter, "quote")
    assert toggle_on == "{hQuote channel is now ON.{x"
    assert not quoter.has_comm_flag(CommFlag.NOQUOTE)

    quoter.set_comm_flag(CommFlag.QUIET)
    quiet_msg = process_command(quoter, "quote hush")
    assert quiet_msg == "You must turn off quiet mode first."
    quoter.clear_comm_flag(CommFlag.QUIET)

    quoter.set_comm_flag(CommFlag.NOCHANNELS)
    nochannels_msg = process_command(quoter, "quote hush")
    assert nochannels_msg == "The gods have revoked your channel privileges."
    quoter.clear_comm_flag(CommFlag.NOCHANNELS)


def test_clantalk_reaches_clan_members():
    leader = make_player("Leader", 3001)
    ally = make_player("Ally", 3001)
    outsider = make_player("Outsider", 3001)

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
    leader = make_player("Leader", 3001)
    ally = make_player("Ally", 3001)
    outsider = make_player("Outsider", 3001)

    leader.clan = 1
    ally.clan = 1
    outsider.clan = 2

    leader.set_comm_flag(CommFlag.QUIET)
    out = process_command(leader, "clan hush")
    assert out == "You clan 'hush'"
    assert "Leader clans, 'hush'" in ally.messages
    assert all("hush" not in msg for msg in outsider.messages)


def test_immtalk_restricts_to_immortals():
    mortal = make_player("Mortal", 3001)
    immortal = make_player("Immortal", 3001)
    watcher = make_player("Watcher", 3001)

    immortal.level = LEVEL_IMMORTAL
    watcher.trust = LEVEL_IMMORTAL

    denied = process_command(mortal, "immtalk hello")
    assert denied == "You aren't an immortal."

    out = process_command(immortal, "immtalk Greetings")
    expected = "{i[{IImmortal{i]: Greetings{x\n\r"
    assert out == expected
    assert expected in watcher.messages
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
    expected_hush = "{i[{IImmortal{i]: hush{x\n\r"
    assert nochannels == expected_hush
    assert expected_hush in watcher.messages
    immortal.clear_comm_flag(CommFlag.NOCHANNELS)

    watcher.messages.clear()
    immortal.set_comm_flag(CommFlag.QUIET)
    quiet_speaker = process_command(immortal, "immtalk hush2")
    expected_hush2 = "{i[{IImmortal{i]: hush2{x\n\r"
    assert quiet_speaker == expected_hush2
    assert expected_hush2 in watcher.messages
    immortal.clear_comm_flag(CommFlag.QUIET)

    watcher.messages.clear()
    watcher.set_comm_flag(CommFlag.NOWIZ)
    process_command(immortal, "immtalk Hidden")
    assert all("Hidden" not in msg for msg in watcher.messages)


def test_immtalk_uses_rom_colour_envelope():
    speaker = make_player("Immortal", 3001)
    listener = make_player("Watcher", 3001)

    speaker.level = LEVEL_IMMORTAL
    listener.trust = LEVEL_IMMORTAL

    result = process_command(speaker, "immtalk Status report")
    expected = "{i[{IImmortal{i]: Status report{x\n\r"

    assert result == expected
    assert result.endswith("\n\r")
    assert expected in listener.messages


def test_immtalk_bypasses_nochannels_for_speaker():
    mortal = make_player("Mortal", 3001)
    immortal = make_player("Immortal", 3001)
    watcher = make_player("Watcher", 3001)

    immortal.level = LEVEL_IMMORTAL
    watcher.trust = LEVEL_IMMORTAL

    immortal.set_comm_flag(CommFlag.NOCHANNELS)
    immortal.set_comm_flag(CommFlag.QUIET)

    out = process_command(immortal, "immtalk hush")
    expected = "{i[{IImmortal{i]: hush{x\n\r"
    assert out == expected
    assert expected in watcher.messages
    assert all("hush" not in msg for msg in mortal.messages)


def test_reply_and_afk_buffer_match_rom():
    alice = make_player("Alice", 3001)
    bob = make_player("Bob", 3001)

    bob.messages.clear()
    bob.set_comm_flag(CommFlag.AFK)
    response = process_command(alice, "tell Bob hello there")
    assert response == "Bob is AFK, but your tell will go through when they return."
    assert bob.messages[-1] == "Alice tells you, 'hello there'"
    assert bob.reply is alice

    bob.messages.clear()
    bob.clear_comm_flag(CommFlag.AFK)
    bob.desc = None
    offline = process_command(alice, "tell Bob you around?")
    assert offline == "Bob seems to have misplaced their link...try again later."
    assert bob.messages[-1] == "Alice tells you, 'you around?'"
    assert bob.reply is alice

    bob.desc = object()
    alice.messages.clear()
    returned = process_command(bob, "reply Hey!")
    assert returned == "You tell Alice, 'Hey!'"
    assert alice.messages[-1] == "Bob tells you, 'Hey!'"
