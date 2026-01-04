"""Integration tests for weather and time systems.

Tests ROM 2.4b6 parity for:
- Weather transitions (clear → cloudy → rain → lightning)
- Weather broadcasts to outdoor characters
- Time advancement (hour → day → month → year)
- Day/night cycle broadcasts
- Player visibility of weather/time changes

ROM C References:
- src/update.c:weather_update() - Weather pressure and sky transitions
- src/update.c:522-654 - Time advancement and sunlight changes
- Lines 643-651: Weather broadcasts only to IS_OUTSIDE + IS_AWAKE characters
"""

from __future__ import annotations

import pytest

from mud.game_loop import SkyState, game_tick, time_tick, weather, weather_tick
from mud.models.character import Character
from mud.models.constants import Position, RoomFlag
from mud.models.room import Room
from mud.time import Sunlight, time_info


@pytest.fixture(autouse=True)
def reset_weather_time():
    """Reset weather and time to known state before each test."""
    # Reset weather
    weather.sky = SkyState.CLOUDLESS
    weather.mmhg = 1000
    weather.change = 0

    # Reset time
    time_info.hour = 0
    time_info.day = 0
    time_info.month = 0
    time_info.year = 0
    time_info.sunlight = Sunlight.DARK

    yield

    # Clean up after test
    weather.sky = SkyState.CLOUDLESS
    weather.mmhg = 1000
    weather.change = 0
    time_info.hour = 0


# ============================================================================
# Weather System Tests - ROM parity with src/update.c:weather_update()
# ============================================================================


class TestWeatherBroadcasts:
    """Test weather messages are broadcast to outdoor characters only."""

    def test_outdoor_character_sees_weather_changes(self):
        """ROM parity: src/update.c:647 - IS_OUTSIDE check for weather broadcasts."""
        # Create outdoor room (no INDOORS flag)
        outdoor_room = Room(
            vnum=1000,
            name="Forest",
            description="You are in a forest.",
            room_flags=0,  # No INDOORS flag = outdoor
        )

        # Create character in outdoor room
        char = Character(
            name="Tester",
            short_descr="a tester",
            long_descr="A tester is standing here.",
            level=10,
            room=outdoor_room,
            is_npc=False,
            position=Position.STANDING,
        )
        outdoor_room.people.append(char)

        # Verify character is_awake and _is_outside work
        assert char.is_awake(), "Standing character should be awake"

        from mud.game_loop import _is_outside, _should_receive_weather

        assert _is_outside(char), "Character in outdoor room should be outside"
        assert _should_receive_weather(char), "Awake outdoor character should receive weather"

        weather.mmhg = 975
        weather.change = 0
        weather.sky = SkyState.CLOUDLESS

        weather_tick()

        assert weather.sky == SkyState.CLOUDY, f"Sky should transition to cloudy (pressure={weather.mmhg})"

    def test_indoor_character_does_not_see_weather(self):
        """ROM parity: src/update.c:647 - Indoor characters don't see weather."""
        # Create indoor room (INDOORS flag set)
        indoor_room = Room(
            vnum=1001,
            name="Inn",
            description="You are inside an inn.",
            room_flags=int(RoomFlag.ROOM_INDOORS),  # INDOORS flag = indoor
        )

        # Create character in indoor room
        char = Character(
            name="IndoorTester",
            short_descr="an indoor tester",
            long_descr="An indoor tester is here.",
            level=10,
            room=indoor_room,
            is_npc=False,
            position=Position.STANDING,
        )
        indoor_room.people.append(char)

        # Force weather change
        weather.mmhg = 985
        weather.sky = SkyState.CLOUDLESS

        messages_seen = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather" and should_send and should_send(char):
                messages_seen.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            weather_tick()

            # Indoor character should NOT see weather
            assert len(messages_seen) == 0, "Indoor character should not see weather changes"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_sleeping_character_does_not_see_weather(self):
        """ROM parity: src/update.c:648 - IS_AWAKE check for weather broadcasts."""
        outdoor_room = Room(
            vnum=1002,
            name="Field",
            description="An open field.",
            room_flags=0,  # Outdoor
        )

        sleeping_char = Character(
            name="Sleeper",
            short_descr="a sleeping person",
            long_descr="Someone is sleeping here.",
            level=10,
            room=outdoor_room,
            is_npc=False,
            position=Position.SLEEPING,  # Not awake
        )
        outdoor_room.people.append(sleeping_char)

        weather.mmhg = 985
        weather.sky = SkyState.CLOUDLESS

        messages_seen = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather" and should_send and should_send(sleeping_char):
                messages_seen.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            weather_tick()

            # Sleeping character should NOT see weather
            assert len(messages_seen) == 0, "Sleeping character should not see weather changes"
        finally:
            mud.game_loop.broadcast_global = original_broadcast


class TestWeatherTransitions:
    """Test ROM weather state transitions match ROM C formulas."""

    def test_cloudless_to_cloudy_transition(self):
        """ROM parity: src/update.c:593-600 - Cloudless → cloudy when pressure < 990.

        NOTE: ROM updates pressure FIRST (line 582), THEN checks sky (line 594).
        Pressure change is random (±12 max), so we must set it very low to guarantee
        it stays below 990 after the random change.
        """
        weather.sky = SkyState.CLOUDLESS
        weather.mmhg = 975  # Low enough that even +12 change keeps it < 990
        weather.change = 0  # Reset change to minimize randomness

        # Mock broadcast to capture message
        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            weather_tick()

            # After pressure update, should still be < 990, triggering deterministic transition
            assert weather.sky == SkyState.CLOUDY, (
                f"Sky should transition to cloudy (pressure after tick: {weather.mmhg})"
            )
            assert any("cloudy" in msg.lower() for msg in messages), "Should broadcast 'The sky is getting cloudy'"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_cloudy_to_raining_transition(self):
        """ROM parity: src/update.c:603-608 - Cloudy → raining when pressure < 970."""
        weather.sky = SkyState.CLOUDY
        weather.mmhg = 960
        weather.change = 0

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            weather_tick()

            assert weather.sky == SkyState.RAINING, f"Sky should transition to raining (pressure={weather.mmhg})"
            assert any("rain" in msg.lower() for msg in messages), "Should broadcast 'It starts to rain'"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_raining_to_lightning_transition(self):
        """ROM parity: src/update.c:618 - Raining → lightning when pressure < 970 AND number_bits(2)==0."""
        success = False
        for attempt in range(50):
            weather.sky = SkyState.RAINING
            weather.mmhg = 960
            weather.change = 0

            weather_tick()

            if weather.sky == SkyState.LIGHTNING:
                success = True
                break

        assert success, (
            f"Sky should transition to lightning within 50 attempts (25% RNG chance per tick, pressure={weather.mmhg})"
        )

    def test_lightning_to_raining_transition(self):
        """ROM parity: src/update.c:632-639 - Lightning → raining when pressure > 1010."""
        weather.sky = SkyState.LIGHTNING
        weather.mmhg = 1015  # Above 1010 threshold

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            weather_tick()

            assert weather.sky == SkyState.RAINING, "Sky should transition back to raining"
            assert any("lightning" in msg.lower() and "stopped" in msg.lower() for msg in messages), (
                "Should broadcast 'The lightning has stopped'"
            )
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_raining_to_cloudy_transition(self):
        """ROM parity: src/update.c:624-629 - Raining → cloudy when pressure > 1030 OR (> 1010 AND RNG)."""
        success = False
        for attempt in range(50):
            weather.sky = SkyState.RAINING
            weather.mmhg = 1015
            weather.change = 0

            weather_tick()

            if weather.sky == SkyState.CLOUDY:
                success = True
                break

        assert success, (
            f"Sky should clear to cloudy within 50 attempts (RNG threshold or deterministic, pressure={weather.mmhg})"
        )

    def test_cloudy_to_cloudless_transition(self):
        """ROM parity: src/update.c:610-614 - Cloudy → cloudless when pressure > 1030 AND number_bits(2)==0."""
        success = False
        for attempt in range(50):
            weather.sky = SkyState.CLOUDY
            weather.mmhg = 1040
            weather.change = 0

            weather_tick()

            if weather.sky == SkyState.CLOUDLESS:
                success = True
                break

        assert success, (
            f"Sky should clear to cloudless within 50 attempts (25% RNG chance per tick, pressure={weather.mmhg})"
        )

    def test_pressure_change_calculation(self):
        """ROM parity: src/update.c:573-584 - Pressure change formula."""
        # Test winter months (9-16): diff = -2 if mmhg > 985 else 2
        time_info.month = 10  # Winter
        weather.mmhg = 990
        weather.change = 0

        initial_mmhg = weather.mmhg
        weather_tick()

        # Pressure should change (exact value depends on RNG)
        assert weather.mmhg != initial_mmhg, "Pressure should change"
        assert 960 <= weather.mmhg <= 1040, "Pressure should stay within bounds"

        # Test summer months (0-8, 17+): diff = -2 if mmhg > 1015 else 2
        time_info.month = 5  # Summer
        weather.mmhg = 1020
        weather.change = 0

        initial_mmhg = weather.mmhg
        weather_tick()

        assert weather.mmhg != initial_mmhg, "Pressure should change"
        assert 960 <= weather.mmhg <= 1040, "Pressure should stay within bounds"


# ============================================================================
# Time System Tests - ROM parity with src/update.c:522-556
# ============================================================================


class TestTimeAdvancement:
    """Test time advancement and day/night cycle."""

    def test_hour_advancement(self):
        """ROM parity: src/update.c:530 - Hour increments each time_tick()."""
        time_info.hour = 10

        time_tick()

        assert time_info.hour == 11, "Hour should advance by 1"

    def test_day_advancement_at_midnight(self):
        """ROM parity: src/update.c:552-555 - Day advances at hour 24 → 0."""
        time_info.hour = 23
        time_info.day = 5

        time_tick()

        assert time_info.hour == 0, "Hour should wrap to 0 at midnight"
        assert time_info.day == 6, "Day should advance at midnight"

    def test_month_advancement(self):
        """ROM parity: src/update.c:558-562 - Month advances at day 35."""
        time_info.day = 34
        time_info.month = 3
        time_info.hour = 23

        time_tick()  # Advances to day 35, hour 0

        assert time_info.day == 0, "Day should wrap to 0 at month end"
        assert time_info.month == 4, "Month should advance"

    def test_year_advancement(self):
        """ROM parity: src/update.c:564-567 - Year advances at month 17."""
        time_info.month = 16
        time_info.day = 34
        time_info.year = 100
        time_info.hour = 23

        time_tick()  # Advances to month 17, day 0

        assert time_info.month == 0, "Month should wrap to 0 at year end"
        assert time_info.year == 101, "Year should advance"


class TestDayNightCycle:
    """Test sunlight transitions and broadcasts."""

    def test_dawn_broadcast(self):
        """ROM parity: src/update.c:532-535 - Hour 5: 'The day has begun'."""
        time_info.hour = 4

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            time_tick()

            assert time_info.hour == 5
            assert time_info.sunlight == Sunlight.LIGHT, "Sunlight should be LIGHT at dawn"
            assert any("day has begun" in msg.lower() for msg in messages), "Should broadcast 'The day has begun'"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_sunrise_broadcast(self):
        """ROM parity: src/update.c:537-540 - Hour 6: 'The sun rises'."""
        time_info.hour = 5

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            time_tick()

            assert time_info.hour == 6
            assert time_info.sunlight == Sunlight.RISE, "Sunlight should be RISE"
            assert any("sun rises" in msg.lower() for msg in messages), "Should broadcast 'The sun rises in the east'"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_sunset_broadcast(self):
        """ROM parity: src/update.c:542-545 - Hour 19: 'The sun slowly disappears'."""
        time_info.hour = 18

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            time_tick()

            assert time_info.hour == 19
            assert time_info.sunlight == Sunlight.SET, "Sunlight should be SET"
            assert any("sun" in msg.lower() and "disappear" in msg.lower() for msg in messages), (
                "Should broadcast 'The sun slowly disappears in the west'"
            )
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_nightfall_broadcast(self):
        """ROM parity: src/update.c:547-550 - Hour 20: 'The night has begun'."""
        time_info.hour = 19

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            time_tick()

            assert time_info.hour == 20
            assert time_info.sunlight == Sunlight.DARK, "Sunlight should be DARK"
            assert any("night has begun" in msg.lower() for msg in messages), "Should broadcast 'The night has begun'"
        finally:
            mud.game_loop.broadcast_global = original_broadcast

    def test_no_broadcast_for_normal_hours(self):
        """ROM parity: Most hours don't trigger broadcasts."""
        time_info.hour = 10  # Mid-day, no special event

        messages = []

        def mock_broadcast(msg, channel=None, should_send=None):
            if channel == "weather":
                messages.append(msg)

        import mud.game_loop

        original_broadcast = mud.game_loop.broadcast_global
        mud.game_loop.broadcast_global = mock_broadcast

        try:
            time_tick()

            assert time_info.hour == 11
            assert len(messages) == 0, "No broadcast for normal hour advancement"
        finally:
            mud.game_loop.broadcast_global = original_broadcast
