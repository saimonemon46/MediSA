<?php
require_once 'backend_php/includes/config.php';
$db = getDB();
$stmt = $db->query("SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = 'mediai_db' AND TABLE_NAME = 'triage_reports' AND REFERENCED_TABLE_NAME IS NOT NULL");
$fks = $stmt->fetchAll();
header('Content-Type: application/json');
echo json_encode($fks, JSON_PRETTY_PRINT);
