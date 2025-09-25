from mud.loaders.area_loader import load_area_file
from mud.loaders.specials_loader import apply_specials_from_json
from mud.registry import area_registry, mob_registry, room_registry
from mud.scripts.convert_are_to_json import convert_area


def setup_function(_):
    mob_registry.clear()
    area_registry.clear()
    room_registry.clear()


def test_convert_are_includes_specials_section():
    data = convert_area("area/haon.are")
    specs = {(s["mob_vnum"], s["spec"].lower()) for s in data.get("specials", [])}
    # Known from existing loader test: mob 6112 uses spec_breath_gas
    assert (6112, "spec_breath_gas") in specs


def test_apply_specials_from_json_overlays_spec_fun_on_prototypes():
    # Load prototypes (without relying on #SPECIALS outcome)
    load_area_file("area/haon.are")
    proto = mob_registry.get(6112)
    assert proto is not None
    # Clear then re-apply from JSON list
    proto.spec_fun = None
    entries = [{"mob_vnum": 6112, "spec": "spec_breath_gas"}]
    apply_specials_from_json(entries)
    assert (proto.spec_fun or "").lower() == "spec_breath_gas"
