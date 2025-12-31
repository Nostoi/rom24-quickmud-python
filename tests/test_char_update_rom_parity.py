"""
Character Update ROM Parity Tests

Tests for ROM character update tick mechanics (HP/mana/move regeneration).
ROM Reference: src/update.c lines 149-365 (hit_gain, mana_gain, move_gain)

Priority: P0 (high - core gameplay regeneration formulas)

Coverage:
- Hit point regeneration formulas
- Mana point regeneration formulas
- Movement point regeneration formulas
- Position-based modifiers (sleeping, resting, fighting, standing)
- Condition-based penalties (hunger/thirst at 0)
- Affect-based modifiers (poison, plague, haste/slow, regeneration)
- Room heal/mana rate modifiers
- Furniture bonus modifiers
- Class-based mana regeneration differences
- Skill bonuses (fast healing, meditation)
"""

from __future__ import annotations

import pytest

from mud.characters.conditions import gain_condition
from mud.game_loop import hit_gain, mana_gain, move_gain
from mud.models.character import Character, PCData
from mud.models.constants import (
    AffectFlag,
    Condition,
    ItemType,
    Position,
    Stat,
)
from mud.models.object import Object, ObjIndex
from mud.models.room import Room
from mud.registry import (
    area_registry,
    mob_registry,
    obj_registry,
    room_registry,
)
from mud.world import create_test_character, initialize_world
from helpers_player import set_conditions


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestHitGainROMParity:
    """Test ROM hit point regeneration formulas.

    ROM Reference: src/update.c:149-230 (hit_gain function)
    """

    @pytest.mark.p0
    def test_hit_gain_npc_base_formula(self):
        """NPCs gain 5 + level HP per tick (base).

        ROM C: gain = 5 + ch->level;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.hit = 0
        mob.max_hit = 1000
        mob.position = int(Position.RESTING)

        gain = hit_gain(mob)

        assert gain == 15  # 5 + 10

    @pytest.mark.p0
    def test_hit_gain_npc_regeneration_doubles(self):
        """NPCs with AFF_REGENERATION gain 2x HP.

        ROM C: if (IS_AFFECTED(ch, AFF_REGENERATION)) gain *= 2;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.hit = 0
        mob.max_hit = 1000
        mob.position = int(Position.RESTING)
        mob.affected_by = int(AffectFlag.REGENERATION)

        gain = hit_gain(mob)

        assert gain == 30  # (5 + 10) * 2

    @pytest.mark.p0
    def test_hit_gain_npc_sleeping_bonus(self):
        """NPCs sleeping gain 1.5x HP (3 * gain / 2).

        ROM C: case POS_SLEEPING: gain = 3 * gain / 2; break;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.hit = 0
        mob.max_hit = 1000
        mob.position = int(Position.SLEEPING)

        gain = hit_gain(mob)

        # (5 + 10) * 3 / 2 = 15 * 3 / 2 = 45 / 2 = 22 (integer division)
        assert gain == 22

    @pytest.mark.p0
    def test_hit_gain_npc_fighting_penalty(self):
        """NPCs fighting gain 1/3 HP.

        ROM C: case POS_FIGHTING: gain /= 3; break;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.hit = 0
        mob.max_hit = 1000
        mob.position = int(Position.FIGHTING)

        gain = hit_gain(mob)

        # (5 + 10) / 3 = 15 / 3 = 5
        assert gain == 5

    @pytest.mark.p0
    def test_hit_gain_npc_standing_penalty(self):
        """NPCs standing/default gain 1/2 HP.

        ROM C: default: gain /= 2; break;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.hit = 0
        mob.max_hit = 1000
        mob.position = int(Position.STANDING)

        gain = hit_gain(mob)

        # (5 + 10) / 2 = 15 / 2 = 7 (integer division)
        assert gain == 7

    @pytest.mark.p0
    def test_hit_gain_player_base_formula(self):
        """Players gain max(3, CON-3 + level/2) + hp_max - 10.

        ROM C: gain = UMAX(3, get_curr_stat(ch, STAT_CON) - 3 + ch->level/2);
               gain += class_table[ch->class].hp_max - 10;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]  # CON = 13
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        # UMAX(3, 13 - 3 + 20/2) = UMAX(3, 10 + 10) = 20
        # 20 + (8 - 10) = 20 + (-2) = 18  # hp_max=8 for mage (class 0)
        assert gain == 18

    @pytest.mark.p0
    def test_hit_gain_player_minimum_3(self):
        """Player HP gain is at least 3 (before class bonus).

        ROM C: gain = UMAX(3, ...);
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 1
        player.pcdata = PCData()
        player.perm_stat = [3, 3, 3, 3, 3]  # CON = 3 (very low)
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        # UMAX(3, 3 - 3 + 1/2) = UMAX(3, 0) = 3
        # 3 + (8 - 10) = 3 + (-2) = 1  # hp_max=8 for mage (class 0)
        assert gain == 1

    @pytest.mark.p0
    def test_hit_gain_player_resting_penalty(self):
        """Players resting gain 1/2 HP.

        ROM C: case POS_RESTING: gain /= 2; break;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.RESTING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        # Base = 18, resting = 18 / 2 = 9
        assert gain == 9

    @pytest.mark.p0
    def test_hit_gain_player_fighting_penalty(self):
        """Players fighting gain 1/6 HP.

        ROM C: case POS_FIGHTING: gain /= 6; break;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.FIGHTING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 3

    @pytest.mark.p0
    def test_hit_gain_player_standing_penalty(self):
        """Players standing gain 1/4 HP.

        ROM C: default: gain /= 4; break;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.STANDING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 4

    @pytest.mark.p0
    def test_hit_gain_hunger_penalty(self):
        """Hunger at 0 halves HP regen.

        ROM C: if (ch->pcdata->condition[COND_HUNGER] == 0) gain /= 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=0, thirst=48)

        gain = hit_gain(player)

        assert gain == 9

    @pytest.mark.p0
    def test_hit_gain_thirst_penalty(self):
        """Thirst at 0 halves HP regen.

        ROM C: if (ch->pcdata->condition[COND_THIRST] == 0) gain /= 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=0)

        gain = hit_gain(player)

        assert gain == 9

    @pytest.mark.p0
    def test_hit_gain_hunger_and_thirst_stack(self):
        """Hunger and thirst penalties stack (1/4 total).

        ROM C: Both conditions apply sequentially
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=0, thirst=0)

        gain = hit_gain(player)

        assert gain == 4

    @pytest.mark.p0
    def test_hit_gain_poison_penalty(self):
        """Poison reduces HP regen to 1/4.

        ROM C: if (IS_AFFECTED(ch, AFF_POISON)) gain /= 4;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        player.affected_by = int(AffectFlag.POISON)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 4

    @pytest.mark.p0
    def test_hit_gain_plague_penalty(self):
        """Plague reduces HP regen to 1/8.

        ROM C: if (IS_AFFECTED(ch, AFF_PLAGUE)) gain /= 8;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        player.affected_by = int(AffectFlag.PLAGUE)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 2

    @pytest.mark.p0
    def test_hit_gain_haste_penalty(self):
        """Haste reduces HP regen to 1/2.

        ROM C: if (IS_AFFECTED(ch, AFF_HASTE) || IS_AFFECTED(ch, AFF_SLOW)) gain /= 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        player.affected_by = int(AffectFlag.HASTE)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 9

    @pytest.mark.p0
    def test_hit_gain_slow_penalty(self):
        """Slow reduces HP regen to 1/2.

        ROM C: if (IS_AFFECTED(ch, AFF_HASTE) || IS_AFFECTED(ch, AFF_SLOW)) gain /= 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        player.affected_by = int(AffectFlag.SLOW)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 9

    @pytest.mark.p0
    def test_hit_gain_room_heal_rate_modifier(self):
        """Room heal_rate modifies HP regen.

        ROM C: gain = gain * ch->in_room->heal_rate / 100;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        # Set room heal rate to 200% (healing room)
        original_heal_rate = player.room.heal_rate
        try:
            player.room.heal_rate = 200
            gain = hit_gain(player)
            assert gain == 36
        finally:
            # Restore original heal_rate to avoid contaminating other tests
            player.room.heal_rate = original_heal_rate

    @pytest.mark.p0
    def test_hit_gain_furniture_heal_bonus(self):
        """Furniture value[3] modifies HP regen.

        ROM C: if (ch->on != NULL && ch->on->item_type == ITEM_FURNITURE)
                   gain = gain * ch->on->value[3] / 100;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        # Create healing bed (150% heal rate)
        bed_proto = ObjIndex(vnum=9999, short_descr="a healing bed", item_type=int(ItemType.FURNITURE))
        bed = Object(instance_id=None, prototype=bed_proto)
        bed.value = [0, 0, 0, 150, 100]  # value[3] = 150% heal
        player.on = bed

        gain = hit_gain(player)

        assert gain == 27

    @pytest.mark.p0
    def test_hit_gain_deficit_cap(self):
        """HP gain cannot exceed deficit to max HP.

        ROM C: return UMIN(gain, ch->max_hit - ch->hit);
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 995  # Only 5 HP needed to max
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 5


class TestManaGainROMParity:
    """Test ROM mana point regeneration formulas.

    ROM Reference: src/update.c:234-307 (mana_gain function)
    """

    @pytest.mark.p0
    def test_mana_gain_npc_base_formula(self):
        """NPCs gain 5 + level mana per tick.

        ROM C: gain = 5 + ch->level;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.mana = 0
        mob.max_mana = 1000
        mob.position = int(Position.RESTING)

        gain = mana_gain(mob)

        assert gain == 15  # 5 + 10

    @pytest.mark.p0
    def test_mana_gain_player_base_formula(self):
        """Players gain (WIS + INT + level) / 2.

        ROM C: gain = (get_curr_stat(ch, STAT_INT) + get_curr_stat(ch, STAT_WIS) + ch->level) / 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 15, 17, 13, 13]  # STR, INT=15, WIS=17, DEX, CON
        player.mod_stat = [0, 0, 0, 0, 0]
        player.mana = 0
        player.max_mana = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = mana_gain(player)

        assert gain == 26

    @pytest.mark.p0
    def test_mana_gain_non_mana_class_penalty(self):
        """Non-mana classes (f_mana = False) gain half mana.

        ROM C: if (!class_table[ch->class].fMana) gain /= 2;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.ch_class = 3  # Warrior (class 3) is non-mana
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 15, 17, 13, 13]  # STR, INT=15, WIS=17, DEX, CON
        player.mod_stat = [0, 0, 0, 0, 0]
        player.mana = 0
        player.max_mana = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = mana_gain(player)

        assert gain == 13


class TestMoveGainROMParity:
    """Test ROM movement point regeneration formulas.

    ROM Reference: src/update.c:310-365 (move_gain function)
    """

    @pytest.mark.p0
    def test_move_gain_npc_base_formula(self):
        """NPCs gain level move per tick.

        ROM C: gain = ch->level;
        """
        mob = create_test_character("TestMob", 3001)
        mob.is_npc = True
        mob.level = 10
        mob.move = 0
        mob.max_move = 1000
        mob.position = int(Position.STANDING)

        gain = move_gain(mob)

        assert gain == 10

    @pytest.mark.p0
    def test_move_gain_player_base_formula(self):
        """Players gain max(15, level) move per tick.

        ROM C: gain = UMAX(15, ch->level);
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 18, 13]  # STR, INT, WIS, DEX=18, CON
        player.mod_stat = [0, 0, 0, 0, 0]
        player.move = 0
        player.max_move = 1000
        player.position = int(Position.STANDING)
        set_conditions(player, hunger=48, thirst=48)

        gain = move_gain(player)

        assert gain == 20

    @pytest.mark.p0
    def test_move_gain_player_sleeping_dex_bonus(self):
        """Players sleeping add DEX to move regen.

        ROM C: case POS_SLEEPING: gain += get_curr_stat(ch, STAT_DEX); break;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 18, 13]  # STR, INT, WIS, DEX=18, CON
        player.mod_stat = [0, 0, 0, 0, 0]
        player.move = 0
        player.max_move = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = move_gain(player)

        assert gain == 38


class TestCharUpdateEdgeCases:
    """Test edge cases and combined modifiers in character update.

    ROM Reference: src/update.c:661-904 (char_update function)
    """

    @pytest.mark.p0
    def test_hit_gain_multiple_penalties_stack(self):
        """All HP regen penalties stack multiplicatively.

        Test: standing (/4) + hunger (/2) + poison (/4)
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.STANDING)
        player.affected_by = int(AffectFlag.POISON)
        set_conditions(player, hunger=0, thirst=48)

        gain = hit_gain(player)

        # Base = 30, standing /4 = 7, hunger /2 = 3, poison /4 = 0 (integer division)
        assert gain == 0

    @pytest.mark.p0
    def test_room_and_furniture_modifiers_stack(self):
        """Room heal rate and furniture bonus stack multiplicatively.

        ROM C: gain *= room_rate / 100; gain *= furniture_rate / 100;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        # Room with 200% heal rate
        original_heal_rate = player.room.heal_rate
        try:
            player.room.heal_rate = 200

            # Furniture with 150% heal bonus
            bed_proto = ObjIndex(vnum=9999, short_descr="a healing bed", item_type=int(ItemType.FURNITURE))
            bed = Object(instance_id=None, prototype=bed_proto)
            bed.value = [0, 0, 0, 150, 100]
            player.on = bed

            gain = hit_gain(player)

            assert gain == 54
        finally:
            # Restore original heal_rate to avoid contaminating other tests
            player.room.heal_rate = original_heal_rate

    @pytest.mark.p0
    def test_zero_gain_when_at_max(self):
        """No regen when already at max HP/mana/move.

        ROM C: if (ch->hit < ch->max_hit) ch->hit += hit_gain(ch);
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 1000
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        gain = hit_gain(player)

        assert gain == 0

    @pytest.mark.p0
    def test_no_regeneration_when_no_room(self):
        """Characters not in a room gain nothing.

        ROM C: if (ch->in_room == NULL) return 0;
        """
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.level = 20
        player.pcdata = PCData()
        player.perm_stat = [13, 13, 13, 13, 13]
        player.mod_stat = [0, 0, 0, 0, 0]
        player.hit = 0
        player.max_hit = 1000
        player.position = int(Position.SLEEPING)
        set_conditions(player, hunger=48, thirst=48)

        # Remove from room
        player.room = None

        gain = hit_gain(player)

        assert gain == 0
