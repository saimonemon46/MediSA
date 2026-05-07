<?php
// MediAI — API: Appointments
require_once '../includes/config.php';

header('Access-Control-Allow-Origin: *');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$db = getDB();

function resolveDoctorId(PDO $db, int $doctor_id, string $doctor_source, string $doctor_name, string $specialization, string $hospital, string $location, string $contact): int {
    $doctor_source = strtolower($doctor_source);

    if ($doctor_id && $doctor_source !== 'csv') {
        $stmt = $db->prepare('SELECT id FROM doctors WHERE id = ? LIMIT 1');
        $stmt->execute([$doctor_id]);
        $existing = $stmt->fetchColumn();
        if ($existing) {
            return (int)$existing;
        }
    }

    if (!$doctor_name) {
        return 0;
    }

    if (!$specialization) {
        $specialization = 'Medicine Specialist';
    }

    $stmt = $db->prepare('
        SELECT id FROM doctors
        WHERE doctor_name = ?
          AND specialization = ?
          AND COALESCE(hospital, "") = ?
        LIMIT 1
    ');
    $stmt->execute([$doctor_name, $specialization, $hospital]);
    $existing = $stmt->fetchColumn();
    if ($existing) {
        return (int)$existing;
    }

    $stmt = $db->prepare('
        INSERT INTO doctors (doctor_name, specialization, hospital, location, availability, contact, bio, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, NOW())
    ');
    $stmt->execute([
        $doctor_name,
        $specialization,
        $hospital,
        $location,
        'Schedule by request',
        $contact,
        'Imported from the recommendation directory during appointment booking.'
    ]);

    return (int)$db->lastInsertId();
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $user_id = (int)($_GET['user_id'] ?? 0);
    if (!$user_id) { jsonResponse(['success'=>false,'message'=>'user_id required']); }

    $stmt = $db->prepare('
        SELECT a.*, d.doctor_name, d.specialization, d.hospital, d.location, d.contact
        FROM appointments a
        LEFT JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date DESC
    ');
    $stmt->execute([$user_id]);
    jsonResponse(['success'=>true, 'appointments'=>$stmt->fetchAll()]);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user_id    = (int)($_POST['user_id'] ?? 0);
    $doctor_id  = (int)($_POST['doctor_id'] ?? 0);
    $doctor_source = sanitize($_POST['doctor_source'] ?? 'db');
    $doctor_name = sanitize($_POST['doctor_name'] ?? '');
    $specialization = sanitize($_POST['specialization'] ?? '');
    $hospital = sanitize($_POST['hospital'] ?? '');
    $location = sanitize($_POST['location'] ?? '');
    $contact = sanitize($_POST['contact'] ?? '');
    $appt_date  = sanitize($_POST['appointment_date'] ?? '');
    $notes      = sanitize($_POST['notes'] ?? '');

    $resolved_doctor_id = resolveDoctorId($db, $doctor_id, $doctor_source, $doctor_name, $specialization, $hospital, $location, $contact);

    if (!$user_id || !$resolved_doctor_id || !$appt_date) {
        jsonResponse(['success'=>false,'message'=>'user_id, doctor details and appointment_date are required']);
    }

    $stmt = $db->prepare('INSERT INTO appointments (user_id, doctor_id, appointment_date, notes, status, created_at)
                          VALUES (?,?,?,?,"pending",NOW())');
    $stmt->execute([$user_id, $resolved_doctor_id, $appt_date, $notes]);

    jsonResponse(['success'=>true, 'appointment_id'=>(int)$db->lastInsertId(), 'doctor_id'=>$resolved_doctor_id]);
}

if ($_SERVER['REQUEST_METHOD'] === 'PUT') {
    $data  = json_decode(file_get_contents('php://input'), true) ?? [];
    $id     = (int)($data['id'] ?? 0);
    $status = sanitize($data['status'] ?? '');
    if (!$id || !$status) { jsonResponse(['success'=>false,'message'=>'id and status required']); }

    $db->prepare('UPDATE appointments SET status=? WHERE id=?')->execute([$status, $id]);
    jsonResponse(['success'=>true]);
}
