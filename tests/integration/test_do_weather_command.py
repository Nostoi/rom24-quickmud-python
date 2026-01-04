"""
Integration tests for do_weather command.

Tests ROM C parity for weather display command.

ROM Reference: src/act_info.c lines 1806-1830
"""

from __future__ import annotations

import pytest

from mud.commands.info import do_weather
from mud.game_loop import weather, SkyState
from mud.models.character import Character
from mud.models.constants import RoomFlag, Sector
from mud.models.room import Room


@pytest.fixture
def outdoor_room():
    """Create an outdoor room for weather testing."""
    room = Room(vnum=3001)
    room.name = "Outdoor Location"
    room.description = "You are standing outdoors."
    room.sector_type = int(Sector.FIELD)
    room.room_flags = 0
    room.light = 1
    return room


@pytest.fixture
def indoor_room():
    """Create an indoor room for weather testing."""
    room = Room(vnum=3002)
    room.name = "Indoor Location"
    room.description = "You are standing indoors."
    room.sector_type = int(Sector.INSIDE)
    room.room_flags = int(RoomFlag.ROOM_INDOORS)
    room.light = 1
    return room


@pytest.fixture
def test_character():
    """Create a test character for weather testing."""
    char = Character()
    char.name = "WeatherTester"
    char.level = 1
    char.trust = 0
    char.is_npc = False
    return char


class TestDoWeatherIntegration:
    """Integration tests for do_weather command."""

    def test_basic_weather_display_outdoors(self, test_character, outdoor_room):
        """Test basic weather display when outdoors."""
        test_character.room = outdoor_room

        result = do_weather(test_character, "")

        assert result
        assert len(result) > 0
        assert "sky" in result.lower() or "rain" in result.lower() or "cloud" in result.lower()

    def test_weather_indoors_blocked(self, test_character, indoor_room):
        """Test that weather cannot be seen indoors."""
        test_character.room = indoor_room

        result = do_weather(test_character, "")

        assert "indoors" in result.lower() or "can't see" in result.lower()

    def test_sky_state_cloudless(self, test_character, outdoor_room):
        """Test cloudless sky description."""
        test_character.room = outdoor_room

        weather.sky = SkyState.CLOUDLESS
        result = do_weather(test_character, "")

        assert "cloudless" in result.lower()

    def test_sky_state_cloudy(self, test_character, outdoor_room):
        """Test cloudy sky description."""
        test_character.room = outdoor_room

        weather.sky = SkyState.CLOUDY
        result = do_weather(test_character, "")

        assert "cloudy" in result.lower()

    def test_sky_state_raining(self, test_character, outdoor_room):
        """Test rainy sky description."""
        test_character.room = outdoor_room

        weather.sky = SkyState.RAINING
        result = do_weather(test_character, "")

        assert "rain" in result.lower()

    def test_sky_state_lightning(self, test_character, outdoor_room):
        """Test lightning sky description."""
        test_character.room = outdoor_room

        weather.sky = SkyState.LIGHTNING
        result = do_weather(test_character, "")

        assert "lightning" in result.lower() or "flash" in result.lower()

    def test_wind_direction_warm_south(self, test_character, outdoor_room):
        """Test warm southerly breeze (positive weather change)."""
        test_character.room = outdoor_room

        weather.sky = SkyState.CLOUDLESS
        weather.change = 5

        result = do_weather(test_character, "")

        assert "warm" in result.lower() and ("south" in result.lower() or "breeze" in result.lower())

    def test_wind_direction_cold_north(self, test_character, outdoor_room):
        """Test cold northern gust (negative weather change)."""
        test_character.room = outdoor_room

        weather.sky = SkyState.CLOUDLESS
        weather.change = -5

        result = do_weather(test_character, "")

        assert "cold" in result.lower() and ("north" in result.lower() or "gust" in result.lower())

    def test_wind_direction_boundary_zero(self, test_character, outdoor_room):
        """Test wind direction at boundary (change = 0)."""
        test_character.room = outdoor_room

        weather.sky = SkyState.CLOUDLESS
        weather.change = 0

        result = do_weather(test_character, "")

        assert "warm" in result.lower() and ("south" in result.lower() or "breeze" in result.lower())

    def test_no_room_error(self):
        """Test error handling when character has no room."""
        char = Character()
        char.name = "NoRoom"

        result = do_weather(char, "")

        assert result
        assert "nowhere" in result.lower() or "can't see" in result.lower()
