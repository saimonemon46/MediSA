-- MediAI Migration: Add image_path column to triage_reports table
-- This stores the uploaded symptom image path for saved triage reports

ALTER TABLE `triage_reports`
  ADD COLUMN `image_path` VARCHAR(255) NULL AFTER `image_analysis`;

-- Create index for faster lookup if needed
CREATE INDEX `idx_report_image_path` ON `triage_reports` (`image_path`);
