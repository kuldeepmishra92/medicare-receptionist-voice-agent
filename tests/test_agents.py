"""
Tests — Agent Tests
"""
import pytest
from app.agents.tools import map_symptom_to_specialization


def test_symptom_mapping_chest_pain():
    result = map_symptom_to_specialization.invoke({"symptom": "chest pain"})
    assert result == "Cardiologist"


def test_symptom_mapping_skin_rash():
    result = map_symptom_to_specialization.invoke({"symptom": "skin rash"})
    assert result == "Dermatologist"


def test_symptom_mapping_eye_problem():
    result = map_symptom_to_specialization.invoke({"symptom": "eye irritation"})
    assert result == "Ophthalmologist"


def test_symptom_mapping_ear_pain():
    result = map_symptom_to_specialization.invoke({"symptom": "ear pain"})
    assert result == "ENT Specialist"


def test_symptom_mapping_unknown():
    result = map_symptom_to_specialization.invoke({"symptom": "unknown symptom"})
    assert result == "General Physician"
