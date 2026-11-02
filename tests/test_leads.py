"""
Tests for the Leads module.
Tests schema validation, CRUD operations, conversion logic, and calendar integration.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from core_data import data_manager, ValidationError


class TestLeadsSchema:
    """Test leads schema validation."""
    
    def test_validate_lead_valid(self):
        """Test validation of a valid lead."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "role": "Engineer",
            "email": "jane@example.com",
            "linkedin": "https://example.com/demo-profile",
            "contact_method": "email",
            "date_contacted": "2025-11-05",
            "status": "Active",
            "source": "Networking",
            "topic": "Software architecture roles",
            "notes": "Initial inquiry",
            "next_action": {
                "what": "Follow up",
                "when": "2025-11-12",
                "done": False
            },
            "linked_job_id": None
        }
        
        errors = data_manager.validate_lead(lead)
        assert len([e for e in errors if e.severity == "error"]) == 0
    
    def test_validate_lead_missing_required(self):
        """Test validation fails when required fields are missing."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            # Missing company, contact_method, date_contacted, status
        }
        
        errors = data_manager.validate_lead(lead)
        error_fields = [e.field for e in errors if e.severity == "error"]
        assert "company" in error_fields
        assert "contact_method" in error_fields
        assert "date_contacted" in error_fields
        assert "status" in error_fields
    
    def test_validate_lead_invalid_date(self):
        """Test validation fails for invalid date format."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "email",
            "date_contacted": "11-05-2025",  # Invalid format
            "status": "Active"
        }
        
        errors = data_manager.validate_lead(lead)
        error_fields = [e.field for e in errors if e.severity == "error"]
        assert "date_contacted" in error_fields
    
    def test_validate_lead_invalid_status(self):
        """Test validation fails for invalid status."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "email",
            "date_contacted": "2025-11-05",
            "status": "InvalidStatus"
        }
        
        errors = data_manager.validate_lead(lead)
        error_fields = [e.field for e in errors if e.severity == "error"]
        assert "status" in error_fields
    
    def test_validate_lead_invalid_contact_method(self):
        """Test validation fails for invalid contact method."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "carrier_pigeon",  # Invalid
            "date_contacted": "2025-11-05",
            "status": "Active"
        }
        
        errors = data_manager.validate_lead(lead)
        error_fields = [e.field for e in errors if e.severity == "error"]
        assert "contact_method" in error_fields


class TestLeadIDGeneration:
    """Test lead ID generation."""
    
    def test_generate_lead_id(self):
        """Test that lead IDs are generated consistently."""
        name = "Jane Doe"
        company = "Tech Corp"
        date = "2025-11-05"
        
        id1 = data_manager.generate_lead_id(name, company, date)
        id2 = data_manager.generate_lead_id(name, company, date)
        
        assert id1 == id2
        assert id1.startswith("lead_")
    
    def test_generate_lead_id_uniqueness(self):
        """Test that different inputs generate different IDs."""
        id1 = data_manager.generate_lead_id("Jane Doe", "Tech Corp", "2025-11-05")
        id2 = data_manager.generate_lead_id("John Smith", "Tech Corp", "2025-11-05")
        
        assert id1 != id2


class TestLeadsDataOperations:
    """Test leads data persistence."""
    
    def test_save_and_load_leads(self, tmp_path):
        """Test saving and loading leads data."""
        # Create temporary data directory
        original_data_dir = data_manager.data_dir
        data_manager.data_dir = tmp_path
        
        try:
            leads_data = {
                "schema_version": 1,
                "leads": [
                    {
                        "lead_id": "lead_001",
                        "name": "Jane Doe",
                        "company": "Tech Corp",
                        "role": "Engineer",
                        "email": "jane@example.com",
                        "linkedin": "",
                        "contact_method": "email",
                        "date_contacted": "2025-11-05",
                        "status": "Active",
                        "source": "Networking",
                        "topic": "Software roles",
                        "notes": "Initial contact",
                        "next_action": {
                            "what": "Follow up",
                            "when": "2025-11-12",
                            "done": False
                        },
                        "linked_job_id": None
                    }
                ]
            }
            
            # Save leads
            success = data_manager.save_leads(leads_data)
            assert success
            
            # Load leads
            loaded_data, errors = data_manager.load_leads()
            assert len(errors) == 0
            assert len(loaded_data["leads"]) == 1
            assert loaded_data["leads"][0]["name"] == "Jane Doe"
        
        finally:
            data_manager.data_dir = original_data_dir
    
    def test_load_nonexistent_leads_file(self, tmp_path):
        """Test loading leads when file doesn't exist."""
        original_data_dir = data_manager.data_dir
        data_manager.data_dir = tmp_path
        
        try:
            loaded_data, errors = data_manager.load_leads()
            assert loaded_data["schema_version"] == 1
            assert loaded_data["leads"] == []
            assert len(errors) == 0
        
        finally:
            data_manager.data_dir = original_data_dir


class TestLeadsControlledVocabulary:
    """Test controlled vocabulary for leads."""
    
    def test_lead_statuses_available(self):
        """Test that lead status values are available."""
        settings = data_manager.settings
        lead_statuses = settings.get("controlled_vocabularies", {}).get("lead_status", [])
        
        expected_statuses = ["Active", "Replied", "No Response", "Converted", "Closed"]
        assert all(status in lead_statuses for status in expected_statuses)
    
    def test_contact_methods_available(self):
        """Test that contact method values are available."""
        settings = data_manager.settings
        methods = settings.get("controlled_vocabularies", {}).get("contact_method", [])
        
        expected_methods = ["email", "linkedin", "phone", "in-person", "other"]
        assert all(method in methods for method in expected_methods)
    
    def test_lead_sources_available(self):
        """Test that lead source values are available."""
        settings = data_manager.settings
        sources = settings.get("controlled_vocabularies", {}).get("lead_source", [])
        
        expected_sources = ["Networking", "LinkedIn", "Referral", "Company Website", "Job Board", "Event", "Other"]
        assert all(source in sources for source in expected_sources)


class TestLeadNextActions:
    """Test lead next action reminders."""
    
    def test_lead_next_action_structure(self):
        """Test that next action has proper structure."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "email",
            "date_contacted": "2025-11-05",
            "status": "Active",
            "next_action": {
                "what": "Send portfolio",
                "when": "2025-11-12",
                "done": False
            }
        }
        
        errors = data_manager.validate_lead(lead)
        # Should have no errors related to next_action
        next_action_errors = [e for e in errors if "next_action" in e.field]
        assert len(next_action_errors) == 0
    
    def test_lead_without_next_action(self):
        """Test that lead can exist without next_action."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "email",
            "date_contacted": "2025-11-05",
            "status": "Active"
        }
        
        errors = data_manager.validate_lead(lead)
        error_count = len([e for e in errors if e.severity == "error"])
        # Should only have no data-level errors (only required field errors)
        assert error_count == 0


class TestLeadsIntegration:
    """Test leads module integration with jobs."""
    
    def test_lead_linked_to_job(self):
        """Test that a lead can be linked to a job."""
        lead = {
            "lead_id": "lead_001",
            "name": "Jane Doe",
            "company": "Tech Corp",
            "contact_method": "email",
            "date_contacted": "2025-11-05",
            "status": "Converted",
            "linked_job_id": "job_abc123"
        }
        
        errors = data_manager.validate_lead(lead)
        assert len([e for e in errors if e.severity == "error"]) == 0
    
    def test_lead_source_values(self):
        """Test various lead source values."""
        sources = ["Networking", "LinkedIn", "Referral", "Company Website", "Job Board", "Event", "Other"]
        
        for source in sources:
            lead = {
                "lead_id": "lead_001",
                "name": "Jane Doe",
                "company": "Tech Corp",
                "contact_method": "email",
                "date_contacted": "2025-11-05",
                "status": "Active",
                "source": source
            }
            
            errors = data_manager.validate_lead(lead)
            source_errors = [e for e in errors if e.field == "source" and e.severity == "error"]
            assert len(source_errors) == 0, f"Source '{source}' should be valid"


class TestLeadsNormalization:
    """Test leads enum normalization."""
    
    def test_normalize_lead_status(self):
        """Test that lead status is normalized correctly."""
        # Test case-insensitive normalization
        normalized = data_manager.normalize_enum("active", "lead_status")
        assert normalized == "Active"
        
        normalized = data_manager.normalize_enum("REPLIED", "lead_status")
        assert normalized == "Replied"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
