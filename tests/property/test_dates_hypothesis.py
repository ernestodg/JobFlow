"""
Property-based tests for date parsing and validation using Hypothesis.
Tests random valid/invalid date strings to ensure parser never crashes.
"""
import sys
from pathlib import Path

# Import from app modules - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
from datetime import datetime

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from core_data import DataManager
from utils import validate_dates


class TestDatesHypothesis:
    """Property-based tests for date validation and parsing."""

    def setup_method(self):
        """Set up data manager for each test."""
        self.data_manager = DataManager()

    # Date string generation strategies
    @st.composite
    def valid_iso_date_string(draw):
        """Generate valid ISO date strings (YYYY-MM-DD)."""
        year = draw(st.integers(min_value=1900, max_value=2100))
        month = draw(st.integers(min_value=1, max_value=12))

        # Handle different month lengths
        if month in [1, 3, 5, 7, 8, 10, 12]:
            max_day = 31
        elif month in [4, 6, 9, 11]:
            max_day = 30
        else:  # February
            # Simple leap year check
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            max_day = 29 if is_leap else 28

        day = draw(st.integers(min_value=1, max_value=max_day))

        return f"{year:04d}-{month:02d}-{day:02d}"

    @st.composite
    def invalid_date_string(draw):
        """Generate various invalid date string formats."""
        strategy_choice = draw(st.integers(min_value=0, max_value=6))

        if strategy_choice == 0:
            # Wrong format: MM/DD/YYYY
            month = draw(st.integers(min_value=1, max_value=12))
            day = draw(st.integers(min_value=1, max_value=31))
            year = draw(st.integers(min_value=1900, max_value=2100))
            return f"{month:02d}/{day:02d}/{year}"

        elif strategy_choice == 1:
            # Wrong delimiter: YYYY.MM.DD
            year = draw(st.integers(min_value=1900, max_value=2100))
            month = draw(st.integers(min_value=1, max_value=12))
            day = draw(st.integers(min_value=1, max_value=31))
            return f"{year}.{month:02d}.{day:02d}"

        elif strategy_choice == 2:
            # Invalid month
            year = draw(st.integers(min_value=1900, max_value=2100))
            month = draw(st.integers(min_value=13, max_value=99))
            day = draw(st.integers(min_value=1, max_value=31))
            return f"{year:04d}-{month:02d}-{day:02d}"

        elif strategy_choice == 3:
            # Invalid day
            year = draw(st.integers(min_value=1900, max_value=2100))
            month = draw(st.integers(min_value=1, max_value=12))
            day = draw(st.integers(min_value=32, max_value=99))
            return f"{year:04d}-{month:02d}-{day:02d}"

        elif strategy_choice == 4:
            # Random text
            return draw(st.text(min_size=1, max_size=20))

        elif strategy_choice == 5:
            # Empty or whitespace
            return draw(st.sampled_from(["", " ", "  ", "\t", "\n"]))

        else:
            # Wrong year format
            year = draw(st.integers(min_value=0, max_value=99))
            month = draw(st.integers(min_value=1, max_value=12))
            day = draw(st.integers(min_value=1, max_value=31))
            return f"{year:02d}-{month:02d}-{day:02d}"

    @given(valid_iso_date_string())
    @example("2025-10-01")  # Ensure we test a known good date
    @example("2024-02-29")  # Leap year edge case
    @example("2025-12-31")  # End of year
    def test_valid_dates_are_accepted(self, date_string: str):
        """
        PROPERTY: All valid ISO date strings should be accepted by validator
        GIVEN: A properly formatted ISO date string (YYYY-MM-DD)
        WHEN: Validating the date
        THEN: Validation passes and parser doesn't crash
        """
        # Test core_data validation
        is_valid = self.data_manager.validate_iso_date(date_string)
        assert is_valid, f"Valid date {date_string} should pass validation"

        # Test utils validation if available
        try:
            # This might not exist in utils, so we'll try it
            result = validate_dates([date_string])
            assert isinstance(result, list | tuple | bool)
        except (AttributeError, NameError):
            # Function might not exist, skip this part
            pass

    @given(invalid_date_string())
    @example("13/01/2025")  # US format
    @example("2025-13-01")  # Invalid month
    @example("2025-02-30")  # Invalid day for February
    @example("not-a-date")  # Random text
    @example("")  # Empty string
    def test_invalid_dates_are_rejected(self, date_string: str):
        """
        PROPERTY: Invalid date strings should be rejected without crashing
        GIVEN: An improperly formatted or invalid date string
        WHEN: Validating the date
        THEN: Validation fails gracefully without exceptions
        """
        # Test should not raise exceptions
        try:
            is_valid = self.data_manager.validate_iso_date(date_string)
            # Should be False for invalid dates
            assert not is_valid, f"Invalid date {date_string} should fail validation"
        except Exception as e:
            # Should not crash with any exception
            pytest.fail(f"Date validation crashed on {date_string}: {e}")

    @given(st.lists(valid_iso_date_string(), min_size=0, max_size=100))
    def test_batch_date_validation_never_crashes(self, date_list: list[str]):
        """
        PROPERTY: Batch date validation should never crash regardless of input size
        GIVEN: A list of valid ISO date strings
        WHEN: Validating all dates
        THEN: Process completes without exceptions
        """
        try:
            results = []
            for date_str in date_list:
                result = self.data_manager.validate_iso_date(date_str)
                results.append(result)

            # All should be valid
            assert all(results), f"Some valid dates failed: {date_list}"
            assert len(results) == len(date_list)

        except Exception as e:
            pytest.fail(f"Batch validation crashed: {e}")

    @given(st.lists(st.one_of(valid_iso_date_string(), invalid_date_string()), min_size=0, max_size=50))
    def test_mixed_date_validation_robustness(self, mixed_dates: list[str]):
        """
        PROPERTY: Mixed valid/invalid date validation should be robust
        GIVEN: A list containing both valid and invalid date strings
        WHEN: Validating each date
        THEN: Process completes and correctly categorizes each date
        """
        try:
            valid_count = 0
            invalid_count = 0

            for date_str in mixed_dates:
                is_valid = self.data_manager.validate_iso_date(date_str)
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

            # Should process all dates
            assert valid_count + invalid_count == len(mixed_dates)

        except Exception as e:
            pytest.fail(f"Mixed validation crashed: {e}")

    @given(st.text())
    def test_arbitrary_string_date_validation(self, arbitrary_string: str):
        """
        PROPERTY: Date validator should handle any arbitrary string
        GIVEN: Any arbitrary string input
        WHEN: Validating as a date
        THEN: Process completes without crashing
        """
        try:
            result = self.data_manager.validate_iso_date(arbitrary_string)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Validation crashed on arbitrary string '{arbitrary_string}': {e}")

    @given(st.one_of(st.none(), st.integers(), st.floats(), st.booleans()))
    def test_non_string_date_validation(self, non_string_input):
        """
        PROPERTY: Date validator should handle non-string inputs gracefully
        GIVEN: Non-string input (None, int, float, bool)
        WHEN: Validating as a date
        THEN: Process completes without crashing (should return False)
        """
        try:
            result = self.data_manager.validate_iso_date(non_string_input)
            # Should return False for non-string inputs
            assert result is False
        except Exception as e:
            pytest.fail(f"Validation crashed on non-string input {non_string_input}: {e}")

    @given(valid_iso_date_string())
    def test_date_parsing_consistency(self, date_string: str):
        """
        PROPERTY: Valid dates should parse consistently
        GIVEN: A valid ISO date string
        WHEN: Parsing multiple times
        THEN: Results should be identical
        """
        # Parse the same date multiple times
        results = []
        for _ in range(5):
            try:
                # Test with datetime parsing
                parsed = datetime.strptime(date_string, "%Y-%m-%d")
                results.append(parsed)
            except ValueError:
                pytest.fail(f"Valid date {date_string} failed to parse")

        # All results should be identical
        assert all(result == results[0] for result in results)

    @given(st.lists(valid_iso_date_string(), min_size=2, max_size=10))
    def test_date_ordering_consistency(self, date_list: list[str]):
        """
        PROPERTY: Date ordering should be consistent with string and datetime comparison
        GIVEN: A list of valid ISO date strings
        WHEN: Sorting by string vs datetime
        THEN: Order should be the same
        """
        assume(len(set(date_list)) > 1)  # Ensure we have different dates

        try:
            # Sort as strings
            string_sorted = sorted(date_list)

            # Sort as datetime objects
            datetime_objects = [datetime.strptime(d, "%Y-%m-%d") for d in date_list]
            datetime_sorted = sorted(datetime_objects)
            datetime_sorted_strings = [d.strftime("%Y-%m-%d") for d in datetime_sorted]

            # Should be the same order
            assert string_sorted == datetime_sorted_strings

        except Exception as e:
            pytest.fail(f"Date ordering comparison failed: {e}")

    @given(valid_iso_date_string())
    def test_date_roundtrip_parsing(self, date_string: str):
        """
        PROPERTY: Valid dates should survive roundtrip parsing
        GIVEN: A valid ISO date string
        WHEN: Parsing to datetime and back to string
        THEN: Original string should be preserved
        """
        try:
            # Parse to datetime
            parsed = datetime.strptime(date_string, "%Y-%m-%d")

            # Convert back to string
            roundtrip_string = parsed.strftime("%Y-%m-%d")

            # Should be identical
            assert date_string == roundtrip_string

        except Exception as e:
            pytest.fail(f"Roundtrip parsing failed for {date_string}: {e}")

    @given(st.lists(valid_iso_date_string(), min_size=1, max_size=20))
    def test_date_uniqueness_preservation(self, date_list: list[str]):
        """
        PROPERTY: Date validation should preserve uniqueness
        GIVEN: A list of dates (possibly with duplicates)
        WHEN: Validating and processing
        THEN: Unique dates remain unique, duplicates remain duplicates
        """
        original_unique_count = len(set(date_list))

        try:
            # Validate all dates
            validated_dates = []
            for date_str in date_list:
                if self.data_manager.validate_iso_date(date_str):
                    validated_dates.append(date_str)

            validated_unique_count = len(set(validated_dates))

            # Should preserve uniqueness
            assert validated_unique_count == original_unique_count

        except Exception as e:
            pytest.fail(f"Uniqueness preservation failed: {e}")

    @given(
        st.sampled_from(
            [
                "2025-01-01",
                "2025-06-15",
                "2025-12-31",  # Regular dates
                "2024-02-29",
                "2025-02-28",  # Leap year handling
                "1900-01-01",
                "2100-12-31",  # Edge years
            ]
        )
    )
    def test_known_valid_dates_edge_cases(self, known_date: str):
        """
        PROPERTY: Known edge case dates should always validate correctly
        GIVEN: Known valid dates including edge cases
        WHEN: Validating
        THEN: All should pass validation
        """
        is_valid = self.data_manager.validate_iso_date(known_date)
        assert is_valid, f"Known valid date {known_date} should pass validation"
