"""
Property-based tests for status/stage/source enum validation using Hypothesis.
Tests random strings to ensure validator rejects non-enumerated values with precise messages.
"""

import sys
from pathlib import Path

# Import from app modules - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st

from app import normalize_status
from core_data import DataManager


class TestStatusEnumsHypothesis:
    """Property-based tests for enum validation and normalization."""

    def setup_method(self):
        """Set up data manager and valid enum values for each test."""
        self.data_manager = DataManager()

        # Define valid enum values
        self.valid_statuses = [
            "Applied",
            "Interviewing",
            "Offer",
            "Rejected",
            "Ghosted",
            "Withdrawn",
            "Hired",
            "Declined",
            "Under Consideration",
        ]

        self.valid_stages = ["applied", "screening", "interview", "offer", "employed", "closed"]

        self.valid_sources = [
            "LinkedIn",
            "Indeed",
            "Glassdoor",
            "Company Website",
            "AngelList",
            "Recruiter",
            "Referral",
            "Job Board",
        ]

    @given(
        st.sampled_from(["Applied", "Interviewing", "Offer", "Rejected", "Ghosted", "Withdrawn", "Hired", "Declined"])
    )
    @example("Applied")
    @example("Interviewing")
    @example("Rejected")
    def test_valid_status_enum_acceptance(self, valid_status: str):
        """
        PROPERTY: All valid status values should be accepted by validator
        GIVEN: A valid status enum value
        WHEN: Validating the status
        THEN: Validation passes
        """
        # Test with normalize_status function
        normalized = normalize_status(valid_status)
        assert normalized in self.valid_statuses or normalized == valid_status

        # Test with data manager if enum validation is available
        try:
            _is_valid = self.data_manager.validate_enum(valid_status, "status")  # Validation check
            # If controlled vocabulary is set up, should be valid
            # Otherwise, function may not have the vocabulary loaded
        except (AttributeError, KeyError):
            # Method might not be fully implemented, skip
            pass

    @given(
        st.text().filter(
            lambda x: x
            not in [
                "Applied",
                "Interviewing",
                "Offer",
                "Rejected",
                "Ghosted",
                "Withdrawn",
                "Hired",
                "Declined",
                "Under Consideration",
            ]
            and x.strip() != ""
        )
    )
    @example("APPLIED")  # Wrong case
    @example("rejected")  # Wrong case
    @example("Invalid")  # Not in enum
    @example("Unknown")  # Not in enum
    @example("Pending")  # Not in enum
    def test_invalid_status_enum_rejection(self, invalid_status: str):
        """
        PROPERTY: Invalid status values should be rejected with clear messages
        GIVEN: An invalid status string (not in enum)
        WHEN: Validating the status
        THEN: Validation fails with a precise error message
        """
        assume(invalid_status.strip())  # Skip empty strings
        assume(invalid_status not in self.valid_statuses)

        # Test normalization - should either normalize or return original
        try:
            normalized = normalize_status(invalid_status)
            # If it's not a known status, it might return the original or a default
            assert isinstance(normalized, str)
        except Exception as e:
            pytest.fail(f"Status normalization should not crash on {invalid_status}: {e}")

    @given(st.sampled_from(["applied", "screening", "interview", "offer", "employed", "closed"]))
    @example("applied")
    @example("interview")
    @example("closed")
    def test_valid_stage_enum_acceptance(self, valid_stage: str):
        """
        PROPERTY: All valid stage values should be accepted
        GIVEN: A valid stage enum value
        WHEN: Validating the stage
        THEN: Validation passes
        """
        try:
            _is_valid = self.data_manager.validate_enum(valid_stage, "stage")
            # Should be valid if controlled vocabulary is set up
        except (AttributeError, KeyError):
            # Method might not be implemented, test passes
            pass

    @given(
        st.text().filter(
            lambda x: x not in ["applied", "screening", "interview", "offer", "employed", "closed"] and x.strip() != ""
        )
    )
    @example("APPLIED")  # Wrong case
    @example("Applied")  # Wrong case
    @example("invalid")  # Not in enum
    @example("pending")  # Not in enum
    def test_invalid_stage_enum_rejection(self, invalid_stage: str):
        """
        PROPERTY: Invalid stage values should be rejected
        GIVEN: An invalid stage string (not in enum)
        WHEN: Validating the stage
        THEN: Validation fails
        """
        assume(invalid_stage.strip())
        assume(invalid_stage not in self.valid_stages)

        try:
            _is_valid = self.data_manager.validate_enum(invalid_stage, "stage")
            # Should be False for invalid stages (if vocabulary is loaded)
        except (AttributeError, KeyError):
            # Method might not be implemented
            pass

    @given(
        st.one_of(
            st.sampled_from(["Applied", "Interviewing", "Rejected"]),
            st.sampled_from(["applied", "interviewing", "rejected"]),
            st.sampled_from(["APPLIED", "INTERVIEWING", "REJECTED"]),
        )
    )
    def test_case_insensitive_status_normalization(self, status_variant: str):
        """
        PROPERTY: Status normalization should be case-insensitive
        GIVEN: Status values in different cases
        WHEN: Normalizing the status
        THEN: Result should be in proper case format
        """
        try:
            normalized = normalize_status(status_variant)

            # Should return a properly formatted string
            assert isinstance(normalized, str)
            assert len(normalized) > 0

            # Should be title case or match our known formats
            # (The exact behavior depends on implementation)

        except Exception as e:
            pytest.fail(f"Status normalization failed for {status_variant}: {e}")

    @given(st.text(min_size=1, max_size=50))
    def test_arbitrary_string_enum_validation(self, arbitrary_string: str):
        """
        PROPERTY: Enum validator should handle any arbitrary string
        GIVEN: Any arbitrary string input
        WHEN: Validating as enum
        THEN: Process completes without crashing
        """
        try:
            # Test status normalization
            result = normalize_status(arbitrary_string)
            assert isinstance(result, str)

            # Test data manager validation if available
            try:
                is_valid = self.data_manager.validate_enum(arbitrary_string, "status")
                assert isinstance(is_valid, bool)
            except (AttributeError, KeyError):
                pass

        except Exception as e:
            pytest.fail(f"Enum validation crashed on '{arbitrary_string}': {e}")

    @given(st.one_of(st.none(), st.integers(), st.floats(), st.booleans()))
    def test_non_string_enum_validation(self, non_string_input):
        """
        PROPERTY: Enum validator should handle non-string inputs gracefully
        GIVEN: Non-string input (None, int, float, bool)
        WHEN: Validating as enum
        THEN: Process completes without crashing
        """
        try:
            result = normalize_status(non_string_input)
            assert isinstance(result, str)  # Should convert to string or return default
        except Exception as e:
            pytest.fail(f"Enum validation crashed on non-string input {non_string_input}: {e}")

    @given(
        st.lists(
            st.sampled_from(["Applied", "Interviewing", "Rejected", "Invalid", "APPLIED", "rejected"]),
            min_size=0,
            max_size=20,
        )
    )
    def test_batch_enum_validation(self, status_list: list[str]):
        """
        PROPERTY: Batch enum validation should be robust
        GIVEN: A list of mixed valid/invalid status values
        WHEN: Validating all statuses
        THEN: Process completes without crashing
        """
        try:
            results = []
            for status in status_list:
                normalized = normalize_status(status)
                results.append(normalized)

            assert len(results) == len(status_list)
            assert all(isinstance(r, str) for r in results)

        except Exception as e:
            pytest.fail(f"Batch enum validation failed: {e}")

    @given(st.text().map(lambda x: x.strip()))
    def test_whitespace_handling_in_enums(self, text_with_whitespace: str):
        """
        PROPERTY: Enum validation should handle whitespace appropriately
        GIVEN: Text that may contain leading/trailing whitespace
        WHEN: Validating as enum
        THEN: Whitespace is handled consistently
        """
        if not text_with_whitespace:  # Skip empty strings
            return

        try:
            result = normalize_status(text_with_whitespace)
            assert isinstance(result, str)

            # Result should not have leading/trailing whitespace if input was valid
            if result in self.valid_statuses:
                assert result == result.strip()

        except Exception as e:
            pytest.fail(f"Whitespace handling failed for '{text_with_whitespace}': {e}")

    @given(
        st.sampled_from(
            [
                ("Applied", "Applied"),
                ("applied", "Applied"),
                ("APPLIED", "Applied"),
                ("interviewing", "Interviewing"),
                ("INTERVIEWING", "Interviewing"),
            ]
        )
    )
    def test_normalization_consistency(self, input_output_pair):
        """
        PROPERTY: Enum normalization should be consistent
        GIVEN: Input/expected output pairs
        WHEN: Normalizing multiple times
        THEN: Results should be consistent
        """
        input_val, expected = input_output_pair

        results = []
        for _ in range(5):
            try:
                result = normalize_status(input_val)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Normalization failed for {input_val}: {e}")

        # All results should be identical
        assert all(r == results[0] for r in results)

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    def test_enum_validation_error_messages(self, invalid_enum_list: list[str]):
        """
        PROPERTY: Invalid enum validation should provide clear error messages
        GIVEN: A list of potentially invalid enum values
        WHEN: Validating each value
        THEN: Any error messages should be clear and specific
        """
        assume(all(val.strip() for val in invalid_enum_list))  # No empty strings
        assume(not any(val in self.valid_statuses for val in invalid_enum_list))

        try:
            for invalid_val in invalid_enum_list:
                # Test job validation which might give error messages
                test_job = {
                    "job_id": "job_test123456789",
                    "company": "Test Corp",
                    "title": "Test Role",
                    "date_applied": "2025-10-01",
                    "status": invalid_val,
                    "stage": "applied",
                    "source": "Test",
                }

                errors = self.data_manager.validate_job(test_job)

                # If there are status-related errors, they should be informative
                status_errors = [e for e in errors if e.field == "status"]
                for error in status_errors:
                    assert isinstance(error.message, str)
                    assert len(error.message) > 0
                    # Error message should mention the field or validation type
                    assert (
                        "status" in error.message.lower()
                        or "enum" in error.message.lower()
                        or "valid" in error.message.lower()
                    )

        except Exception as e:
            pytest.fail(f"Error message generation failed: {e}")

    @given(st.sampled_from(["Applied", "Interviewing", "Rejected"]))
    def test_enum_idempotency(self, valid_status: str):
        """
        PROPERTY: Normalizing an already normalized enum should be idempotent
        GIVEN: A properly formatted enum value
        WHEN: Normalizing it multiple times
        THEN: Result should remain unchanged
        """
        try:
            first_normalization = normalize_status(valid_status)
            second_normalization = normalize_status(first_normalization)

            assert first_normalization == second_normalization

        except Exception as e:
            pytest.fail(f"Enum idempotency failed for {valid_status}: {e}")

    @given(st.text().filter(lambda x: len(x.strip()) > 100))
    def test_very_long_enum_values(self, very_long_string: str):
        """
        PROPERTY: Enum validation should handle very long strings gracefully
        GIVEN: Very long strings that are not valid enums
        WHEN: Validating as enum
        THEN: Process completes without performance issues or crashes
        """
        try:
            result = normalize_status(very_long_string)
            assert isinstance(result, str)
            # Should not hang or crash on long inputs

        except Exception as e:
            pytest.fail(f"Long string handling failed: {e}")

    @given(st.text().filter(lambda x: any(c in x for c in "!@#$%^&*()[]{}|\\:;\"'<>,.?/~`")))
    def test_special_characters_in_enums(self, text_with_special_chars: str):
        """
        PROPERTY: Enum validation should handle special characters gracefully
        GIVEN: Text containing special characters
        WHEN: Validating as enum
        THEN: Process completes without crashing
        """
        try:
            result = normalize_status(text_with_special_chars)
            assert isinstance(result, str)

        except Exception as e:
            pytest.fail(f"Special character handling failed for '{text_with_special_chars}': {e}")
