CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    login TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id UUID PRIMARY KEY,
    group_name TEXT NOT NULL,
    date TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    time_range TEXT NOT NULL,
    teacher TEXT,
    room TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_class
ON classes (group_name, date, subject_name, time_range);

CREATE TABLE IF NOT EXISTS user_class_notes (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    note TEXT,
    PRIMARY KEY (user_id, class_id)
);
