from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.mob_spawner import spawn_mob


def setup_module(module):
    initialize_world('area/area.lst')


def test_setroom_obj_mob():
    admin = create_test_character('Admin', 3001)
    admin.is_admin = True
    # Room name and description
    out = process_command(admin, '@setroom name "Admin Room"')
    assert "Room name set" in out
    assert admin.room.name == "Admin Room"
    out = process_command(admin, '@setroom desc "A blank room."')
    assert admin.room.description == "A blank room."
    # Object editing
    sword = spawn_object(3022)
    assert sword is not None
    admin.room.add_object(sword)
    out = process_command(admin, '@setobj sword short "shiny sword"')
    assert out == "Object updated."
    assert sword.prototype.short_descr == "shiny sword"
    # Mob editing
    baker = spawn_mob(3001)
    assert baker is not None
    admin.room.add_mob(baker)
    out = process_command(admin, '@setmob baker short "grumpy baker"')
    assert out == "Mob updated."
    assert baker.prototype.short_descr == "grumpy baker"
