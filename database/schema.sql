-- ============================================================
-- MediAI / MediSA — Complete Database Schema & Seed Data
-- ============================================================

CREATE DATABASE IF NOT EXISTS `mediai_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `mediai_db`;

-- ------------------------------------------------------------
-- Table: users
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `health_profiles`;
DROP TABLE IF EXISTS `medication_schedule`;
DROP TABLE IF EXISTS `medical_documents`;
DROP TABLE IF EXISTS `appointments`;
DROP TABLE IF EXISTS `triage_reports`;
DROP TABLE IF EXISTS `symptom_sessions`;
DROP TABLE IF EXISTS `doctors`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(191) NOT NULL UNIQUE,
  `phone` VARCHAR(50) DEFAULT NULL,
  `dob` DATE DEFAULT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('patient', 'doctor', 'admin') NOT NULL DEFAULT 'patient',
  `last_login` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: health_profiles
-- ------------------------------------------------------------
CREATE TABLE `health_profiles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `blood_group` VARCHAR(10) DEFAULT NULL,
  `allergies` TEXT DEFAULT NULL,
  `chronic_conditions` TEXT DEFAULT NULL,
  `emergency_contact` VARCHAR(100) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_health_profiles_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: symptom_sessions
-- ------------------------------------------------------------
CREATE TABLE `symptom_sessions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `session_id` VARCHAR(64) NOT NULL,
  `primary_symptom` TEXT DEFAULT NULL,
  `status` VARCHAR(50) NOT NULL DEFAULT 'completed',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_sessions_user` (`user_id`),
  INDEX `idx_sessions_session_id` (`session_id`),
  CONSTRAINT `fk_symptom_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: triage_reports
-- ------------------------------------------------------------
CREATE TABLE `triage_reports` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `session_id` VARCHAR(64) DEFAULT NULL,
  `possible_condition` VARCHAR(255) NOT NULL,
  `urgency` VARCHAR(50) NOT NULL DEFAULT 'medium',
  `recommended_specialist` VARCHAR(100) DEFAULT NULL,
  `reasoning` TEXT DEFAULT NULL,
  `guidance` TEXT DEFAULT NULL,
  `explanation` TEXT DEFAULT NULL,
  `image_analysis` LONGTEXT DEFAULT NULL,
  `image_path` VARCHAR(255) DEFAULT NULL,
  `symptoms_listed` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_reports_user` (`user_id`),
  INDEX `idx_reports_session` (`session_id`),
  INDEX `idx_reports_image_path` (`image_path`),
  CONSTRAINT `fk_triage_reports_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: doctors
-- ------------------------------------------------------------
CREATE TABLE `doctors` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `doctor_name` VARCHAR(150) NOT NULL,
  `specialization` VARCHAR(100) NOT NULL,
  `hospital` VARCHAR(150) DEFAULT NULL,
  `location` VARCHAR(100) DEFAULT NULL,
  `availability` VARCHAR(100) DEFAULT NULL,
  `education` VARCHAR(255) DEFAULT NULL,
  `experience` VARCHAR(50) DEFAULT NULL,
  `contact` VARCHAR(100) DEFAULT NULL,
  `bio` TEXT DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_doctors_specialization` (`specialization`),
  INDEX `idx_doctors_location` (`location`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: appointments
-- ------------------------------------------------------------
CREATE TABLE `appointments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `doctor_id` INT NOT NULL,
  `appointment_date` DATETIME NOT NULL,
  `notes` TEXT DEFAULT NULL,
  `status` ENUM('pending', 'confirmed', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_appointments_user` (`user_id`),
  INDEX `idx_appointments_doctor` (`doctor_id`),
  CONSTRAINT `fk_appointments_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_appointments_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctors` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: medical_documents
-- ------------------------------------------------------------
CREATE TABLE `medical_documents` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `original_name` VARCHAR(255) NOT NULL,
  `stored_name` VARCHAR(255) NOT NULL,
  `file_path` VARCHAR(255) NOT NULL,
  `document_type` VARCHAR(100) NOT NULL DEFAULT 'Medical Document',
  `file_size` INT NOT NULL,
  `mime_type` VARCHAR(100) NOT NULL,
  `ai_analysis` LONGTEXT DEFAULT NULL,
  `uploaded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_documents_user` (`user_id`),
  CONSTRAINT `fk_medical_documents_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Table: medication_schedule
-- ------------------------------------------------------------
CREATE TABLE `medication_schedule` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `document_id` INT DEFAULT NULL,
  `medicine_name` VARCHAR(150) NOT NULL,
  `dosage` VARCHAR(100) DEFAULT NULL,
  `frequency` VARCHAR(50) NOT NULL DEFAULT 'once_daily',
  `start_date` DATE NOT NULL,
  `end_date` DATE DEFAULT NULL,
  `instructions` TEXT DEFAULT NULL,
  `active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_medications_user` (`user_id`),
  CONSTRAINT `fk_medications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_medications_document` FOREIGN KEY (`document_id`) REFERENCES `medical_documents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Seed Data
-- ------------------------------------------------------------

-- Demo User: password is "password123"
INSERT INTO `users` (`id`, `first_name`, `last_name`, `email`, `phone`, `dob`, `password_hash`, `role`, `created_at`) VALUES
(1, 'John', 'Doe', 'john.doe@example.com', '+8801712345678', '1990-05-15', '$2y$12$jerZNhOhc5B81/DVUJLxve4aJk54G8Khdpnnm.PI4rrLBt5GNh6Vq', 'patient', NOW()),
(2, 'Sarah', 'Rahman', 'sarah.rahman@example.com', '+8801812345678', '1985-08-22', '$2y$12$jerZNhOhc5B81/DVUJLxve4aJk54G8Khdpnnm.PI4rrLBt5GNh6Vq', 'patient', NOW());

INSERT INTO `health_profiles` (`user_id`, `blood_group`, `allergies`, `chronic_conditions`, `emergency_contact`, `created_at`) VALUES
(1, 'O+', 'Penicillin, Dust', 'Mild Asthma', '+8801799887766', NOW()),
(2, 'B+', 'None', 'None', '+8801899887766', NOW());

INSERT INTO `doctors` (`id`, `doctor_name`, `specialization`, `hospital`, `location`, `availability`, `education`, `experience`, `contact`, `bio`, `is_active`) VALUES
(1, 'Dr. Rahim Ahmed', 'Cardiologist', 'Dhaka Medical College Hospital', 'Dhaka', 'Mon-Fri 10:00 AM - 2:00 PM', 'MBBS, FCPS (Cardiology)', '12 years', '+8801711111111', 'Senior consultant in cardiovascular diseases and interventional cardiology.', 1),
(2, 'Dr. Nasrin Islam', 'Medicine Specialist', 'Square Hospital', 'Dhaka', 'Sun-Thu 4:00 PM - 8:00 PM', 'MBBS, MD (Internal Medicine)', '10 years', '+8801722222222', 'Specialist in complex internal medicine, infectious diseases, and diabetes care.', 1),
(3, 'Dr. Karim Hossain', 'Neurologist', 'BIRDEM General Hospital', 'Dhaka', 'Mon-Wed 3:00 PM - 7:00 PM', 'MBBS, FCPS (Neurology)', '15 years', '+8801733333333', 'Expert in migraine management, stroke recovery, and neuropathy.', 1),
(4, 'Dr. Fatema Begum', 'Pediatrician', 'Dhaka Shishu Hospital', 'Dhaka', 'Sat-Thu 9:00 AM - 1:00 PM', 'MBBS, DCH, FCPS (Pediatrics)', '8 years', '+8801744444444', 'Dedicated pediatrician specializing in neonatal and child health care.', 1),
(5, 'Dr. Arif Siddiqui', 'Dermatologist', 'Evercare Hospital Dhaka', 'Dhaka', 'Mon-Sat 5:00 PM - 9:00 PM', 'MBBS, DDV, FCPS (Dermatology)', '11 years', '+8801755555555', 'Specializes in allergy testing, inflammatory skin diseases, and dermatologic surgery.', 1),
(6, 'Dr. Tariq Rahman', 'Gastroenterologist', 'Labaid Specialized Hospital', 'Dhaka', 'Mon-Thu 2:00 PM - 6:00 PM', 'MBBS, MD (Gastroenterology)', '14 years', '+8801766666666', 'Consultant in gastrointestinal disorders, endoscopy, and liver pathology.', 1);

INSERT INTO `symptom_sessions` (`user_id`, `session_id`, `primary_symptom`, `status`, `created_at`) VALUES
(1, 'SESS-DEMO-001', 'High fever, persistent headache, and body aches', 'completed', DATE_SUB(NOW(), INTERVAL 3 DAY)),
(1, 'SESS-DEMO-002', 'Mild skin rash on left forearm', 'completed', DATE_SUB(NOW(), INTERVAL 1 DAY));

INSERT INTO `triage_reports` (`user_id`, `session_id`, `possible_condition`, `urgency`, `recommended_specialist`, `reasoning`, `guidance`, `explanation`, `symptoms_listed`, `created_at`) VALUES
(1, 'SESS-DEMO-001', 'Viral Syndrome / Probable Dengue', 'medium', 'Medicine Specialist', 'Symptoms of acute high fever, retro-orbital headache, and generalized body aches during monsoon season in Dhaka strongly match viral exanthem / Dengue fever.', 'Stay well hydrated with oral rehydration solution. Monitor platelet count if fever persists beyond 3 days. Avoid NSAIDs like ibuprofen; use paracetamol for fever.', 'Your reported symptoms indicate a systemic viral infection. Please consult a physician and get a complete blood count (CBC) test.', '["High fever", "Persistent headache", "Body aches"]', DATE_SUB(NOW(), INTERVAL 3 DAY));

INSERT INTO `appointments` (`user_id`, `doctor_id`, `appointment_date`, `notes`, `status`, `created_at`) VALUES
(1, 2, DATE_ADD(NOW(), INTERVAL 2 DAY), 'Follow-up consultation for persistent viral fever and lab review.', 'confirmed', NOW());

INSERT INTO `medication_schedule` (`user_id`, `medicine_name`, `dosage`, `frequency`, `start_date`, `end_date`, `instructions`, `active`, `created_at`) VALUES
(1, 'Paracetamol', '500mg', 'three_times', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'Take after meals for fever relief. Maximum 3000mg/day.', 1, NOW()),
(1, 'Oral Rehydration Salts (ORS)', '1 sachet in 500ml water', 'as_needed', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'Sip continuously throughout the day for electrolyte replenishment.', 1, NOW());
