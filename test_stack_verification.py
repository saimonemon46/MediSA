#!/usr/bin/env python3
"""
Stack Verification Test Script for MediSA
Verifies:
1. Django backend models, migrations, seed data, and REST API endpoints
2. Next.js frontend pages and build artifacts
3. FastAPI AI microservice routes and LangGraph/RAG dependencies
4. Patient state and triage enhancement tests
"""

import os
import sys

os.environ["TORCH_CLOCK_IGNORE_MONOTONIC_ERROR"] = "1"
import json
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'backend_django'))

print("=" * 60)
print("MediSA Stack Verification: Next.js + Django + FastAPI")
print("=" * 60)

# 1. Verify Django
print("\n[1/4] Verifying Django Backend & REST APIs...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medisa_backend.settings')
import django
django.setup()

from django.test import Client
from medisa_api.models import User, Doctor, TriageReport, Appointment, MedicationSchedule

# Verify Seed Data
users_count = User.objects.count()
doctors_count = Doctor.objects.count()
reports_count = TriageReport.objects.count()
meds_count = MedicationSchedule.objects.count()
print(f"  - Seed Data: {users_count} users, {doctors_count} doctors, {reports_count} reports, {meds_count} medications")
assert users_count >= 2, "Seed users missing"
assert doctors_count >= 6, "Seed doctors missing"

client = Client()

# Test Login
login_res = client.post('/api/auth/login', {'email': 'john.doe@example.com', 'password': 'password123'})
assert login_res.status_code == 200 and login_res.json()['success'] is True, "Login failed"
print("  - POST /api/auth/login: PASSED")

# Test Dashboard
dash_res = client.get('/api/dashboard?user_id=1')
assert dash_res.status_code == 200 and dash_res.json()['success'] is True, "Dashboard failed"
print("  - GET /api/dashboard: PASSED")

# Test Doctors Directory
doc_res = client.get('/api/doctors')
assert doc_res.status_code == 200 and len(doc_res.json()['doctors']) >= 6, "Doctors failed"
print("  - GET /api/doctors: PASSED")

# Test Reports
rep_res = client.get('/api/reports?user_id=1')
assert rep_res.status_code == 200 and len(rep_res.json()['reports']) >= 1, "Reports failed"
print("  - GET /api/reports: PASSED")

# Test Appointments
appt_res = client.get('/api/appointments?user_id=1')
assert appt_res.status_code == 200 and len(appt_res.json()['appointments']) >= 1, "Appointments failed"
print("  - GET /api/appointments: PASSED")

# Test Medications
meds_res = client.get('/api/medications?user_id=1')
assert meds_res.status_code == 200 and len(meds_res.json()['medications']) >= 2, "Medications failed"
print("  - GET /api/medications: PASSED")

# 2. Verify FastAPI AI Service
print("\n[2/4] Verifying FastAPI AI Microservice & Endpoints...")
from fastapi_ai.main import app as fastapi_app
routes = []
for r in fastapi_app.routes:
    if hasattr(r, 'path'):
        routes.append(r.path)
    orig = getattr(r, 'original_router', None)
    if orig and hasattr(orig, 'routes'):
        for sub in orig.routes:
            if hasattr(sub, 'path'):
                routes.append(sub.path)
expected_routes = [
    '/', '/health', '/process-message', '/generate-questions',
    '/generate-report', '/analyze-document', '/analyze-symptom-image-for-triage',
    '/doctor-recommendation', '/evaluation/dataset-status', '/evaluation/compare',
    '/evaluation/run'
]
for r in expected_routes:
    assert r in routes, f"Missing route {r} in FastAPI AI service"
    print(f"  - Route {r}: FOUND")

# 3. Verify Next.js Pages & Build Output
print("\n[3/4] Verifying Next.js Pages & Build Outputs...")
next_pages_dir = os.path.join(ROOT_DIR, 'frontend_next', 'pages')
expected_pages = [
    'index.js', 'login.js', 'register.js', 'dashboard.js',
    'symptom-chat.js', 'reports.js', 'doctors.js',
    'appointments.js', 'documents.js', 'medications.js',
    'hospital-dashboard.js', 'research-evaluation.js'
]
for p in expected_pages:
    page_path = os.path.join(next_pages_dir, p)
    assert os.path.isfile(page_path), f"Missing Next.js page: {p}"
    print(f"  - Page {p}: VERIFIED")

next_build_manifest = os.path.join(ROOT_DIR, 'frontend_next', '.next', 'build-manifest.json')
assert os.path.isfile(next_build_manifest), "Next.js build manifest missing"
print("  - Production Build Output (.next): VERIFIED")

# 4. Verify Enhancement Tests
print("\n[4/4] Verifying LangGraph Patient State & Differential Diagnosis Engine...")
import test_enhancements
test_enhancements.test_patient_state_creation()
test_enhancements.test_question_deduplication()
test_enhancements.test_state_management()
test_enhancements.test_diagnostic_scoring()
test_enhancements.test_state_persistence()
test_enhancements.test_symptom_summaries()

print("\n" + "=" * 60)
print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (100% HEALTHY)")
print("=" * 60)
