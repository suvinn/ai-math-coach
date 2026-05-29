CREATE TABLE users (
id BIGSERIAL PRIMARY KEY,
email VARCHAR(255) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL,
role VARCHAR(16) NOT NULL DEFAULT 'student' CHECK (role IN ('student','teacher','admin')),
display_name VARCHAR(255),
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE achievement_standards (
id BIGSERIAL PRIMARY KEY,
code VARCHAR(64) UNIQUE,
name VARCHAR(255),
description TEXT,
grade SMALLINT,
semester SMALLINT,
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE detail_types (
id BIGSERIAL PRIMARY KEY,
name VARCHAR(255) UNIQUE NOT NULL,
achievement_standard_id BIGINT REFERENCES achievement_standards(id) ON DELETE SET NULL,
description TEXT,
examples TEXT,
embedding VECTOR(1536),
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE problems (
id BIGSERIAL PRIMARY KEY,
source VARCHAR(128),
content TEXT NOT NULL,
answer_text TEXT,
wrong_choices JSONB,
solution_text TEXT,
difficulty VARCHAR(8) CHECK (difficulty IN ('상','중','하')),
is_multiple_choice BOOLEAN DEFAULT FALSE,
embedding VECTOR(1536),
metadata JSONB,
created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE problem_achievement_standards (
problem_id BIGINT REFERENCES problems(id) ON DELETE CASCADE,
achievement_standard_id BIGINT REFERENCES achievement_standards(id) ON DELETE CASCADE,
primary_flag BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT now(),
PRIMARY KEY (problem_id, achievement_standard_id)
);

CREATE TABLE problem_detail_types (
problem_id BIGINT REFERENCES problems(id) ON DELETE CASCADE,
detail_type_id BIGINT REFERENCES detail_types(id) ON DELETE CASCADE,
primary_flag BOOLEAN DEFAULT FALSE,
created_at TIMESTAMPTZ DEFAULT now(),
PRIMARY KEY (problem_id, detail_type_id)
);

CREATE TABLE solve_records (
id BIGSERIAL PRIMARY KEY,
student_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
problem_id BIGINT REFERENCES problems(id) ON DELETE CASCADE,
student_answer TEXT,
is_correct BOOLEAN NOT NULL,
solve_time_sec INTEGER,
created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_solve_records_student_created ON solve_records(student_id, created_at DESC);
CREATE INDEX idx_solve_records_problem ON solve_records(problem_id);

CREATE TABLE student_weak_types (
id BIGSERIAL PRIMARY KEY,
student_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
detail_type_id BIGINT REFERENCES detail_types(id) ON DELETE CASCADE,
weakness_score NUMERIC(5,4) NOT NULL CHECK (weakness_score >= 0 AND weakness_score <= 1),
total_attempts INTEGER DEFAULT 0,
wrong_attempts INTEGER DEFAULT 0,
last_wrong_at TIMESTAMPTZ,
updated_at TIMESTAMPTZ DEFAULT now(),
UNIQUE (student_id, detail_type_id)
);
CREATE INDEX idx_weak_types_student_score ON student_weak_types(student_id, weakness_score DESC);

CREATE TABLE recommendation_runs (
id BIGSERIAL PRIMARY KEY,
student_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
trigger_solve_record_id BIGINT REFERENCES solve_records(id) ON DELETE SET NULL,
weak_detail_type_ids INT[],
ai_feedback TEXT,
model_name VARCHAR(128),
prompt_tokens INTEGER,
completion_tokens INTEGER,
latency_ms INTEGER,
created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_reco_runs_student_created ON recommendation_runs(student_id, created_at DESC);

CREATE TABLE recommendation_items (
id BIGSERIAL PRIMARY KEY,
recommendation_run_id BIGINT REFERENCES recommendation_runs(id) ON DELETE CASCADE,
detail_type_id BIGINT REFERENCES detail_types(id) ON DELETE SET NULL,
problem_id BIGINT REFERENCES problems(id) ON DELETE RESTRICT,
rank SMALLINT,
similarity_score NUMERIC(6,4),
reason TEXT,
created_at TIMESTAMPTZ DEFAULT now(),
UNIQUE (recommendation_run_id, problem_id)
);
CREATE INDEX idx_reco_items_run_rank ON recommendation_items(recommendation_run_id, rank);


CREATE TABLE llm_call_logs (
id BIGSERIAL PRIMARY KEY,
run_type VARCHAR(64),
request_payload JSONB,
response_payload JSONB,
model_name VARCHAR(128),
tokens_prompt INTEGER,
tokens_completion INTEGER,
latency_ms INTEGER,
created_at TIMESTAMPTZ DEFAULT now()
);