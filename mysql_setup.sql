CREATE DATABASE IF NOT EXISTS student_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE student_portal;

CREATE TABLE IF NOT EXISTS students (
  student_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  course VARCHAR(120) NOT NULL,
  year_of_study TINYINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_results (
  result_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  subject VARCHAR(120) NOT NULL,
  assessment_name VARCHAR(120) NOT NULL,
  marks_obtained DECIMAL(6, 2) NOT NULL,
  total_marks DECIMAL(6, 2) NOT NULL,
  assessment_date DATE NOT NULL,
  CONSTRAINT chk_student_results_marks
    CHECK (marks_obtained >= 0 AND total_marks > 0 AND marks_obtained <= total_marks),
  CONSTRAINT uq_student_assessment
    UNIQUE (student_id, subject, assessment_name),
  CONSTRAINT fk_student_results_student
    FOREIGN KEY (student_id) REFERENCES students (student_id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS portal_accounts (
  account_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'teacher') NOT NULL,
  created_by VARCHAR(80) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO students (full_name, email, course, year_of_study) VALUES
  ('Aarav Sharma', 'aarav.sharma@example.com', 'Computer Science', 2),
  ('Maya Patel', 'maya.patel@example.com', 'Data Analytics', 3),
  ('Noah Williams', 'noah.williams@example.com', 'Business Studies', 1),
  ('Zara Khan', 'zara.khan@example.com', 'Computer Science', 4),
  ('Ethan Chen', 'ethan.chen@example.com', 'Information Systems', 2),
  ('Priya Nair', 'priya.nair@example.com', 'Data Analytics', 1),
  ('Lucas Martin', 'lucas.martin@example.com', 'Business Studies', 3),
  ('Anaya Singh', 'anaya.singh@example.com', 'Information Systems', 4);

INSERT INTO student_results (
  student_id, subject, assessment_name, marks_obtained, total_marks, assessment_date
)
SELECT
  s.student_id,
  demo.subject,
  'Midterm',
  demo.marks_obtained,
  100,
  '2026-03-15'
FROM students AS s
JOIN (
  SELECT 'aarav.sharma@example.com' AS email, 'Programming' AS subject, 88 AS marks_obtained
  UNION ALL SELECT 'aarav.sharma@example.com', 'Databases', 79
  UNION ALL SELECT 'aarav.sharma@example.com', 'Statistics', 84
  UNION ALL SELECT 'aarav.sharma@example.com', 'Mathematics', 72
  UNION ALL SELECT 'maya.patel@example.com', 'Programming', 91
  UNION ALL SELECT 'maya.patel@example.com', 'Databases', 86
  UNION ALL SELECT 'maya.patel@example.com', 'Statistics', 93
  UNION ALL SELECT 'maya.patel@example.com', 'Mathematics', 81
  UNION ALL SELECT 'noah.williams@example.com', 'Programming', 54
  UNION ALL SELECT 'noah.williams@example.com', 'Databases', 62
  UNION ALL SELECT 'noah.williams@example.com', 'Statistics', 48
  UNION ALL SELECT 'noah.williams@example.com', 'Mathematics', 57
  UNION ALL SELECT 'zara.khan@example.com', 'Programming', 96
  UNION ALL SELECT 'zara.khan@example.com', 'Databases', 89
  UNION ALL SELECT 'zara.khan@example.com', 'Statistics', 92
  UNION ALL SELECT 'zara.khan@example.com', 'Mathematics', 87
  UNION ALL SELECT 'ethan.chen@example.com', 'Programming', 73
  UNION ALL SELECT 'ethan.chen@example.com', 'Databases', 81
  UNION ALL SELECT 'ethan.chen@example.com', 'Statistics', 77
  UNION ALL SELECT 'ethan.chen@example.com', 'Mathematics', 69
  UNION ALL SELECT 'priya.nair@example.com', 'Programming', 82
  UNION ALL SELECT 'priya.nair@example.com', 'Databases', 90
  UNION ALL SELECT 'priya.nair@example.com', 'Statistics', 87
  UNION ALL SELECT 'priya.nair@example.com', 'Mathematics', 78
  UNION ALL SELECT 'lucas.martin@example.com', 'Programming', 65
  UNION ALL SELECT 'lucas.martin@example.com', 'Databases', 58
  UNION ALL SELECT 'lucas.martin@example.com', 'Statistics', 71
  UNION ALL SELECT 'lucas.martin@example.com', 'Mathematics', 63
  UNION ALL SELECT 'anaya.singh@example.com', 'Programming', 94
  UNION ALL SELECT 'anaya.singh@example.com', 'Databases', 96
  UNION ALL SELECT 'anaya.singh@example.com', 'Statistics', 91
  UNION ALL SELECT 'anaya.singh@example.com', 'Mathematics', 89
) AS demo ON demo.email = s.email
ON DUPLICATE KEY UPDATE
  marks_obtained = VALUES(marks_obtained),
  total_marks = VALUES(total_marks),
  assessment_date = VALUES(assessment_date);
