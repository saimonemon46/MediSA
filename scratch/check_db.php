<?php
require_once 'backend_php/includes/config.php';
$db = getDB();
$stmt = $db->query("DESCRIBE triage_reports");
$columns = $stmt->fetchAll();
header('Content-Type: application/json');
echo json_encode($columns, JSON_PRETTY_PRINT);
