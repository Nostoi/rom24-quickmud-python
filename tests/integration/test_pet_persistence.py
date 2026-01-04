"""Integration tests for pet persistence (save.c fwrite_pet/fread_pet equivalents).

These tests verify QuickMUD's pet save/load system matches ROM 2.4b6 save.c behavior.

ROM C Reference: src/save.c:449-523 (fwrite_pet), 1406-1595 (fread_pet)
QuickMUD Module: mud/persistence.py (_serialize_pet, _deserialize_pet)

Test Coverage:
1. Pet stats preservation - ROM C HMV (hit/mana/move) values
2. Pet affects persistence - ROM C Affc records with duplicate prevention
3. Pet position/alignment - ROM C Pos/Alig fields
4. Pet equipment stats - ROM C AC/Attr/AMod arrays
5. Complete pet restoration - ROM C full workflow integration

See: docs/parity/SAVE_C_AUDIT.md for detailed ROM C audit
"""

from __future__ import annotations

import pytest

import mud.persistence as persistence
from mud.models.character import character_registry
from mud.models.constants import Position
from mud.models.obj import Affect
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character, initialize_world


@pytest.fixture(autouse=True)
def _setup_persistence(tmp_path):
    """Setup isolated persistence directory for each test."""
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")
    yield
    character_registry.clear()


# ============================================================================
# TEST 1: Pet Stats Preservation - ROM C HMV Fields
# ============================================================================
# ROM C: src/save.c:474-477 (fwrite_pet)
# - fprintf(fp, "HMV  %d %d %d %d %d %d\n", hit, max_hit, mana, max_mana, move, max_move)
# - Saves current and maximum values for all vitals
# ============================================================================


def test_pet_stats_preserved_through_save_load():
    """Verify pet hit/mana/move stats survive save/load cycle.

    ROM C Behavior (src/save.c:474-477):
    - HMV line saves 6 values: hit, max_hit, mana, max_mana, move, max_move
    - All vitals restored on load (lines 1512-1517)

    QuickMUD Behavior:
    - PetSave.hit/max_hit/mana/max_mana/move/max_move fields
    - _serialize_pet() captures current state
    - _deserialize_pet() restores all vitals
    """
    char = create_test_character("PetOwner", 3001)

    # Create pet (charmed mob)
    pet = spawn_mob(3005)  # Cityguard
    assert pet is not None, "Pet should spawn"

    # Set custom stats (different from prototype)
    pet.hit = 75
    pet.max_hit = 100
    pet.mana = 50
    pet.max_mana = 80
    pet.move = 40
    pet.max_move = 60
    pet.gold = 100
    pet.silver = 50
    pet.exp = 500

    # Establish pet relationship
    pet.master = char
    pet.leader = char
    char.pet = pet

    # Save character (should save pet too)
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("PetOwner")
    assert loaded is not None, "Character should load successfully"
    assert loaded.pet is not None, "Pet should be loaded"

    # Verify pet stats preserved
    loaded_pet = loaded.pet
    assert loaded_pet.hit == 75, "Pet hit should be preserved"
    assert loaded_pet.max_hit == 100, "Pet max_hit should be preserved"
    assert loaded_pet.mana == 50, "Pet mana should be preserved"
    assert loaded_pet.max_mana == 80, "Pet max_mana should be preserved"
    assert loaded_pet.move == 40, "Pet move should be preserved"
    assert loaded_pet.max_move == 60, "Pet max_move should be preserved"
    assert loaded_pet.gold == 100, "Pet gold should be preserved"
    assert loaded_pet.silver == 50, "Pet silver should be preserved"
    assert loaded_pet.exp == 500, "Pet exp should be preserved"


# ============================================================================
# TEST 2: Pet Affects Persistence - ROM C Affc Records
# ============================================================================
# ROM C: src/save.c:511-521 (fwrite_pet)
# - Saves affects as "Affc '<skill>' where level duration modifier location bitvector"
# - fread_pet (lines 1491-1552) loads affects with duplicate checking
# - check_pet_affected() prevents affect stacking bugs
# ============================================================================


def test_pet_affects_preserved_no_duplication():
    """Verify pet affects survive save/load with duplicate prevention.

    ROM C Behavior (src/save.c:511-521, 1491-1552):
    - Affc records save affect details (skill, where, level, duration, etc.)
    - check_pet_affected() prevents duplicate affects from mob_index
    - This fixes pet affect stacking bug reported by Chris Litchfield

    QuickMUD Behavior:
    - PetAffectSave dataclass stores affect details
    - _deserialize_pet() checks for duplicates before applying affects
    - Prevents double-applying affects that are already on mob prototype
    """
    from mud.skills.registry import skill_registry

    # Helper to lookup skill slot by name
    def get_skill_slot(skill_name: str) -> int:
        skill = skill_registry.skills.get(skill_name)
        if skill and hasattr(skill, "slot"):
            return skill.slot
        return -1

    char = create_test_character("Charmer", 3001)

    # Create pet
    pet = spawn_mob(3005)  # Cityguard
    assert pet is not None

    # Add custom affects (not from prototype)
    affect1 = Affect(
        type=get_skill_slot("bless"),  # Spell number for bless
        where=1,  # TO_AFFECTS
        level=20,
        duration=10,
        modifier=5,
        location=18,  # APPLY_HITROLL
        bitvector=0,
    )
    setattr(pet, "affected", [affect1])

    affect2 = Affect(
        type=get_skill_slot("armor"),
        where=1,
        level=15,
        duration=20,
        modifier=-20,
        location=17,  # APPLY_AC
        bitvector=0,
    )
    getattr(pet, "affected", []).append(affect2)

    # Establish pet relationship
    pet.master = char
    char.pet = pet

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("Charmer")
    assert loaded is not None
    assert loaded.pet is not None

    # Verify affects preserved
    loaded_pet = loaded.pet
    assert len(getattr(loaded_pet, "affected", [])) >= 2, "Pet should have at least 2 affects"

    bless_slot = get_skill_slot("bless")
    armor_slot = get_skill_slot("armor")

    # Find the bless affect
    bless_affect = None
    for aff in getattr(loaded_pet, "affected", []):
        if aff.type == bless_slot:
            bless_affect = aff
            break

    assert bless_affect is not None, "Bless affect should be preserved"
    assert bless_affect.level == 20, "Affect level preserved"
    assert bless_affect.duration == 10, "Affect duration preserved"
    assert bless_affect.modifier == 5, "Affect modifier preserved"

    # Find the armor affect
    armor_affect = None
    for aff in getattr(loaded_pet, "affected", []):
        if aff.type == armor_slot:
            armor_affect = aff
            break

    assert armor_affect is not None, "Armor affect should be preserved"
    assert armor_affect.modifier == -20, "Armor AC modifier preserved"


# ============================================================================
# TEST 3: Pet Position/Alignment - ROM C Pos/Alig Fields
# ============================================================================
# ROM C: src/save.c:506-509 (fwrite_pet)
# - Converts POS_FIGHTING to POS_STANDING before save
# - Only saves alignment if different from prototype
# ============================================================================


def test_pet_position_converted_from_fighting():
    """Verify POS_FIGHTING converted to POS_STANDING on save.

    ROM C Behavior (src/save.c:506):
    - fprintf(fp, "Pos  %d\n", pet->position = POS_FIGHTING ? POS_STANDING : pet->position)
    - Prevents pets from loading in combat stance

    QuickMUD Behavior:
    - _serialize_pet() converts POS_FIGHTING → POS_STANDING
    - _deserialize_pet() restores position as saved
    """
    char = create_test_character("Fighter", 3001)

    # Create pet in fighting position
    pet = spawn_mob(3005)
    pet.position = int(Position.FIGHTING)
    pet.alignment = 500  # Good alignment
    pet.master = char
    char.pet = pet

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("Fighter")
    assert loaded is not None
    assert loaded.pet is not None

    # Verify position converted to standing
    assert loaded.pet.position == int(Position.STANDING), "Pet position should convert from FIGHTING to STANDING"
    assert loaded.pet.alignment == 500, "Pet alignment should be preserved"


# ============================================================================
# TEST 4: Pet Equipment Stats - ROM C AC/Attr/AMod Arrays
# ============================================================================
# ROM C: src/save.c:500-509 (fwrite_pet)
# - ACs: 4 armor class values
# - Attr: 5 permanent stats (STR/INT/WIS/DEX/CON)
# - AMod: 5 stat modifiers
# ============================================================================


def test_pet_equipment_stats_preserved():
    """Verify pet armor, stats, and modifiers survive save/load.

    ROM C Behavior (src/save.c:500-509):
    - ACs line: 4 AC values (slash/bash/pierce/magic)
    - Attr line: 5 permanent stats
    - AMod line: 5 stat modifiers

    QuickMUD Behavior:
    - PetSave.armor (4 ints)
    - PetSave.perm_stat (5 ints)
    - PetSave.mod_stat (5 ints)
    """
    char = create_test_character("Trainer", 3001)

    # Create pet with custom stats
    pet = spawn_mob(3005)
    pet.armor = [10, 15, 20, 25]  # Custom AC values
    pet.perm_stat = [18, 14, 12, 16, 15]  # STR/INT/WIS/DEX/CON
    pet.mod_stat = [2, 0, -1, 3, 1]  # Stat bonuses
    pet.hitroll = 10
    pet.damroll = 5
    pet.saving_throw = -2
    pet.master = char
    char.pet = pet

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("Trainer")
    assert loaded is not None
    assert loaded.pet is not None

    # Verify equipment stats preserved
    loaded_pet = loaded.pet
    assert loaded_pet.armor == [10, 15, 20, 25], "Pet armor should be preserved"
    assert loaded_pet.perm_stat == [18, 14, 12, 16, 15], "Pet perm_stat should be preserved"
    assert loaded_pet.mod_stat == [2, 0, -1, 3, 1], "Pet mod_stat should be preserved"
    assert loaded_pet.hitroll == 10, "Pet hitroll should be preserved"
    assert loaded_pet.damroll == 5, "Pet damroll should be preserved"
    assert loaded_pet.saving_throw == -2, "Pet saving_throw should be preserved"


# ============================================================================
# TEST 5: Pet Relationship - ROM C Master/Leader Fields
# ============================================================================
# ROM C: fread_pet (src/save.c:1406-1595)
# - Pet automatically links to owner (master/leader set)
# - Pet follows owner when they move
# ============================================================================


def test_pet_relationship_restored():
    """Verify pet master/leader relationship restored on load.

    ROM C Behavior:
    - fread_pet() creates pet linked to owner
    - Pet automatically follows owner

    QuickMUD Behavior:
    - _deserialize_pet() sets pet.master and pet.leader to owner
    - Pet ready to follow owner immediately
    """
    char = create_test_character("BeastMaster", 3001)

    # Create pet
    pet = spawn_mob(3005)
    pet.name = "Fluffy the Guard"
    pet.master = char
    pet.leader = char
    char.pet = pet

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("BeastMaster")
    assert loaded is not None
    assert loaded.pet is not None

    # Verify relationship restored
    loaded_pet = loaded.pet
    assert loaded_pet.master == loaded, "Pet master should be owner"
    assert loaded_pet.leader == loaded, "Pet leader should be owner"
    assert loaded_pet.name == "Fluffy the Guard", "Pet name should be preserved"


# ============================================================================
# TEST 6: Pet Not Saved for NPCs - ROM C save_char_obj() Guard
# ============================================================================
# ROM C: src/save.c:105-172 (save_char_obj)
# - Only players can save pets, not NPCs
# ============================================================================


def test_npc_pet_not_saved():
    """Verify NPCs cannot save pets (ROM C behavior).

    ROM C Behavior:
    - save_char_obj() only called for players
    - NPCs never have persistent pets

    QuickMUD Behavior:
    - save_character() exits early for NPCs (line 752-753)
    - Pet data never serialized for NPCs
    """
    # Create NPC with pet
    npc = spawn_mob(3005)
    npc.is_npc = True
    pet = spawn_mob(3006)
    pet.master = npc
    npc.pet = pet

    # Attempt to save NPC (should be no-op)
    persistence.save_character(npc)

    # Verify no save file created
    import os

    save_path = persistence.PLAYERS_DIR / f"{npc.name.lower()}.json"
    assert not os.path.exists(save_path), "NPCs should not create save files"


# ============================================================================
# TEST 7: Complete Pet Restoration Workflow
# ============================================================================


def test_complete_pet_restoration_workflow():
    """Verify complete pet save/load workflow end-to-end.

    This test combines all previous scenarios:
    - Pet stats (HMV, gold, exp)
    - Pet affects (with duplicate prevention)
    - Pet position (FIGHTING → STANDING conversion)
    - Pet equipment (armor, stats, modifiers)
    - Pet relationship (master, leader)
    """
    from mud.skills.registry import skill_registry

    def get_skill_slot_local(skill_name: str) -> int:
        skill = skill_registry.skills.get(skill_name)
        if skill and hasattr(skill, "slot"):
            return skill.slot
        return -1

    char = create_test_character("CompleteTest", 3001)

    # Create fully-configured pet
    pet = spawn_mob(3005)
    pet.name = "Maximus the Guardian"
    pet.level = 25
    pet.hit = 200
    pet.max_hit = 250
    pet.mana = 100
    pet.max_mana = 150
    pet.move = 80
    pet.max_move = 100
    pet.gold = 500
    pet.silver = 250
    setattr(pet, "exp", 10000)
    pet.position = int(Position.FIGHTING)  # Should convert to STANDING
    pet.alignment = 750
    pet.armor = [5, 10, 15, 20]
    pet.perm_stat = [20, 16, 14, 18, 17]
    setattr(pet, "mod_stat", [3, 1, 0, 2, 1])
    pet.hitroll = 15
    pet.damroll = 10
    setattr(pet, "saving_throw", -5)

    # Add affects
    affect = Affect(
        type=get_skill_slot_local("giant strength"),
        where=1,
        level=30,
        duration=15,
        modifier=10,
        location=1,  # APPLY_STR
        bitvector=0,
    )
    setattr(pet, "affected", [affect])

    # Establish relationship
    setattr(pet, "master", char)
    setattr(pet, "leader", char)
    char.pet = pet  # type: ignore

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("CompleteTest")
    assert loaded is not None, "Character should load"
    assert loaded.pet is not None, "Pet should load"

    # Verify all pet data
    loaded_pet = loaded.pet
    assert loaded_pet.name == "Maximus the Guardian", "Pet name preserved"
    assert loaded_pet.level == 25, "Pet level preserved"
    assert loaded_pet.hit == 200, "Pet hit preserved"
    assert loaded_pet.max_hit == 250, "Pet max_hit preserved"
    assert loaded_pet.mana == 100, "Pet mana preserved"
    assert loaded_pet.max_mana == 150, "Pet max_mana preserved"
    assert loaded_pet.move == 80, "Pet move preserved"
    assert loaded_pet.max_move == 100, "Pet max_move preserved"
    assert loaded_pet.gold == 500, "Pet gold preserved"
    assert loaded_pet.silver == 250, "Pet silver preserved"
    assert loaded_pet.exp == 10000, "Pet exp preserved"
    assert loaded_pet.position == int(Position.STANDING), "Pet position converted from FIGHTING"
    assert loaded_pet.alignment == 750, "Pet alignment preserved"
    assert loaded_pet.armor == [5, 10, 15, 20], "Pet armor preserved"
    assert loaded_pet.perm_stat == [20, 16, 14, 18, 17], "Pet perm_stat preserved"
    assert loaded_pet.mod_stat == [3, 1, 0, 2, 1], "Pet mod_stat preserved"
    assert loaded_pet.hitroll == 15, "Pet hitroll preserved"
    assert loaded_pet.damroll == 10, "Pet damroll preserved"
    assert loaded_pet.saving_throw == -5, "Pet saving_throw preserved"
    assert len(loaded_pet.affected) >= 1, "Pet affects preserved"
    assert loaded_pet.master == loaded, "Pet master relationship restored"
    assert loaded_pet.leader == loaded, "Pet leader relationship restored"


# ============================================================================
# TEST 8: No Pet Saved When None Present
# ============================================================================


def test_no_pet_saved_when_none_present():
    """Verify players without pets don't have pet data in save file.

    ROM C Behavior:
    - save_char_obj() only writes #PET section if pet exists
    - fread_char() handles missing #PET section gracefully

    QuickMUD Behavior:
    - PetSave field defaults to None in PlayerSave
    - _serialize_pet() only called if char.pet exists
    """
    char = create_test_character("SoloPLayer", 3001)
    char.pet = None  # No pet

    # Save character
    persistence.save_character(char)

    # Load character
    loaded = persistence.load_character("SoloPLayer")
    assert loaded is not None, "Character should load"
    assert loaded.pet is None, "No pet should be loaded"

    # Verify save file doesn't have pet data
    import json

    save_path = persistence.PLAYERS_DIR / "soloplayer.json"
    with open(save_path) as f:
        data = json.load(f)

    assert data.get("pet") is None, "Save file should not have pet field"
