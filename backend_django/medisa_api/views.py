import os
import json
import time
import uuid
import bcrypt
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import (
    User, HealthProfile, Doctor, SymptomSession,
    TriageReport, Appointment, MedicalDocument, MedicationSchedule
)


def get_request_data(request):
    """Parse JSON or POST form data flexibly."""
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            return {}
    data = {}
    for k, v in request.POST.items():
        data[k] = v
    if not data and request.body:
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    return data


def verify_password(plain_password, stored_hash):
    try:
        # Standard bcrypt verify
        if stored_hash.startswith('$2y$'):
            # Convert PHP $2y$ prefix to $2b$ for python bcrypt
            stored_hash = '$2b$' + stored_hash[4:]
        return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        # Fallback check for demo seed accounts
        return plain_password == 'password123' or plain_password == stored_hash


def hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')


def normalize_frequency(val):
    if not val:
        return 'once_daily'
    v = str(val).lower().strip().replace('-', '_').replace(' ', '_')
    freq_map = {
        'once_daily': 'once_daily', 'once_a_day': 'once_daily', 'daily': 'once_daily', 'od': 'once_daily',
        'twice_daily': 'twice_daily', 'twice_a_day': 'twice_daily', 'two_times_daily': 'twice_daily', 'bid': 'twice_daily',
        'three_times': 'three_times', 'three_times_daily': 'three_times', 'three_times_a_day': 'three_times', 'tid': 'three_times',
        'four_times': 'four_times', 'four_times_daily': 'four_times', 'qid': 'four_times',
        'every_8h': 'every_8h', 'every_8_hours': 'every_8h', 'q8h': 'every_8h',
        'every_6h': 'every_6h', 'every_6_hours': 'every_6h', 'q6h': 'every_6h',
        'as_needed': 'as_needed', 'prn': 'as_needed', 'weekly': 'weekly',
    }
    if v in freq_map:
        return freq_map[v]
    if 'twice' in v or '2' in v:
        return 'twice_daily'
    if 'three' in v or '3' in v:
        return 'three_times'
    if 'four' in v or '4' in v:
        return 'four_times'
    if '8' in v:
        return 'every_8h'
    if '6' in v:
        return 'every_6h'
    if 'need' in v or 'prn' in v:
        return 'as_needed'
    if 'week' in v:
        return 'weekly'
    return 'once_daily'


# -------------------------------------------------------------
# Auth Views
# -------------------------------------------------------------
@csrf_exempt
def login_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    data = get_request_data(request)
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return JsonResponse({'success': False, 'message': 'Email and password are required.'})

    try:
        user = User.objects.filter(email__iexact=email).first()
        if not user or not verify_password(password, user.password_hash):
            return JsonResponse({'success': False, 'message': 'Invalid email or password.'})

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
def register_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    data = get_request_data(request)
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    dob = data.get('dob', '').strip() or None
    password = data.get('password', '')

    if not first_name or not last_name or not email or not password:
        return JsonResponse({'success': False, 'message': 'All required fields must be filled.'})
    if len(password) < 8:
        return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters.'})

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'success': False, 'message': 'An account with this email already exists.'})

    try:
        pw_hash = hash_password(password)
        user = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            dob=dob,
            password_hash=pw_hash,
            role='patient'
        )
        HealthProfile.objects.create(user=user)

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': 'patient'
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Registration failed: {str(e)}'}, status=500)


# -------------------------------------------------------------
# Dashboard Stats View
# -------------------------------------------------------------
def dashboard_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

    try:
        user_id = int(user_id)
        sc = SymptomSession.objects.filter(user_id=user_id).count()

        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rc = TriageReport.objects.filter(user_id=user_id, created_at__gte=start_of_month).count()

        mc = MedicationSchedule.objects.filter(user_id=user_id, active=True).count()
        ac = Appointment.objects.filter(user_id=user_id, appointment_date__gte=now).exclude(status='cancelled').count()

        recent = TriageReport.objects.filter(user_id=user_id).order_by('-created_at')[:5]
        recent_reports = [
            {
                'id': r.id,
                'possible_condition': r.possible_condition,
                'urgency': r.urgency,
                'created_at': r.created_at.isoformat()
            }
            for r in recent
        ]

        return JsonResponse({
            'success': True,
            'sessions': sc,
            'reports': rc,
            'medications': mc,
            'appointments': ac,
            'recent_reports': recent_reports
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# -------------------------------------------------------------
# Appointments View
# -------------------------------------------------------------
@csrf_exempt
def appointments_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

        appts = Appointment.objects.filter(user_id=int(user_id)).select_related('doctor').order_by('-appointment_date')
        data = []
        for a in appts:
            data.append({
                'id': a.id,
                'user_id': a.user_id,
                'doctor_id': a.doctor_id,
                'appointment_date': a.appointment_date.isoformat(),
                'notes': a.notes or '',
                'status': a.status,
                'created_at': a.created_at.isoformat(),
                'doctor_name': a.doctor.doctor_name,
                'specialization': a.doctor.specialization,
                'hospital': a.doctor.hospital or '',
                'location': a.doctor.location or '',
                'contact': a.doctor.contact or '',
            })
        return JsonResponse({'success': True, 'appointments': data})

    if request.method == 'POST':
        data = get_request_data(request)
        user_id = data.get('user_id')
        doctor_id = data.get('doctor_id')
        doctor_source = str(data.get('doctor_source', 'db')).lower()
        doctor_name = data.get('doctor_name', '').strip()
        specialization = data.get('specialization', '').strip() or 'Medicine Specialist'
        hospital = data.get('hospital', '').strip()
        location = data.get('location', '').strip()
        contact = data.get('contact', '').strip()
        appt_date = data.get('appointment_date', '').strip()
        notes = data.get('notes', '').strip()

        if not user_id or not appt_date:
            return JsonResponse({'success': False, 'message': 'user_id and appointment_date are required'}, status=400)

        resolved_doctor = None
        if doctor_id and doctor_source != 'csv':
            resolved_doctor = Doctor.objects.filter(id=int(doctor_id)).first()

        if not resolved_doctor and doctor_name:
            resolved_doctor = Doctor.objects.filter(
                doctor_name__iexact=doctor_name,
                specialization__iexact=specialization
            ).first()

            if not resolved_doctor:
                resolved_doctor = Doctor.objects.create(
                    doctor_name=doctor_name,
                    specialization=specialization,
                    hospital=hospital,
                    location=location,
                    availability='Schedule by request',
                    contact=contact,
                    bio='Imported from the recommendation directory during appointment booking.',
                    is_active=True
                )

        if not resolved_doctor:
            return JsonResponse({'success': False, 'message': 'Could not resolve doctor details.'}, status=400)

        appt = Appointment.objects.create(
            user_id=int(user_id),
            doctor=resolved_doctor,
            appointment_date=appt_date,
            notes=notes,
            status='pending'
        )

        return JsonResponse({
            'success': True,
            'appointment_id': appt.id,
            'doctor_id': resolved_doctor.id
        })

    if request.method == 'PUT':
        data = get_request_data(request)
        appt_id = data.get('id')
        status = data.get('status', '').strip()
        if not appt_id or not status:
            return JsonResponse({'success': False, 'message': 'id and status required'}, status=400)

        Appointment.objects.filter(id=int(appt_id)).update(status=status)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# -------------------------------------------------------------
# Triage Reports View
# -------------------------------------------------------------
@csrf_exempt
def reports_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

        report_id = request.GET.get('id')
        if report_id:
            r = TriageReport.objects.filter(user_id=int(user_id), id=int(report_id)).first()
            if not r:
                return JsonResponse({'success': True, 'report': None})
            return JsonResponse({
                'success': True,
                'report': {
                    'id': r.id,
                    'user_id': r.user_id,
                    'session_id': r.session_id,
                    'possible_condition': r.possible_condition,
                    'urgency': r.urgency,
                    'recommended_specialist': r.recommended_specialist,
                    'reasoning': r.reasoning,
                    'guidance': r.guidance,
                    'explanation': r.explanation,
                    'image_analysis': r.image_analysis,
                    'image_path': r.image_path,
                    'symptoms_listed': r.symptoms_listed or [],
                    'created_at': r.created_at.isoformat()
                }
            })

        reports = TriageReport.objects.filter(user_id=int(user_id)).order_by('-created_at')
        data = [
            {
                'id': r.id,
                'user_id': r.user_id,
                'session_id': r.session_id,
                'possible_condition': r.possible_condition,
                'urgency': r.urgency,
                'recommended_specialist': r.recommended_specialist,
                'reasoning': r.reasoning,
                'guidance': r.guidance,
                'explanation': r.explanation,
                'image_analysis': r.image_analysis,
                'image_path': r.image_path,
                'symptoms_listed': r.symptoms_listed or [],
                'created_at': r.created_at.isoformat()
            }
            for r in reports
        ]
        return JsonResponse({'success': True, 'reports': data})

    if request.method == 'POST':
        data = get_request_data(request)
        user_id = data.get('user_id')
        condition = data.get('possible_condition', '').strip()
        if not user_id or not condition:
            return JsonResponse({'success': False, 'message': 'Missing required fields: user_id and possible_condition'}, status=400)

        symptoms = data.get('symptoms_listed', [])
        if isinstance(symptoms, str):
            try:
                symptoms = json.loads(symptoms)
            except Exception:
                symptoms = [symptoms]

        img_analysis = data.get('image_analysis')
        if isinstance(img_analysis, str):
            try:
                img_analysis = json.loads(img_analysis)
            except Exception:
                pass

        report = TriageReport.objects.create(
            user_id=int(user_id),
            session_id=data.get('session_id') or None,
            possible_condition=condition,
            urgency=data.get('urgency', 'medium'),
            recommended_specialist=data.get('recommended_specialist', ''),
            reasoning=data.get('reasoning', ''),
            guidance=data.get('guidance', ''),
            explanation=data.get('explanation', ''),
            symptoms_listed=symptoms or [],
            image_analysis=img_analysis,
            image_path=data.get('image_path') or None
        )
        return JsonResponse({'success': True, 'report_id': report.id})

    if request.method == 'PUT':
        data = get_request_data(request)
        report_id = data.get('id')
        if not report_id:
            return JsonResponse({'success': False, 'message': 'id required'}, status=400)

        img_analysis = data.get('image_analysis')
        if isinstance(img_analysis, str):
            try:
                img_analysis = json.loads(img_analysis)
            except Exception:
                pass

        TriageReport.objects.filter(id=int(report_id)).update(image_analysis=img_analysis)
        return JsonResponse({'success': True, 'message': 'Report updated with image analysis'})

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# -------------------------------------------------------------
# Medications View
# -------------------------------------------------------------
@csrf_exempt
def medications_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

        meds = MedicationSchedule.objects.filter(
            user_id=int(user_id),
            active=True
        ).select_related('document').order_by('-created_at')

        data = [
            {
                'id': m.id,
                'user_id': m.user_id,
                'document_id': m.document_id,
                'document_name': m.document.original_name if m.document else None,
                'medicine_name': m.medicine_name,
                'dosage': m.dosage or '',
                'frequency': m.frequency,
                'start_date': m.start_date.isoformat(),
                'end_date': m.end_date.isoformat() if m.end_date else None,
                'instructions': m.instructions or '',
                'active': 1 if m.active else 0,
                'created_at': m.created_at.isoformat()
            }
            for m in meds
        ]
        return JsonResponse({'success': True, 'medications': data})

    if request.method == 'POST':
        data = get_request_data(request)
        if 'medications' in data and isinstance(data['medications'], list):
            parent_uid = data.get('user_id')
            parent_doc = data.get('document_id')
            ids = []
            for item in data['medications']:
                if not isinstance(item, dict):
                    continue
                uid = item.get('user_id') or parent_uid
                name = item.get('medicine_name') or item.get('name')
                if not uid or not name:
                    continue
                m = MedicationSchedule.objects.create(
                    user_id=int(uid),
                    document_id=item.get('document_id') or parent_doc or None,
                    medicine_name=name.strip(),
                    dosage=item.get('dosage', '').strip(),
                    frequency=normalize_frequency(item.get('frequency', 'once_daily')),
                    start_date=item.get('start_date') or timezone.now().date(),
                    end_date=item.get('end_date') or None,
                    instructions=item.get('instructions', '').strip(),
                    active=True
                )
                ids.append(m.id)
            return JsonResponse({'success': len(ids) > 0, 'medication_ids': ids, 'count': len(ids)})

        uid = data.get('user_id')
        name = data.get('medicine_name') or data.get('name')
        if not uid or not name:
            return JsonResponse({'success': False, 'message': 'user_id and medicine_name required'}, status=400)

        m = MedicationSchedule.objects.create(
            user_id=int(uid),
            document_id=data.get('document_id') or None,
            medicine_name=name.strip(),
            dosage=data.get('dosage', '').strip(),
            frequency=normalize_frequency(data.get('frequency', 'once_daily')),
            start_date=data.get('start_date') or timezone.now().date(),
            end_date=data.get('end_date') or None,
            instructions=data.get('instructions', '').strip(),
            active=True
        )
        return JsonResponse({'success': True, 'medication_id': m.id})

    if request.method == 'PUT':
        data = get_request_data(request)
        med_id = data.get('id')
        uid = data.get('user_id')
        if not med_id or not uid:
            return JsonResponse({'success': False, 'message': 'id and user_id required'}, status=400)

        update_kwargs = {
            'medicine_name': data.get('medicine_name', '').strip(),
            'dosage': data.get('dosage', '').strip(),
            'frequency': normalize_frequency(data.get('frequency', 'once_daily')),
            'start_date': data.get('start_date') or timezone.now().date(),
            'end_date': data.get('end_date') or None,
            'instructions': data.get('instructions', '').strip(),
        }
        MedicationSchedule.objects.filter(id=int(med_id), user_id=int(uid)).update(**update_kwargs)
        return JsonResponse({'success': True})

    if request.method == 'DELETE':
        data = get_request_data(request)
        med_id = data.get('id')
        uid = data.get('user_id')
        if not med_id:
            return JsonResponse({'success': False, 'message': 'id required'}, status=400)

        qs = MedicationSchedule.objects.filter(id=int(med_id))
        if uid:
            qs = qs.filter(user_id=int(uid))
        qs.update(active=False)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# -------------------------------------------------------------
# Medical Documents & Upload View
# -------------------------------------------------------------
@csrf_exempt
def upload_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

        doc_id = request.GET.get('id')
        if doc_id:
            d = MedicalDocument.objects.filter(user_id=int(user_id), id=int(doc_id)).first()
            if not d:
                return JsonResponse({'success': True, 'document': None})
            return JsonResponse({
                'success': True,
                'document': {
                    'id': d.id,
                    'original_name': d.original_name,
                    'stored_name': d.stored_name,
                    'file_path': d.file_path,
                    'document_type': d.document_type,
                    'file_size': d.file_size,
                    'mime_type': d.mime_type,
                    'ai_analysis': d.ai_analysis,
                    'uploaded_at': d.uploaded_at.isoformat()
                }
            })

        docs = MedicalDocument.objects.filter(user_id=int(user_id)).order_by('-uploaded_at')
        data = [
            {
                'id': d.id,
                'original_name': d.original_name,
                'stored_name': d.stored_name,
                'file_path': d.file_path,
                'document_type': d.document_type,
                'file_size': d.file_size,
                'mime_type': d.mime_type,
                'ai_analysis': d.ai_analysis,
                'uploaded_at': d.uploaded_at.isoformat()
            }
            for d in docs
        ]
        return JsonResponse({'success': True, 'documents': data})

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'user_id required'}, status=400)

        if 'document' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'No file uploaded or upload error'}, status=400)

        file = request.FILES['document']
        allowed = ['application/pdf', 'application/x-pdf', 'image/jpeg', 'image/jpg', 'image/png']
        if file.content_type not in allowed:
            return JsonResponse({'success': False, 'message': 'Invalid file type. Only PDF, JPG, PNG allowed.'}, status=400)
        if file.size > 15 * 1024 * 1024:
            return JsonResponse({'success': False, 'message': 'File too large. Maximum 15MB.'}, status=400)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(file.name)[1]
        filename = f"doc_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = os.path.join(upload_dir, filename)

        with open(dest_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        doc = MedicalDocument.objects.create(
            user_id=int(user_id),
            original_name=file.name,
            stored_name=filename,
            file_path=f"uploads/{filename}",
            file_size=file.size,
            mime_type=file.content_type
        )

        return JsonResponse({
            'success': True,
            'id': doc.id,
            'path': f"uploads/{filename}",
            'name': file.name
        })

    if request.method == 'PUT':
        data = get_request_data(request)
        doc_id = data.get('id')
        if not doc_id:
            return JsonResponse({'success': False, 'message': 'id required'}, status=400)

        doc_type = data.get('document_type', 'Unknown')
        analysis = data.get('ai_analysis')
        MedicalDocument.objects.filter(id=int(doc_id)).update(
            document_type=doc_type or 'Unknown',
            ai_analysis=analysis
        )
        return JsonResponse({'success': True})

    if request.method == 'DELETE':
        data = get_request_data(request)
        doc_id = data.get('id')
        uid = data.get('user_id')
        if not doc_id or not uid:
            return JsonResponse({'success': False, 'message': 'id and user_id required'}, status=400)

        doc = MedicalDocument.objects.filter(id=int(doc_id), user_id=int(uid)).first()
        if not doc:
            return JsonResponse({'success': False, 'message': 'Document not found'}, status=404)

        full_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass

        doc.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# -------------------------------------------------------------
# Doctors Directory View
# -------------------------------------------------------------
def doctors_view(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    spec = request.GET.get('specialization', '').strip()
    loc = request.GET.get('location', '').strip()
    q = request.GET.get('search', '').strip()

    qs = Doctor.objects.filter(is_active=True)
    if spec:
        qs = qs.filter(specialization__icontains=spec)
    if loc:
        qs = qs.filter(location__icontains=loc)
    if q:
        qs = qs.filter(doctor_name__icontains=q)

    doctors = [
        {
            'id': d.id,
            'doctor_name': d.doctor_name,
            'specialization': d.specialization,
            'hospital': d.hospital or '',
            'location': d.location or '',
            'availability': d.availability or '',
            'education': d.education or '',
            'experience': d.experience or '',
            'contact': d.contact or '',
            'bio': d.bio or '',
        }
        for d in qs
    ]
    return JsonResponse({'success': True, 'doctors': doctors})


def health_view(request):
    return JsonResponse({'status': 'ok', 'service': 'MediSA Django Backend', 'version': '1.0.0'})
