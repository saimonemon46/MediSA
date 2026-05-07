<?php
// MediAI — Auth: Register
require_once '../includes/config.php';

header('Access-Control-Allow-Origin: *');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { jsonResponse(['success'=>false,'message'=>'Method not allowed'], 405); }

$first_name = sanitize($_POST['first_name'] ?? '');
$last_name  = sanitize($_POST['last_name'] ?? '');
$email      = filter_var(trim($_POST['email'] ?? ''), FILTER_VALIDATE_EMAIL);
$phone      = sanitize($_POST['phone'] ?? '');
$dob        = sanitize($_POST['dob'] ?? '');
$password   = $_POST['password'] ?? '';

if (!$first_name || !$last_name || !$email || !$password) {
    jsonResponse(['success'=>false,'message'=>'All required fields must be filled.']);
}
if (strlen($password) < 8) {
    jsonResponse(['success'=>false,'message'=>'Password must be at least 8 characters.']);
}

$db = getDB();

// Check duplicate
$stmt = $db->prepare('SELECT id FROM users WHERE email = ?');
$stmt->execute([$email]);
if ($stmt->fetch()) {
    jsonResponse(['success'=>false,'message'=>'An account with this email already exists.']);
}

$hash = password_hash($password, PASSWORD_BCRYPT);
$stmt = $db->prepare('INSERT INTO users (first_name, last_name, email, phone, dob, password_hash, role, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, "patient", NOW())');
$stmt->execute([$first_name, $last_name, $email, $phone, $dob ?: null, $hash]);
$userId = (int)$db->lastInsertId();

// Create health profile
$db->prepare('INSERT INTO health_profiles (user_id, created_at) VALUES (?, NOW())')->execute([$userId]);

jsonResponse([
    'success' => true,
    'user' => [
        'id'         => $userId,
        'first_name' => $first_name,
        'last_name'  => $last_name,
        'email'      => $email,
        'role'       => 'patient'
    ]
]);
