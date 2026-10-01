import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "features" in data
    assert data["features"]["loan_engine"] == "operational"

def test_emi_calculate_endpoint():
    payload = {
        "user_id": "test_user",
        "principal_loan_amount": 500000,
        "annual_interest_rate_percent": 10.5,
        "loan_tenure_months": 36
    }
    response = client.post("/api/emi/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "monthly_emi" in data
    assert data["monthly_emi"] > 0
    assert data["principal_amount"] == 500000
    assert len(data["amortization_preview"]) > 0

def test_credit_analyze_endpoint():
    payload = {
        "user_id": "test_user",
        "credit_score": 750,
        "credit_utilization_percent": 22.5,
        "number_of_active_loans": 2,
        "number_of_credit_cards": 3,
        "existing_monthly_debt": 15000,
        "monthly_income": 75000,
        "payment_history_percent": 98.0,
        "recent_credit_inquiries": 1
    }
    response = client.post("/api/credit/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["credit_health_category"] == "Very Good"
    assert len(data["key_factors"]) >= 3

def test_credit_validation_rejection():
    # Invalid credit score below 300
    payload = {
        "user_id": "test_user",
        "credit_score": 250,
        "credit_utilization_percent": 20.0,
        "number_of_active_loans": 1,
        "number_of_credit_cards": 1,
        "payment_history_percent": 90.0,
        "recent_credit_inquiries": 0
    }
    response = client.post("/api/credit/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False

def test_loan_eligibility_endpoint():
    payload = {
        "user_id": "test_user",
        "monthly_income": 95000,
        "existing_monthly_emis": 8000,
        "employment_type": "Salaried",
        "employment_duration_years": 3.0,
        "requested_loan_amount": 800000,
        "loan_tenure_months": 48,
        "interest_rate_percent": 9.25,
        "credit_score": 760,
        "monthly_expenses": 25000,
        "age": 30
    }
    response = client.post("/api/loan/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "eligible" in data
    assert "dti" in data
    assert "estimated_loan_amount" in data
    assert "recommendations" in data

def test_history_endpoint():
    response = client.get("/api/history/user_default")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert isinstance(data["records"], list)

def test_user_creation_and_listing():
    user_payload = {
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "occupation": "Financial Analyst"
    }
    create_res = client.post("/api/users", json=user_payload)
    assert create_res.status_code == 200
    user_data = create_res.json()
    assert user_data["name"] == "Priya Nair"

    list_res = client.get("/api/users")
    assert list_res.status_code == 200
    users = list_res.json()
    assert len(users) >= 1
