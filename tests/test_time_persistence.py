import mud.persistence as persistence
from mud.time import Sunlight, time_info


def test_time_info_persist_roundtrip(tmp_path):
    # Point time file to temp location
    persistence.TIME_FILE = tmp_path / "time.json"

    # Set a distinctive time state
    time_info.hour = 23
    time_info.day = 34
    time_info.month = 16
    time_info.year = 7
    time_info.sunlight = Sunlight.DARK

    persistence.save_time_info()

    # Clear values and reload
    time_info.hour = 0
    time_info.day = 0
    time_info.month = 0
    time_info.year = 0
    time_info.sunlight = Sunlight.LIGHT

    persistence.load_time_info()

    assert time_info.hour == 23
    assert time_info.day == 34
    assert time_info.month == 16
    assert time_info.year == 7
    assert time_info.sunlight == Sunlight.DARK
