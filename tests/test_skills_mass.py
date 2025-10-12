from mud.math.c_compat import c_div
from mud.combat import engine as combat_engine
from mud.models.character import Character, SpellEffect
from mud.models.constants import ActFlag, AffectFlag, DamageType, ImmFlag, Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int = 3100) -> Room:
    return Room(vnum=vnum, name=f"Room {vnum}")


def test_calm_stops_fights_and_applies_affect(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda *_: 999)

    caster = Character(name="Cleric", level=40, is_npc=False, hit=200, max_hit=200)
    enemy = Character(
        name="Warrior",
        level=30,
        is_npc=True,
        hit=180,
        max_hit=180,
        default_pos=int(Position.STANDING),
    )
    observer = Character(name="Witness", level=25, is_npc=False)

    room = _make_room()
    for character in (caster, enemy, observer):
        room.add_character(character)
        character.messages.clear()

    caster.position = int(Position.FIGHTING)
    enemy.position = int(Position.FIGHTING)
    caster.fighting = enemy
    enemy.fighting = caster

    assert skill_handlers.calm(caster) is True

    assert caster.fighting is None
    assert enemy.fighting is None
    assert Position(caster.position) == Position.STANDING
    assert Position(enemy.position) == Position.STANDING

    assert caster.has_affect(AffectFlag.CALM)
    assert enemy.has_affect(AffectFlag.CALM)
    assert observer.has_affect(AffectFlag.CALM)

    assert caster.hitroll == -5
    assert caster.damroll == -5
    assert enemy.hitroll == -2
    assert enemy.damroll == -2

    assert caster.messages[-1] == "A wave of calm passes over you."
    assert enemy.messages[-1] == "A wave of calm passes over you."
    assert observer.messages[-1] == "A wave of calm passes over you."


def test_calm_respects_undead_and_immunity(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda *_: 999)

    caster = Character(name="Cleric", level=40, is_npc=False)
    foe = Character(name="Raider", level=30, is_npc=True)
    undead = Character(
        name="Ghoul",
        level=28,
        is_npc=True,
        imm_flags=int(ImmFlag.MAGIC),
        act=int(ActFlag.UNDEAD),
    )

    room = _make_room(3105)
    for character in (caster, foe, undead):
        room.add_character(character)
        character.messages.clear()

    caster.position = int(Position.FIGHTING)
    foe.position = int(Position.FIGHTING)
    undead.position = int(Position.FIGHTING)

    caster.fighting = foe
    foe.fighting = caster

    assert skill_handlers.calm(caster) is False

    for character in (caster, foe, undead):
        assert not character.has_affect(AffectFlag.CALM)
        assert character.messages == []

    assert caster.fighting is foe
    assert foe.fighting is caster


def test_calm_uses_override_level_for_scrolls(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers.rng_mm, "number_range", lambda low, high: high)

    caster = Character(name="Novice", level=5, is_npc=False)
    foe = Character(name="Enforcer", level=30, is_npc=True)

    room = _make_room(3106)
    for character in (caster, foe):
        room.add_character(character)
        character.messages.clear()

    caster.position = int(Position.FIGHTING)
    foe.position = int(Position.FIGHTING)
    caster.fighting = foe
    foe.fighting = caster

    assert skill_handlers.calm(caster) is False
    assert not caster.has_affect(AffectFlag.CALM)
    assert not foe.has_affect(AffectFlag.CALM)
    assert caster.fighting is foe
    assert foe.fighting is caster

    assert skill_handlers.calm(caster, override_level=50) is True
    assert caster.fighting is None
    assert foe.fighting is None
    assert caster.has_affect(AffectFlag.CALM)
    assert foe.has_affect(AffectFlag.CALM)


def test_holy_word_buffs_allies_and_curses_enemies(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)
    monkeypatch.setattr(skill_handlers.rng_mm, "dice", lambda number, size: number * size)

    caster = Character(
        name="High Cleric",
        level=40,
        alignment=450,
        is_npc=False,
        hit=300,
        max_hit=300,
        move=100,
    )
    ally = Character(name="Templar", level=35, alignment=400, is_npc=False)
    enemy = Character(name="Dreadknight", level=38, alignment=-500, is_npc=True, hit=350, max_hit=350)
    trainer = Character(name="Trainer", level=30, is_npc=True, act=int(ActFlag.TRAIN))
    witness = Character(name="Witness", level=20, is_npc=False)

    room = _make_room()
    for character in (caster, ally, enemy, trainer, witness):
        room.add_character(character)
        character.messages.clear()

    enemy_start_hit = enemy.hit

    assert skill_handlers.holy_word(caster) is True

    assert any("You utter a word of divine power." == msg for msg in caster.messages)
    assert caster.messages[-1] == "You feel drained."
    assert caster.move == 0
    assert caster.hit == c_div(300, 2)

    assert ally.has_spell_effect("frenzy")
    assert ally.has_spell_effect("bless")

    assert enemy.has_spell_effect("curse")
    assert enemy.has_affect(AffectFlag.CURSE)
    assert enemy.hit == enemy_start_hit - (caster.level * 6)
    assert "You are struck down!" in enemy.messages

    assert not trainer.has_affect(AffectFlag.CURSE)
    assert getattr(trainer, "hit", 0) == 0

    assert any(message == "High Cleric utters a word of divine power!" for message in witness.messages)


def test_holy_word_triggers_death_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)
    monkeypatch.setattr(skill_handlers.rng_mm, "dice", lambda number, size: number * size)

    pipeline_calls: dict[str, int] = {
        "group_gain": 0,
        "wiznet": 0,
        "raw_kill": 0,
        "auto_actions": 0,
    }

    def track_group_gain(attacker, victim):
        pipeline_calls["group_gain"] += 1

    def track_send_wiznet(attacker, victim):
        pipeline_calls["wiznet"] += 1

    def track_raw_kill(victim):
        pipeline_calls["raw_kill"] += 1
        return object()

    def track_auto_actions(attacker, corpse):
        pipeline_calls["auto_actions"] += 1

    monkeypatch.setattr(combat_engine, "group_gain", track_group_gain)
    monkeypatch.setattr(combat_engine, "_send_wiznet_death", track_send_wiznet)
    monkeypatch.setattr(combat_engine, "raw_kill", track_raw_kill)
    monkeypatch.setattr(combat_engine, "_handle_auto_actions", track_auto_actions)

    recorded_damage_types: list[DamageType | int] = []
    original_apply_damage = combat_engine.apply_damage

    def tracking_apply_damage(attacker, victim, damage, dam_type, *, dt=None, immune=False, show=True):
        recorded_damage_types.append(dam_type)
        return original_apply_damage(attacker, victim, damage, dam_type, dt=dt, immune=immune, show=show)

    monkeypatch.setattr(skill_handlers, "apply_damage", tracking_apply_damage)

    caster = Character(
        name="High Cleric",
        level=40,
        alignment=500,
        is_npc=False,
        hit=200,
        max_hit=200,
        move=100,
    )
    enemy = Character(
        name="Heretic",
        level=35,
        alignment=-600,
        is_npc=True,
        hit=60,
        max_hit=60,
    )

    room = _make_room()
    room.add_character(caster)
    room.add_character(enemy)

    caster.fighting = enemy
    enemy.fighting = caster
    caster.position = Position.FIGHTING
    enemy.position = Position.FIGHTING

    assert skill_handlers.holy_word(caster) is True

    assert recorded_damage_types == [DamageType.ENERGY]
    assert pipeline_calls == {
        "group_gain": 1,
        "wiznet": 1,
        "raw_kill": 1,
        "auto_actions": 1,
    }
    assert caster.fighting is None
    assert enemy.fighting is None
    assert caster.position == Position.STANDING
    assert enemy.position == Position.DEAD


def test_holy_word_bypasses_weapon_defenses(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)
    monkeypatch.setattr(skill_handlers.rng_mm, "dice", lambda number, size: number * size)

    defenses_called = {"shield": False, "parry": False, "dodge": False}

    def _record(name):
        def _recorder(attacker, victim):
            defenses_called[name] = True
            return False

        return _recorder

    monkeypatch.setattr(combat_engine, "check_shield_block", _record("shield"))
    monkeypatch.setattr(combat_engine, "check_parry", _record("parry"))
    monkeypatch.setattr(combat_engine, "check_dodge", _record("dodge"))

    caster = Character(
        name="Cleric",
        level=40,
        alignment=500,
        is_npc=False,
        hit=200,
        max_hit=200,
        move=100,
    )
    enemy = Character(
        name="Heretic",
        level=35,
        alignment=-500,
        is_npc=True,
        hit=150,
        max_hit=150,
    )

    room = _make_room()
    room.add_character(caster)
    room.add_character(enemy)

    enemy_start_hit = enemy.hit

    assert skill_handlers.holy_word(caster) is True

    assert defenses_called == {"shield": False, "parry": False, "dodge": False}
    assert enemy.hit < enemy_start_hit


def test_faerie_fog_reveals_hidden_targets(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: False)

    caster = Character(name="Illusionist", level=30, is_npc=False)
    hidden = Character(name="Sneak", level=25, is_npc=False)
    immortal = Character(name="Immortal", level=60, is_npc=False, invis_level=2)

    room = _make_room(3101)
    for character in (caster, hidden, immortal):
        room.add_character(character)

    hidden.apply_spell_effect(
        SpellEffect(
            name="invis",
            duration=12,
            level=20,
            affect_flag=AffectFlag.INVISIBLE,
        )
    )
    hidden.apply_spell_effect(
        SpellEffect(
            name="mass invis",
            duration=24,
            level=20,
            affect_flag=AffectFlag.INVISIBLE,
        )
    )
    hidden.add_affect(AffectFlag.HIDE)
    hidden.add_affect(AffectFlag.SNEAK)

    assert skill_handlers.faerie_fog(caster) is True

    assert not hidden.has_affect(AffectFlag.INVISIBLE)
    assert not hidden.has_affect(AffectFlag.HIDE)
    assert not hidden.has_affect(AffectFlag.SNEAK)
    assert not hidden.has_spell_effect("invis")
    assert not hidden.has_spell_effect("mass invis")
    assert hidden.messages[-1] == "You are revealed!"
    assert caster.messages[-1] == "Sneak is revealed!"
    assert immortal.messages[0] == "Illusionist conjures a cloud of purple smoke."
    assert immortal.messages[-1] == "Sneak is revealed!"


def test_faerie_fog_respects_saves(monkeypatch) -> None:
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *args, **kwargs: True)

    caster = Character(name="Illusionist", level=30, is_npc=False)
    hidden = Character(name="Sneak", level=25, is_npc=False)

    room = _make_room(3102)
    room.add_character(caster)
    room.add_character(hidden)

    hidden.apply_spell_effect(
        SpellEffect(
            name="invis",
            duration=12,
            level=20,
            affect_flag=AffectFlag.INVISIBLE,
        )
    )
    hidden.add_affect(AffectFlag.HIDE)

    assert skill_handlers.faerie_fog(caster) is False

    assert hidden.has_affect(AffectFlag.INVISIBLE)
    assert hidden.has_affect(AffectFlag.HIDE)
    assert hidden.has_spell_effect("invis")
    assert "You are revealed!" not in hidden.messages
    assert caster.messages[-1] == "You conjure a cloud of purple smoke."
