"""ROM nanny.c login-flow parity tests.

Closes gaps from docs/parity/NANNY_C_AUDIT.md.

ROM C reference: src/nanny.c CON_READ_MOTD case (lines 742-819).
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, PCData


@pytest.mark.p1
def test_login_finalization_invokes_reset_char():
    """NANNY-014 — reset_char(ch) must run on every login.

    ROM C: src/nanny.c:760
        ```c
        ch->next = char_list;
        char_list = ch;
        d->connected = CON_PLAYING;
        reset_char (ch);
        ```

    reset_char (handler.c:520-745) clears mod_stat[], hitroll, damroll,
    saving_throw, restores max_hit/max_mana/max_move from pcdata->perm_*,
    and re-applies equipment affects. ROM calls it on the very first line
    of CON_READ_MOTD's body so a returning character with corrupted
    transient state always lands in a clean state.

    Python's `reset_char` exists in mud/handler.py:1046 but the login
    pipeline in mud/net/connection.py:handle_connection never calls it.
    This test asserts the network layer exposes a login-finalization
    helper that invokes reset_char.
    """
    from mud.net.connection import apply_login_state_refresh

    pcdata = PCData()
    pcdata.perm_hit = 100
    pcdata.perm_mana = 80
    pcdata.perm_move = 60
    pcdata.true_sex = 1
    pcdata.last_level = 5

    char = Character(name="Tester", level=10)
    char.is_npc = False
    char.pcdata = pcdata
    # Simulate transient corruption that ROM's reset_char fixes:
    char.max_hit = 50
    char.max_mana = 40
    char.max_move = 30
    char.hitroll = 17
    char.damroll = 9
    char.saving_throw = -3
    char.mod_stat = [4, 0, -1, 2, 0]
    char.armor = [200, 200, 200, 200]

    apply_login_state_refresh(char)

    # mirrors ROM src/handler.c:600-616 — reset_char restores from perm_* and zeros transients
    assert char.max_hit == 100
    assert char.max_mana == 80
    assert char.max_move == 60
    assert char.hitroll == 0
    assert char.damroll == 0
    assert char.saving_throw == 0
    assert list(char.mod_stat) == [0, 0, 0, 0, 0]
    assert char.armor == [100, 100, 100, 100]


@pytest.mark.p1
def test_login_broadcasts_entry_to_room():
    """NANNY-007 — `act("$n has entered the game.", TO_ROOM)` on login.

    ROM C: src/nanny.c:804
        ```c
        act ("$n has entered the game.", ch, NULL, NULL, TO_ROOM);
        ```

    Every other player in the room should see "<Name> has entered the
    game." when a character finishes the login state machine. The actor
    themselves does not receive the message (TO_ROOM excludes ch).
    """
    from mud.models.room import Room
    from mud.net.connection import broadcast_entry_to_room

    room = Room(vnum=9001, name="Login Test Room", description="", room_flags=0, sector_type=0)
    room.people = []

    arriver = Character(name="Arriver", level=10)
    arriver.is_npc = False
    onlooker = Character(name="Onlooker", level=10)
    onlooker.is_npc = False
    bystander = Character(name="Bystander", level=10)
    bystander.is_npc = False

    for occupant in (arriver, onlooker, bystander):
        room.people.append(occupant)
        occupant.room = room

    broadcast_entry_to_room(arriver)

    # mirrors ROM src/nanny.c:804 — TO_ROOM broadcast excludes the actor
    assert any("Arriver has entered the game." in m for m in onlooker.messages)
    assert any("Arriver has entered the game." in m for m in bystander.messages)
    assert all("entered the game" not in m for m in arriver.messages)


@pytest.mark.p1
def test_login_pet_follows_owner_into_room():
    """NANNY-008 — pet follows owner into the login room and is broadcast.

    ROM C: src/nanny.c:810-815
        ```c
        if (ch->pet != NULL)
        {
            char_to_room (ch->pet, ch->in_room);
            act ("$n has entered the game.", ch->pet, NULL, NULL, TO_ROOM);
        }
        ```

    On login, if the owner has a pet, the pet is placed in the owner's
    room and a TO_ROOM "<Pet> has entered the game." broadcast fires
    (excluding the pet itself).
    """
    from mud.models.room import Room
    from mud.net.connection import broadcast_entry_to_room

    room = Room(vnum=9002, name="Pet Login Room", description="", room_flags=0, sector_type=0)
    room.people = []

    owner = Character(name="Owner", level=10)
    owner.is_npc = False
    onlooker = Character(name="Onlooker", level=10)
    onlooker.is_npc = False

    pet = Character(name="Fido", short_descr="the dog Fido", level=5)
    pet.is_npc = True
    owner.pet = pet
    # Pet starts un-roomed (ROM treats the pet as detached until owner logs in).
    pet.room = None

    for occupant in (owner, onlooker):
        room.people.append(occupant)
        occupant.room = room

    broadcast_entry_to_room(owner)

    # mirrors ROM src/nanny.c:812 — char_to_room(ch->pet, ch->in_room)
    assert pet.room is room
    assert pet in room.people
    # mirrors ROM src/nanny.c:813 — TO_ROOM broadcast for the pet excludes the pet
    assert any("Fido has entered the game." in m for m in onlooker.messages)
    assert any("Owner has entered the game." in m for m in onlooker.messages)
    assert all("entered the game" not in m for m in (pet.messages or []))


@pytest.mark.p1
def test_denied_character_is_blocked_from_login():
    """NANNY-002 — characters with PLR_DENY must be denied access.

    ROM C: src/nanny.c:197-205
        ```c
        if (IS_SET (ch->act, PLR_DENY))
        {
            sprintf (log_buf, "Denying access to %s@%s.", argument, d->host);
            log_string (log_buf);
            send_to_desc ("You are denied access.\n\r", d);
            close_socket (d);
            return;
        }
        ```

    Python defines `PlayerFlag.DENY` (mud/models/constants.py:416) but the
    login path never checks it. A denied character should never reach the
    game loop.
    """
    from mud.models.constants import PlayerFlag
    from mud.net.connection import is_character_denied_access

    denied = Character(name="Banned", level=10)
    denied.is_npc = False
    denied.act = int(PlayerFlag.DENY)

    allowed = Character(name="Welcome", level=10)
    allowed.is_npc = False
    allowed.act = 0

    # mirrors ROM src/nanny.c:197 — IS_SET(ch->act, PLR_DENY)
    assert is_character_denied_access(denied) is True
    assert is_character_denied_access(allowed) is False


@pytest.mark.p1
def test_new_character_starts_with_recall_skill_at_50_percent():
    """NANNY-003 — `learned[gsn_recall] = 50` must be set on a new character.

    ROM C: src/nanny.c:579-581 (after CON_GET_ALIGNMENT)
        ```c
        group_add (ch, "rom basics", FALSE);
        group_add (ch, class_table[ch->class].base_group, FALSE);
        ch->pcdata->learned[gsn_recall] = 50;
        ```

    Without this seed, a new character cannot reliably `recall` to safety.
    Python's `from_orm` (mud/models/character.py:1052-1053) seeds the
    skill on every load: any character without a stored value gets 50%,
    and stored values are clamped to ≥50 on load. This test locks in
    that behavior.
    """
    from types import SimpleNamespace

    from mud.models.character import from_orm

    db_char = SimpleNamespace(
        name="Newbie",
        level=1,
        hp=20,
        room_vnum=3700,
        race=0,
        ch_class=0,
        sex=1,
        true_sex=1,
        alignment=0,
        act=0,
        hometown_vnum=3001,
        perm_stats="",
        size=0,
        form=0,
        parts=0,
        imm_flags=0,
        res_flags=0,
        vuln_flags=0,
        practice=5,
        train=3,
        perm_hit=100,
        perm_mana=100,
        perm_move=100,
        default_weapon_vnum=0,
        newbie_help_seen=False,
        creation_points=40,
        creation_groups="",
        creation_skills="",
        prompt=None,
        comm=0,
        player=None,
    )

    char = from_orm(db_char)

    # mirrors ROM src/nanny.c:581 — learned[gsn_recall] = 50
    assert char.pcdata.learned.get("recall", 0) >= 50


@pytest.mark.p1
def test_chosen_weapon_skill_seeded_at_40_percent():
    """NANNY-004 — `learned[*weapon_table[weapon].gsn] = 40` after CON_PICK_WEAPON.

    ROM C: src/nanny.c:653
        ```c
        ch->pcdata->learned[*weapon_table[weapon].gsn] = 40;
        ```

    Without the 40% seed, a freshly created character has 0% in their
    chosen weapon and cannot reliably hit anything. Python's `from_orm`
    (mud/models/character.py:1047-1051) seeds the picked weapon's skill
    on load via `_STARTING_WEAPON_SKILL_BY_VNUM`, clamping to ≥40.
    This regression test locks that in.
    """
    from types import SimpleNamespace

    from mud.models.character import from_orm
    from mud.models.constants import OBJ_VNUM_SCHOOL_SWORD

    db_char = SimpleNamespace(
        name="Swordy",
        level=1,
        hp=20,
        room_vnum=3700,
        race=0,
        ch_class=0,
        sex=1,
        true_sex=1,
        alignment=0,
        act=0,
        hometown_vnum=3001,
        perm_stats="",
        size=0,
        form=0,
        parts=0,
        imm_flags=0,
        res_flags=0,
        vuln_flags=0,
        practice=5,
        train=3,
        perm_hit=100,
        perm_mana=100,
        perm_move=100,
        default_weapon_vnum=int(OBJ_VNUM_SCHOOL_SWORD),
        newbie_help_seen=False,
        creation_points=40,
        creation_groups="",
        creation_skills="",
        prompt=None,
        comm=0,
        player=None,
    )

    char = from_orm(db_char)

    # mirrors ROM src/nanny.c:653 — learned[weapon_gsn] = 40 after weapon pick
    assert char.pcdata.learned.get("sword", 0) >= 40


@pytest.mark.p1
def test_character_login_disconnects_on_wrong_password(monkeypatch):
    """NANNY-001 — ROM closes the socket on the first wrong password.

    ROM C: src/nanny.c:269-274
        ```c
        if (strcmp (crypt (argument, ch->pcdata->pwd), ch->pcdata->pwd))
        {
            send_to_desc ("Wrong password.\n\r", d);
            close_socket (d);
            return;
        }
        ```

    ROM grants exactly one password attempt; failure closes the
    descriptor. The Python login loop instead let the user retry
    indefinitely, which diverges from ROM's "one chance" rule and weakens
    brute-force protection.

    This test asserts the character-login coroutine returns None
    (closing the connection) after a single bad password, instead of
    looping back to a non-ROM account prompt.
    """
    import asyncio

    from mud.account.account_service import LoginFailureReason, LoginResult
    from mud.net import connection as connection_mod

    sent: list[str] = []
    prompts: list[str] = []

    class FakeStream:
        host = "test.example"

        def set_ansi(self, _enabled):
            pass

    async def fake_prompt(_conn, label, *, hide_input=False):
        prompts.append(label)
        # Safety net: if the login loop ever asks twice, bail out by
        # returning None so the test fails on assertion instead of
        # hanging forever. ROM disconnects on first failure, so this
        # path should never trip.
        name_count = sum(1 for p in prompts if p == "Name: ")
        if name_count > 1:
            return None
        if label == "Name: ":
            return "tester"
        if label == "Password: ":
            return "wrongpw"
        return ""

    async def fake_send_line(_conn, msg):
        sent.append(msg)

    monkeypatch.setattr(connection_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(connection_mod, "_send_line", fake_send_line)
    monkeypatch.setattr(connection_mod, "character_exists", lambda _name: True, raising=False)
    monkeypatch.setattr(
        connection_mod,
        "login_with_host",
        lambda _name, _pw, _host, allow_reconnect=False: LoginResult(
            None,
            LoginFailureReason.BAD_CREDENTIALS,
            allow_reconnect,
        ),
        raising=False,
    )

    result = asyncio.run(connection_mod._run_character_login(FakeStream(), None))

    # mirrors ROM src/nanny.c:269-274 — one attempt, then close
    assert result is None
    assert any("Wrong password" in m for m in sent)
    assert prompts.count("Name: ") == 1
    assert "Account: " not in prompts


@pytest.mark.p1
def test_immortal_without_saved_room_routes_to_chat_room():
    """NANNY-006 — ROM routes immortals to ROOM_VNUM_CHAT (1200) when no saved room.

    ROM C: src/nanny.c:791-802
        ```c
        else if (ch->in_room  != NULL) char_to_room(ch, ch->in_room);
        else if (IS_IMMORTAL(ch))      char_to_room(ch, get_room_index(ROOM_VNUM_CHAT));
        else                            char_to_room(ch, get_room_index(ROOM_VNUM_TEMPLE));
        ```

    A returning immortal whose saved room can't be loaded should land in
    the immortal chat room (1200), not the temple (3001).
    """
    from mud.models.constants import ROOM_VNUM_CHAT, ROOM_VNUM_TEMPLE
    from mud.net.connection import default_login_room_vnum

    immortal = Character(name="ImmortalSouL", level=60)
    immortal.is_admin = True
    immortal.is_npc = False

    mortal = Character(name="MortalCoil", level=10)
    mortal.is_admin = False
    mortal.is_npc = False

    # mirrors ROM src/nanny.c:795-797 — immortal fallback room
    assert default_login_room_vnum(immortal) == int(ROOM_VNUM_CHAT)
    assert default_login_room_vnum(mortal) == int(ROOM_VNUM_TEMPLE)


@pytest.mark.p1
def test_first_login_resources_at_max():
    """NANNY-013 — first-login `hit=max_hit; mana=max_mana; move=max_move`.

    ROM C: src/nanny.c:772-775
        ```c
        ch->exp     = exp_per_level (ch, ch->pcdata->points);
        ch->hit     = ch->max_hit;
        ch->mana    = ch->max_mana;
        ch->move    = ch->max_move;
        ```

    A freshly-created character should enter the world at full
    resources. Python persists characters at level 1 with `hp=100` and
    `perm_hit=100`; `from_orm` sets max_* from perm_* and `hit` from
    saved hp. Combined with `apply_login_state_refresh` (NANNY-014)
    which restores max_* on every login, a brand-new character lands
    at full HP/mana/move.
    """
    from types import SimpleNamespace

    from mud.models.character import from_orm

    db_char = SimpleNamespace(
        name="Fresh",
        level=1,
        hp=100,
        room_vnum=3700,
        race=0,
        ch_class=0,
        sex=1,
        true_sex=1,
        alignment=0,
        act=0,
        hometown_vnum=3001,
        perm_stats="",
        size=0,
        form=0,
        parts=0,
        imm_flags=0,
        res_flags=0,
        vuln_flags=0,
        practice=5,
        train=3,
        perm_hit=100,
        perm_mana=100,
        perm_move=100,
        default_weapon_vnum=0,
        newbie_help_seen=False,
        creation_points=40,
        creation_groups="",
        creation_skills="",
        prompt=None,
        comm=0,
        player=None,
    )

    char = from_orm(db_char)

    # mirrors ROM src/nanny.c:772-775 — fresh character at full resources
    assert char.hit == char.max_hit == 100
    assert char.mana == char.max_mana == 100
    assert char.move == char.max_move == 100


@pytest.mark.p1
def test_name_validator_matches_rom_check_parse_name():
    """NANNY-012 / COMM-003 — name validator length floor and reserved words.

    ROM C: src/comm.c:1729 — ``if (strlen(name) < 2) return FALSE;``. The
    audit doc previously asserted a floor of 3 (and this test enforced it),
    but that was a misreading of ROM — the floor is 2. Fixed under
    COMM-003.

    Python keeps the local divergence of also reserving ``god``/``imp``
    (stricter than ROM by intent — see ``COMM_C_AUDIT.md`` deferred-by-design
    list).
    """
    from mud.account import is_valid_account_name

    # mirrors ROM src/comm.c:1729 — len < 2 → reject, len == 2 → accept
    assert is_valid_account_name("a") is False
    assert is_valid_account_name("Bo") is True
    assert is_valid_account_name("Bob") is True

    # mirrors ROM reserved-words list (with local god/imp additions)
    assert is_valid_account_name("god") is False
    assert is_valid_account_name("imp") is False
    assert is_valid_account_name("all") is False  # already covered, sanity check


@pytest.mark.p1
def test_name_validator_rejects_mob_keyword_collision():
    """COMM-004 — `is_valid_character_name` rejects names that collide
    with any mob prototype's `player_name` keyword list.

    mirrors ROM src/comm.c:1782-1796 — iterate `mob_index_hash`, reject if
    `is_name(name, pMobIndex->player_name)` matches. The mob-collision
    check lives on the new `is_valid_character_name` helper, not on
    `is_valid_account_name`, because Python account names have no ROM
    analogue and may legitimately match mob keywords.
    """
    from mud.account import is_valid_account_name, is_valid_character_name
    from mud.models.mob import MobIndex
    from mud.registry import mob_registry

    proto = MobIndex(vnum=99001, player_name="dragon ancient red")
    mob_registry[99001] = proto
    try:
        # any keyword in the mob's player_name list collides for character creation
        assert is_valid_character_name("dragon") is False
        assert is_valid_character_name("ancient") is False
        # an unrelated name still passes
        assert is_valid_character_name("Bob") is True
        # the syntactic-only validator does NOT enforce the collision
        assert is_valid_account_name("dragon") is True
    finally:
        mob_registry.pop(99001, None)


@pytest.mark.p1
def test_name_validator_rejects_clan_name():
    """COMM-006 — `is_valid_character_name` rejects names matching any
    clan in ``CLAN_TABLE``.

    mirrors ROM src/comm.c:1713-1718 — iterate ``clan_table`` and reject
    on `str_cmp` match.
    """
    from mud.account import is_valid_character_name

    # `rom` is a clan in CLAN_TABLE and would otherwise pass the syntactic
    # check; ensure the clan loop rejects it.
    assert is_valid_character_name("rom") is False
    # Case-insensitive match per ROM str_cmp
    assert is_valid_character_name("ROM") is False
    # `loner` is also a clan and is already in _RESERVED_NAMES — sanity.
    assert is_valid_character_name("loner") is False


@pytest.mark.p1
def test_login_state_refresh_is_a_noop_for_npcs():
    """reset_char early-returns on NPCs (handler.py:1067-1069). The login helper
    must preserve that behaviour — NPCs never traverse nanny.c login states.
    """
    from mud.net.connection import apply_login_state_refresh

    npc = Character(name="MobGuard", level=10)
    npc.is_npc = True
    npc.max_hit = 50
    npc.hitroll = 7
    npc.mod_stat = [3, 0, 0, 0, 0]

    apply_login_state_refresh(npc)

    assert npc.max_hit == 50
    assert npc.hitroll == 7


@pytest.mark.p2
def test_new_password_rejects_tilde(monkeypatch):
    """NANNY-011 — ROM rejects '~' in new passwords (src/nanny.c:396-405).

    ROM:
        ```c
        if (strcmp(crypt(argument, ch->name), ch->name) == 0)
        {
            write_to_buffer(d, "New password not acceptable, try again.\\n\\r", 0);
            ...
        }
        ```
    Plus the file-format poisoner check that rejects '~' in passwords because
    pfiles use '~' as field terminators. Python uses a DB backend so the
    practical risk is gone, but parity with ROM input validation is preserved.
    """
    import asyncio

    from mud.net import connection as connection_mod

    sent: list[str] = []
    answers = iter(["bad~pw", "goodpw", "goodpw"])

    class FakeStream:
        host = "test.example"

        def set_ansi(self, _enabled):
            pass

    labels = []

    async def fake_prompt(_conn, label, *, hide_input=False):
        del hide_input
        labels.append(label)
        return next(answers)

    async def fake_send_line(_conn, msg):
        sent.append(msg)

    monkeypatch.setattr(connection_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(connection_mod, "_send_line", fake_send_line)

    result = asyncio.run(connection_mod._prompt_new_password(FakeStream(), "Nova"))

    assert result == "goodpw"
    assert labels == [
        "Give me a password for Nova: ",
        "Password: ",
        "Please retype password: ",
    ]
    # mirrors ROM src/nanny.c:396-405 — '~' rejected with retry
    assert any("New password not acceptable" in m for m in sent)


# ---------------------------------------------------------------------------
# NANNY-RETRY-001 — Race invalid wording (src/nanny.c:460-471)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_race_invalid_retry_wording(monkeypatch):
    """NANNY-RETRY-001 — invalid race sends ROM-exact message then re-prompts.

    ROM C: src/nanny.c:460-471
        send_to_desc("That is not a valid race.\\n\\r", d);
        send_to_desc("The following races are available:\\n\\r  ", d);
        <loop: write name + space>
        write_to_buffer(d, "\\n\\r", 0);
        send_to_desc("What is your race? (help for more information) ", d);

    Observable transcript after one bad entry:
      - error message: "That is not a valid race." (NOT "That's")
      - race listing starts with "The following races are available:\n\r  "
      - re-prompt wording: "What is your race? (help for more information) "
        (note: parentheses, comma-space form, differs from help-branch)
    """
    import asyncio

    from mud.account.account_service import get_creation_races
    from mud.net import connection as conn_mod

    sent_lines: list[str] = []
    prompts: list[str] = []
    # First input: invalid; second: valid first race name
    races = get_creation_races()
    valid_name = races[0].name
    answers = iter(["notarace", valid_name])

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        return next(iter([next(answers)]))

    async def fake_send_line(_conn, msg):
        sent_lines.append(msg)

    async def fake_send(_conn, msg):
        pass

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)
    monkeypatch.setattr(conn_mod, "_send", fake_send)

    async def run():
        return await conn_mod._prompt_for_race(object())  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result is not None

    # mirrors ROM src/nanny.c:460 — "That is not a valid race." (not "That's")
    assert any(m == "That is not a valid race." for m in sent_lines), (
        f"Expected 'That is not a valid race.' in sent_lines={sent_lines!r}"
    )

    # mirrors ROM src/nanny.c:461 — listing header is "The following races are available:\n\r  "
    # _send_line wraps with \n\r so the stored string must start with the correct prefix
    race_listing_msgs = [m for m in sent_lines if "The following races are available" in m]
    assert race_listing_msgs, f"No race listing in sent_lines={sent_lines!r}"
    listing = race_listing_msgs[0]
    assert listing.startswith("The following races are available:\n\r  "), (
        f"Listing must start with 'The following races are available:\\n\\r  ', got {listing!r}"
    )

    # mirrors ROM src/nanny.c:471 — invalid-entry re-prompt (different from help-branch)
    assert "What is your race? (help for more information) " in prompts, (
        f"Expected invalid-entry re-prompt in prompts={prompts!r}"
    )


# ---------------------------------------------------------------------------
# NANNY-RETRY-002 — Race help branch re-prompt wording (src/nanny.c:444-453)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_race_help_branch_reprompt_wording(monkeypatch):
    """NANNY-RETRY-002 — after 'help', re-prompt uses help-branch form.

    ROM C: src/nanny.c:451-452
        send_to_desc("What is your race (help for more information)? ", d);

    Note the different wording vs the invalid-entry prompt:
      help branch:    "What is your race (help for more information)? "
      invalid branch: "What is your race? (help for more information) "
    """
    import asyncio

    from mud.account.account_service import get_creation_races
    from mud.net import connection as conn_mod

    prompts: list[str] = []
    races = get_creation_races()
    valid_name = races[0].name
    answers = iter(["help", valid_name])

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        val = next(answers)
        return val

    async def fake_send_line(_conn, msg):
        pass

    async def fake_send(_conn, msg):
        pass

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)
    monkeypatch.setattr(conn_mod, "_send", fake_send)

    async def run():
        return await conn_mod._prompt_for_race(object())  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result is not None

    # mirrors ROM src/nanny.c:451-452 — help branch keeps original prompt form
    assert "What is your race (help for more information)? " in prompts, (
        f"Expected help-branch re-prompt in prompts={prompts!r}"
    )
    # must NOT have switched to the invalid-entry prompt form after help
    assert prompts[-1] == "What is your race (help for more information)? ", (
        f"Last prompt should still be help-branch form, got {prompts!r}"
    )


# ---------------------------------------------------------------------------
# NANNY-RETRY-003 — Class invalid wording (src/nanny.c:538-539)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_class_invalid_retry_wording(monkeypatch):
    """NANNY-RETRY-003 — invalid class sends ROM-exact wording.

    ROM C: src/nanny.c:538-539
        send_to_desc("That's not a class.\\n\\rWhat IS your class? ", d);

    Two issues to check:
      1. Error message is "That's not a class." (NOT "That's not a valid class.")
      2. After the error the prompt changes to "What IS your class? " (capital IS)
    """
    import asyncio

    from mud.account.account_service import get_creation_classes
    from mud.net import connection as conn_mod

    sent_lines: list[str] = []
    prompts: list[str] = []
    classes = get_creation_classes()
    valid_name = classes[0].name
    answers = iter(["notaclass", valid_name])

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        return next(answers)

    async def fake_send_line(_conn, msg):
        sent_lines.append(msg)

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)

    async def run():
        return await conn_mod._prompt_for_class(object())  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result is not None

    # mirrors ROM src/nanny.c:538 — "That's not a class." (no "valid")
    assert any(m == "That's not a class." for m in sent_lines), (
        f"Expected \"That's not a class.\" in sent_lines={sent_lines!r}"
    )
    # mirrors ROM src/nanny.c:539 — re-prompt with capital IS
    assert "What IS your class? " in prompts, (
        f"Expected 'What IS your class? ' in prompts={prompts!r}"
    )


# ---------------------------------------------------------------------------
# NANNY-RETRY-004 — Customize invalid wording (src/nanny.c:626-628)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_customize_invalid_reprompt_wording(monkeypatch):
    """NANNY-RETRY-004 — invalid customize entry re-prompts with ROM wording.

    ROM C: src/nanny.c:626-628
        default:
            write_to_buffer(d, "Please answer (Y/N)? ", 0);
            return;

    Python's _prompt_yes_no sends "Please answer Y or N." but the
    customize prompt must send "Please answer (Y/N)? " to match ROM.

    This tests the CUSTOMIZE path only — not _prompt_ansi_preference or
    any other Y/N retry site, which have their own separate ROM wording.
    """
    import asyncio

    from mud.net import connection as conn_mod

    sent_lines: list[str] = []
    prompts: list[str] = []
    answers = iter(["x", "n"])  # invalid, then valid

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        return next(answers)

    async def fake_send_line(_conn, msg):
        sent_lines.append(msg)

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)

    async def run():
        return await conn_mod._prompt_customization_choice(object())  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result is False  # 'n' → no customization

    # mirrors ROM src/nanny.c:627 — "Please answer (Y/N)? " NOT "Please answer Y or N."
    assert any(m == "Please answer (Y/N)? " for m in sent_lines), (
        f"Expected 'Please answer (Y/N)? ' in sent_lines={sent_lines!r}"
    )
    # must NOT send the non-ROM wording
    assert not any("Please answer Y or N" in m for m in sent_lines), (
        f"Must not send 'Please answer Y or N' on customize path, got {sent_lines!r}"
    )


# ---------------------------------------------------------------------------
# NANNY-RETRY-005 — Weapon prompt newline format (src/nanny.c:611-624)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_weapon_prompt_uses_crlf(monkeypatch):
    r"""NANNY-RETRY-005 — weapon pick prompt uses \n\r (ROM) not bare \n.

    ROM C: src/nanny.c:612-623 (CON_DEFAULT_CHOICE 'N' branch)
        write_to_buffer(d, "\\n\\r", 2);
        write_to_buffer(d, "Please pick a weapon from the following choices:\\n\\r", 0);
        <loop: name + space>
        strcat(buf, "\\n\\rYour choice? ");
        write_to_buffer(d, buf, 0);

    The weapon prompt must use \\n\\r (telnet line ending) not bare \\n.
    Specifically the separator before "Your choice?" must be "\\n\\r".
    """
    import asyncio

    from mud.account.account_service import get_creation_classes
    from mud.net import connection as conn_mod

    prompts: list[str] = []
    sent_lines: list[str] = []
    classes = get_creation_classes()
    class_type = classes[0]
    answers = iter(["sword"])  # first weapon name, assume valid

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        # Return first word in the weapon list as the answer
        try:
            return next(answers)
        except StopIteration:
            return None

    async def fake_send_line(_conn, msg):
        sent_lines.append(msg)

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)

    async def run():
        return await conn_mod._prompt_for_weapon(object(), class_type)  # type: ignore[arg-type]

    asyncio.run(run())

    # mirrors ROM src/nanny.c:622 — \n\r before "Your choice? " (not bare \n)
    initial_prompts = [p for p in prompts if "Your choice?" in p]
    assert initial_prompts, f"Expected a prompt containing 'Your choice?', got {prompts!r}"
    assert all("\n\rYour choice? " in p for p in initial_prompts), (
        f"Weapon prompt must use \\n\\r before 'Your choice?', got {initial_prompts!r}"
    )


# ---------------------------------------------------------------------------
# NANNY-RETRY-006 — Weapon invalid newline format (src/nanny.c:638-649)
# ---------------------------------------------------------------------------


@pytest.mark.p1
def test_weapon_invalid_uses_crlf(monkeypatch):
    r"""NANNY-RETRY-006 — weapon invalid retry uses \n\r (ROM) not bare \n.

    ROM C: src/nanny.c:638-649 (CON_PICK_WEAPON invalid branch)
        write_to_buffer(d, "\\n\\r", 2);
        write_to_buffer(d, "That's not a valid selection. Choices are:\\n\\r", 0);
        <loop: name + space>
        strcat(buf, "\\n\\rYour choice? ");
        write_to_buffer(d, buf, 0);

    After an invalid weapon entry, the retry prompt must also use \\n\\r.
    """
    import asyncio

    from mud.account.account_service import get_creation_classes, get_weapon_choices
    from mud.net import connection as conn_mod

    prompts: list[str] = []
    sent_lines: list[str] = []
    classes = get_creation_classes()
    class_type = classes[0]
    weapon_choices = get_weapon_choices(class_type)
    valid_weapon = weapon_choices[0].lower() if weapon_choices else "sword"
    answers = iter(["notaweapon", valid_weapon])

    async def fake_prompt(_conn, label, **_kw):
        prompts.append(label)
        try:
            return next(answers)
        except StopIteration:
            return None

    async def fake_send_line(_conn, msg):
        sent_lines.append(msg)

    monkeypatch.setattr(conn_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(conn_mod, "_send_line", fake_send_line)

    async def run():
        return await conn_mod._prompt_for_weapon(object(), class_type)  # type: ignore[arg-type]

    asyncio.run(run())

    # mirrors ROM src/nanny.c:648 — retry prompt must use \n\r before "Your choice? "
    retry_prompts = [p for p in prompts if "Your choice?" in p]
    assert len(retry_prompts) >= 2, (
        f"Expected at least 2 'Your choice?' prompts (initial + retry), got {prompts!r}"
    )
    assert all("\n\rYour choice? " in p for p in retry_prompts), (
        f"Weapon retry prompt must use \\n\\r before 'Your choice?', got {retry_prompts!r}"
    )


@pytest.mark.p1
def test_new_character_starts_with_three_training_sessions():
    """NANNY-015 — A new PC starts with exactly 3 training sessions.

    ROM C: src/nanny.c:776-777 (CON_READ_MOTD, the ``if (ch->level == 0)``
    block that runs once for every newly created character):
        ```c
        ch->train = 3;
        ch->practice = 5;
        ```
    These two assignments are unconditional and run for *every* new PC,
    overwriting the ``ch->train = (40 - ch->pcdata->points + 1) / 2``
    formula computed earlier at src/nanny.c:684. The formula is therefore
    effectively dead — its result never survives to CON_PLAYING.

    QuickMUD diverged: ``CreationSelection.train_value()``
    (mud/account/account_service.py) implemented only the nanny.c:684
    formula and ``create_character`` consumed it (mud/net/connection.py),
    so an elf (race points = 5) started with ``(40 - 5 + 1)//2 = 18``
    training sessions instead of ROM's hardcoded 3. ``practice`` was
    correctly hardcoded to 5; ``train`` was not. The mismatched half of
    the pair is the tell.
    """
    from mud.account.account_service import (
        CreationSelection,
        get_creation_classes,
        get_creation_races,
    )

    def _by_name(items, name):
        for item in items:
            if item.name == name:
                return item
        raise AssertionError(f"{name!r} not in {[i.name for i in items]}")

    elf = _by_name(get_creation_races(), "elf")
    mage = _by_name(get_creation_classes(), "mage")

    # No customization: __post_init__ seeds the class default groups without
    # deducting points, leaving creation_points at the race base (5 for elf),
    # i.e. the path a player takes by answering "no" to "customize?".
    selection = CreationSelection(elf, mage)

    assert selection.train_value() == 3, (
        "ROM nanny.c:776 hardcodes ch->train = 3 for every new PC; the "
        "nanny.c:684 formula is overwritten and must not leak through."
    )
