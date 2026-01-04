"""
Integration tests for do_time command.

Tests ROM C parity for game time display command.

ROM Reference: src/act_info.c lines 1771-1804
"""

from __future__ import annotations

import pytest

from mud.commands.info import do_time
from mud.models.character import Character
from mud.time import time_info


class TestDoTimeIntegration:
    """Integration tests for do_time command."""

    def test_basic_time_display(self, movable_char_factory):
        """Test basic time display shows hour and day."""
        char = movable_char_factory("Tester", 3001)

        # Set known time
        time_info.hour = 15
        time_info.day = 10
        time_info.month = 5

        result = do_time(char, "")

        # Should contain time and day information
        assert "Day of" in result
        assert "Month of" in result

    def test_ordinal_suffix_1st_through_4th(self, movable_char_factory):
        """Test ordinal suffixes for days 1-4."""
        char = movable_char_factory("Tester", 3001)

        # Test day 1 (1st)
        time_info.day = 0  # ROM days are 0-indexed, display as 1
        result = do_time(char, "")
        assert "1st" in result

        # Test day 2 (2nd)
        time_info.day = 1
        result = do_time(char, "")
        assert "2nd" in result

        # Test day 3 (3rd)
        time_info.day = 2
        result = do_time(char, "")
        assert "3rd" in result

        # Test day 4 (4th)
        time_info.day = 3
        result = do_time(char, "")
        assert "4th" in result

    def test_ordinal_suffix_11th_12th_13th(self, movable_char_factory):
        """Test ordinal suffixes for days 11-13 (special case in ROM C)."""
        char = movable_char_factory("Tester", 3001)

        # Test day 11 (11th, NOT 11st)
        time_info.day = 10  # Display as 11
        result = do_time(char, "")
        assert "11th" in result
        assert "11st" not in result  # Bug check

        # Test day 12 (12th, NOT 12nd)
        time_info.day = 11  # Display as 12
        result = do_time(char, "")
        assert "12th" in result
        assert "12nd" not in result  # Bug check

        # Test day 13 (13th, NOT 13rd)
        time_info.day = 12  # Display as 13
        result = do_time(char, "")
        assert "13th" in result
        assert "13rd" not in result  # Bug check

    def test_ordinal_suffix_21st_22nd_23rd(self, movable_char_factory):
        """Test ordinal suffixes for days 21-23."""
        char = movable_char_factory("Tester", 3001)

        # Test day 21 (21st)
        time_info.day = 20  # Display as 21
        result = do_time(char, "")
        assert "21st" in result

        # Test day 22 (22nd)
        time_info.day = 21  # Display as 22
        result = do_time(char, "")
        assert "22nd" in result

        # Test day 23 (23rd)
        time_info.day = 22  # Display as 23
        result = do_time(char, "")
        assert "23rd" in result

    def test_12_hour_format_midnight(self, movable_char_factory):
        """Test 12-hour format at midnight (hour 0 = 12 am)."""
        char = movable_char_factory("Tester", 3001)

        time_info.hour = 0
        result = do_time(char, "")

        # ROM C: hour % 12 == 0 ? 12 : hour % 12
        # Should show "12" not "0"
        assert "12 o'clock am" in result.lower() or "12 am" in result.lower()

    def test_12_hour_format_noon(self, movable_char_factory):
        """Test 12-hour format at noon (hour 12 = 12 pm)."""
        char = movable_char_factory("Tester", 3001)

        time_info.hour = 12
        result = do_time(char, "")

        # Should show "12 pm"
        assert "12 o'clock pm" in result.lower() or "12 pm" in result.lower()

    def test_12_hour_format_afternoon(self, movable_char_factory):
        """Test 12-hour format in afternoon (hour 13 = 1 pm)."""
        char = movable_char_factory("Tester", 3001)

        time_info.hour = 13
        result = do_time(char, "")

        # Should show "1 pm" (13 - 12 = 1)
        assert "1 o'clock pm" in result.lower() or "1 pm" in result.lower()

    def test_day_name_cycling(self, movable_char_factory):
        """Test day names cycle through 7-day week."""
        char = movable_char_factory("Tester", 3001)

        # ROM C: day_name[(time_info.day + 1) % 7]
        # So time_info.day=0 shows "the Bull", time_info.day=6 shows "the Moon"
        day_names = ["the Moon", "the Bull", "Deception", "Thunder", "Freedom", "the Great Gods", "the Sun"]

        for day_offset in range(7):
            time_info.day = day_offset
            result = do_time(char, "")

            # ROM C: day = time_info.day + 1; day_name[day % 7]
            display_day = day_offset + 1
            expected_day = day_names[display_day % 7]
            assert expected_day in result or expected_day.lower() in result.lower()

    def test_month_name_cycling(self, movable_char_factory):
        """Test month names cycle through 17-month calendar."""
        char = movable_char_factory("Tester", 3001)

        month_names = [
            "Winter",
            "the Winter Wolf",
            "the Frost Giant",
            "the Old Forces",
            "the Grand Struggle",
            "the Spring",
            "Nature",
            "Futility",
            "the Dragon",
            "the Sun",
            "the Heat",
            "the Battle",
            "the Dark Shades",
            "the Shadows",
            "the Long Shadows",
            "the Ancient Darkness",
            "the Great Evil",
        ]

        for month in range(17):
            time_info.month = month
            result = do_time(char, "")

            # Check that the correct month name appears
            expected_month = month_names[month]
            assert expected_month in result

    def test_boot_time_display(self, movable_char_factory):
        """Test that boot time is displayed (ROM C feature)."""
        char = movable_char_factory("Tester", 3001)

        result = do_time(char, "")

        # ROM C shows: "ROM started up at {boot_time}"
        assert "ROM started up at" in result or "started up at" in result.lower()

    def test_system_time_display(self, movable_char_factory):
        """Test that system time is displayed (ROM C feature)."""
        char = movable_char_factory("Tester", 3001)

        result = do_time(char, "")

        # ROM C shows: "The system time is {current_time}"
        assert "system time" in result.lower()

    def test_complete_output_format(self, movable_char_factory):
        """Test that do_time returns all 3 lines: game time, boot time, system time."""
        import re

        char = movable_char_factory("Tester", 3001)
        result = do_time(char, "")

        # Should have 3+ lines (game time + boot time + system time)
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) >= 3, f"Expected 3+ lines, got {len(lines)}: {lines}"

        # Verify game time format
        assert "o'clock" in lines[0].lower()
        assert "day of" in lines[0].lower()

        # Verify boot time format (ROM C ctime format: "Wed Jun 30 21:49:08 1993")
        boot_match = re.search(r"ROM started up at (\w{3} \w{3} +\d+ \d{2}:\d{2}:\d{2} \d{4})", lines[1])
        assert boot_match is not None, f"Boot time format incorrect: {lines[1]}"

        # Verify system time format (ROM C ctime format)
        system_match = re.search(r"The system time is (\w{3} \w{3} +\d+ \d{2}:\d{2}:\d{2} \d{4})", lines[2])
        assert system_match is not None, f"System time format incorrect: {lines[2]}"
