import json
from django.db import models
from django.utils import timezone


class User(models.Model):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, max_length=191)
    phone = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    last_login = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class HealthProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='health_profile')
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    chronic_conditions = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'health_profiles'

    def __str__(self):
        return f"Health Profile for {self.user.email}"


class Doctor(models.Model):
    doctor_name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=100)
    hospital = models.CharField(max_length=150, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    availability = models.CharField(max_length=100, blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, null=True)
    experience = models.CharField(max_length=50, blank=True, null=True)
    contact = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'doctors'
        ordering = ['doctor_name']

    def __str__(self):
        return f"{self.doctor_name} ({self.specialization})"


class SymptomSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptom_sessions')
    session_id = models.CharField(max_length=64, db_index=True)
    primary_symptom = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='completed')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'symptom_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} - User {self.user_id}"


class TriageReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triage_reports')
    session_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    possible_condition = models.CharField(max_length=255)
    urgency = models.CharField(max_length=50, default='medium')
    recommended_specialist = models.CharField(max_length=100, blank=True, null=True)
    reasoning = models.TextField(blank=True, null=True)
    guidance = models.TextField(blank=True, null=True)
    explanation = models.TextField(blank=True, null=True)
    image_analysis = models.JSONField(blank=True, null=True)
    image_path = models.CharField(max_length=255, blank=True, null=True)
    symptoms_listed = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'triage_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.id} - {self.possible_condition} ({self.urgency})"


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'appointments'
        ordering = ['-appointment_date']

    def __str__(self):
        return f"Appointment #{self.id} with {self.doctor.doctor_name} ({self.status})"


class MedicalDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_documents')
    original_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100, default='Medical Document')
    file_size = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='application/pdf')
    ai_analysis = models.JSONField(blank=True, null=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'medical_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Document #{self.id}: {self.original_name}"


class MedicationSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medications')
    document = models.ForeignKey(MedicalDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescribed_medications')
    medicine_name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.CharField(max_length=50, default='once_daily')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'medication_schedule'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage}) for User #{self.user_id}"
