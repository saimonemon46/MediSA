<?php
// MediAI — API: Triage Reports
require_once '../includes/config.php';

header('Access-Control-Allow-Origin: *');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$db = getDB();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $user_id = (int)($_GET['user_id'] ?? 0);
    if (!$user_id) { jsonResponse(['success'=>false,'message'=>'user_id required']); }

    $stmt = $db->prepare('SELECT * FROM triage_reports WHERE user_id = ? ORDER BY created_at DESC');
    $stmt->execute([$user_id]);
    $reports = $stmt->fetchAll();

    foreach ($reports as &$r) {
        $r['symptoms_listed'] = json_decode($r['symptoms_listed'] ?? '[]', true);
    }

    jsonResponse(['success'=>true, 'reports'=>$reports]);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $data = json_decode(file_get_contents('php://input'), true) ?? $_POST;
    $user_id   = (int)($data['user_id'] ?? 0);
    $session_id = (int)($data['session_id'] ?? 0);
    $condition  = sanitize($data['possible_condition'] ?? '');
    $urgency    = sanitize($data['urgency'] ?? 'medium');
    $specialist = sanitize($data['recommended_specialist'] ?? '');
    $reasoning  = sanitize($data['reasoning'] ?? '');
    $guidance   = sanitize($data['guidance'] ?? '');
    $explanation = sanitize($data['explanation'] ?? '');
    $symptoms   = json_encode($data['symptoms_listed'] ?? []);

    if (!$user_id || !$condition) { jsonResponse(['success'=>false,'message'=>'Missing required fields']); }

    $stmt = $db->prepare('INSERT INTO triage_reports
        (user_id, session_id, possible_condition, urgency, recommended_specialist, reasoning, guidance, explanation, symptoms_listed, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,NOW())');
    $stmt->execute([$user_id, $session_id ?: null, $condition, $urgency, $specialist, $reasoning, $guidance, $explanation, $symptoms]);

    jsonResponse(['success'=>true, 'report_id'=>(int)$db->lastInsertId()]);
}
