from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from medisa_api.models import (
    User, HealthProfile, Doctor, SymptomSession,
    TriageReport, Appointment, MedicationSchedule, MedicalDocument
)
from medisa_api.views import hash_password


class Command(BaseCommand):
    help = 'Seeds initial test data into the database matching MediSA schema.sql'

    def handle(self, *args, **options):
        self.stdout.write("Seeding database with MediSA demo records...")

        # Password hash for "password123"
        pw_hash = hash_password("password123")

        # 1. Users
        user1, _ = User.objects.get_or_create(
            id=1,
            defaults={
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com',
                'phone': '+8801712345678',
                'dob': '1990-05-15',
                'password_hash': pw_hash,
                'role': 'patient',
            }
        )

        user2, _ = User.objects.get_or_create(
            id=2,
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Rahman',
                'email': 'sarah.rahman@example.com',
                'phone': '+8801812345678',
                'dob': '1985-08-22',
                'password_hash': pw_hash,
                'role': 'patient',
            }
        )

        # 2. Health Profiles
        HealthProfile.objects.get_or_create(
            user=user1,
            defaults={
                'blood_group': 'O+',
                'allergies': 'Penicillin, Dust',
                'chronic_conditions': 'Mild Asthma',
                'emergency_contact': '+8801799887766'
            }
        )

        HealthProfile.objects.get_or_create(
            user=user2,
            defaults={
                'blood_group': 'B+',
                'allergies': 'None',
                'chronic_conditions': 'None',
                'emergency_contact': '+8801899887766'
            }
        )

        # 3. Doctors
        doctors_data = [
            (1, 'Dr. Rahim Ahmed', 'Cardiologist', 'Dhaka Medical College Hospital', 'Dhaka', 'Mon-Fri 10:00 AM - 2:00 PM', 'MBBS, FCPS (Cardiology)', '12 years', '+8801711111111', 'Senior consultant in cardiovascular diseases and interventional cardiology.'),
            (2, 'Dr. Nasrin Islam', 'Medicine Specialist', 'Square Hospital', 'Dhaka', 'Sun-Thu 4:00 PM - 8:00 PM', 'MBBS, MD (Internal Medicine)', '10 years', '+8801722222222', 'Specialist in complex internal medicine, infectious diseases, and diabetes care.'),
            (3, 'Dr. Karim Hossain', 'Neurologist', 'BIRDEM General Hospital', 'Dhaka', 'Mon-Wed 3:00 PM - 7:00 PM', 'MBBS, FCPS (Neurology)', '15 years', '+8801733333333', 'Expert in migraine management, stroke recovery, and neuropathy.'),
            (4, 'Dr. Fatema Begum', 'Pediatrician', 'Dhaka Shishu Hospital', 'Dhaka', 'Sat-Thu 9:00 AM - 1:00 PM', 'MBBS, DCH, FCPS (Pediatrics)', '8 years', '+8801744444444', 'Dedicated pediatrician specializing in neonatal and child health care.'),
            (5, 'Dr. Arif Siddiqui', 'Dermatologist', 'Evercare Hospital Dhaka', 'Dhaka', 'Mon-Sat 5:00 PM - 9:00 PM', 'MBBS, DDV, FCPS (Dermatology)', '11 years', '+8801755555555', 'Specializes in allergy testing, inflammatory skin diseases, and dermatologic surgery.'),
            (6, 'Dr. Tariq Rahman', 'Gastroenterologist', 'Labaid Specialized Hospital', 'Dhaka', 'Mon-Thu 2:00 PM - 6:00 PM', 'MBBS, MD (Gastroenterology)', '14 years', '+8801766666666', 'Consultant in gastrointestinal disorders, endoscopy, and liver pathology.'),
        ]

        for doc_id, name, spec, hosp, loc, avail, edu, exp, contact, bio in doctors_data:
            Doctor.objects.get_or_create(
                id=doc_id,
                defaults={
                    'doctor_name': name,
                    'specialization': spec,
                    'hospital': hosp,
                    'location': loc,
                    'availability': avail,
                    'education': edu,
                    'experience': exp,
                    'contact': contact,
                    'bio': bio,
                    'is_active': True
                }
            )

        now = timezone.now()

        # 4. Symptom Sessions
        SymptomSession.objects.get_or_create(
            session_id='SESS-DEMO-001',
            defaults={
                'user': user1,
                'primary_symptom': 'High fever, persistent headache, and body aches',
                'status': 'completed',
                'created_at': now - timedelta(days=3)
            }
        )

        SymptomSession.objects.get_or_create(
            session_id='SESS-DEMO-002',
            defaults={
                'user': user1,
                'primary_symptom': 'Mild skin rash on left forearm',
                'status': 'completed',
                'created_at': now - timedelta(days=1)
            }
        )

        # 5. Triage Reports
        TriageReport.objects.get_or_create(
            session_id='SESS-DEMO-001',
            defaults={
                'user': user1,
                'possible_condition': 'Viral Syndrome / Probable Dengue',
                'urgency': 'medium',
                'recommended_specialist': 'Medicine Specialist',
                'reasoning': 'Symptoms of acute high fever, retro-orbital headache, and generalized body aches during monsoon season in Dhaka strongly match viral exanthem / Dengue fever.',
                'guidance': 'Stay well hydrated with oral rehydration solution. Monitor platelet count if fever persists beyond 3 days. Avoid NSAIDs like ibuprofen; use paracetamol for fever.',
                'explanation': 'Your reported symptoms indicate a systemic viral infection. Please consult a physician and get a complete blood count (CBC) test.',
                'symptoms_listed': ['High fever', 'Persistent headache', 'Body aches'],
                'created_at': now - timedelta(days=3)
            }
        )

        # 6. Appointments
        doc2 = Doctor.objects.get(id=2)
        Appointment.objects.get_or_create(
            user=user1,
            doctor=doc2,
            defaults={
                'appointment_date': now + timedelta(days=2),
                'notes': 'Follow-up consultation for persistent viral fever and lab review.',
                'status': 'confirmed',
                'created_at': now
            }
        )

        # 7. Medication Schedule
        MedicationSchedule.objects.get_or_create(
            user=user1,
            medicine_name='Paracetamol',
            defaults={
                'dosage': '500mg',
                'frequency': 'three_times',
                'start_date': now.date(),
                'end_date': (now + timedelta(days=5)).date(),
                'instructions': 'Take after meals for fever relief. Maximum 3000mg/day.',
                'active': True,
                'created_at': now
            }
        )

        MedicationSchedule.objects.get_or_create(
            user=user1,
            medicine_name='Oral Rehydration Salts (ORS)',
            defaults={
                'dosage': '1 sachet in 500ml water',
                'frequency': 'as_needed',
                'start_date': now.date(),
                'end_date': (now + timedelta(days=7)).date(),
                'instructions': 'Sip continuously throughout the day for electrolyte replenishment.',
                'active': True,
                'created_at': now
            }
        )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded with demo data!"))
