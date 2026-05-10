-- MediAI Migration: Add image_analysis column to triage_reports table
-- This allows storing LLM-based image analysis results with triage reports

ALTER TABLE `triage_reports` ADD COLUMN `image_analysis` LONGTEXT NULL AFTER `explanation`;

-- Create index for faster queries
CREATE INDEX `idx_image_analysis` ON `triage_reports` (`id`);
