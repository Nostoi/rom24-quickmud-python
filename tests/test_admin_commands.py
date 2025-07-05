from mud.world import initialize_world, create_test_character
from mud.commands import process_command
from mud.net.session import Session, SESSIONS


def setup_module(module):
    initialize_world('area/area.lst')


def teardown_function(function):
    SESSIONS.clear()


def test_admin_commands_permissions():
    admin = create_test_character('Admin', 3001)
    admin.is_admin = True
    sess_admin = Session(name='Admin', character=admin, reader=None, writer=None)
    SESSIONS['Admin'] = sess_admin

    player = create_test_character('Bob', 3001)
    sess_player = Session(name='Bob', character=player, reader=None, writer=None)
    SESSIONS['Bob'] = sess_player

    out_admin = process_command(admin, '@who')
    assert 'Admin' in out_admin and 'Bob' in out_admin

    out_player = process_command(player, '@who')
    assert 'permission' in out_player.lower()

    out_tp = process_command(admin, '@teleport 3005')
    assert 'Teleported' in out_tp
    assert admin.room.vnum == 3005

    out_spawn = process_command(admin, '@spawn 3000')
    assert 'Spawned' in out_spawn
    assert any(mob.prototype.vnum == 3000 for mob in admin.room.people if hasattr(mob, 'prototype'))
