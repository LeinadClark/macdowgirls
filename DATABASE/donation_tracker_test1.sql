-- 1. DATABASE INITIALIZATION
CREATE DATABASE IF NOT EXISTS HelpersOfGod_DB;
USE HelpersOfGod_DB;

-- 2. TABLES
-- Users Table: Adjusted for Student C (PHP CRUD) and Student B (Python/RFID)
CREATE TABLE Users (
    user_id CHAR(36) PRIMARY KEY, -- Use UUID for unique identification
    rfid_tag VARCHAR(50) UNIQUE DEFAULT NULL, -- Field for Student B's RFID Listener
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin', 'donor') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initiatives (Missions) Table
CREATE TABLE Initiatives (
    initiative_id CHAR(36) PRIMARY KEY,
    creator_id CHAR(36),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category ENUM('research', 'outreach', 'conservation', 'scholarship') NOT NULL,
    target_amount DECIMAL(15, 2) NOT NULL,
    current_amount DECIMAL(15, 2) DEFAULT 0.00,
    status ENUM('draft', 'active', 'completed', 'cancelled') DEFAULT 'draft',
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- Donations (Offerings) Table
CREATE TABLE Donations (
    donation_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    donor_id CHAR(36), -- Nullable for anonymous or RFID-based giving
    amount DECIMAL(15, 2) NOT NULL,
    transaction_ref VARCHAR(100) UNIQUE NOT NULL,
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE,
    FOREIGN KEY (donor_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- Milestones Table
CREATE TABLE Milestones (
    milestone_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE
);

-- Updates Table
CREATE TABLE Updates (
    update_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    content TEXT NOT NULL,
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE
);

-- 3. TRANSACTION LOGIC (STORED PROCEDURE)
-- This is what Student B (Python) and Student C (PHP) will call to ensure ACID compliance.
DELIMITER //
CREATE PROCEDURE ProcessDonation(
    IN p_donation_id CHAR(36),
    IN p_initiative_id CHAR(36),
    IN p_donor_id CHAR(36),
    IN p_amount DECIMAL(15, 2),
    IN p_txn_ref VARCHAR(100)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Gift Failed';
    END;

    -- BEGIN TRANSACTION (Lock Database Rows)
    START TRANSACTION;

    -- STEP 1: INSERT - Add Record to 'Donations' Table
    INSERT INTO Donations (donation_id, initiative_id, donor_id, amount, transaction_ref, status)
    VALUES (p_donation_id, p_initiative_id, p_donor_id, p_amount, p_txn_ref, 'success');

    -- STEP 2: UPDATE - Add Amount to Initiative Total
    UPDATE Initiatives
    SET current_amount = current_amount + p_amount
    WHERE initiative_id = p_initiative_id;

    -- COMMIT (Save permanently) - error check is implicit via HANDLER above
    COMMIT;

    -- POST-COMMIT: Goal met? (outside transaction, no rollback risk)
    UPDATE Initiatives
    SET status = 'completed'
    WHERE initiative_id = p_initiative_id
    AND current_amount >= target_amount;

END //
DELIMITER ;

-- 4. SAMPLE DATA
INSERT INTO Users (user_id, rfid_tag, full_name, email, password_hash, role) VALUES
('u1', 'RFID_ABC123', 'Nicole Liwag', 'nliway@uphsd.edu', 'hash123', 'student'),
('u2', NULL, 'Dr. Roberto Malitao', 'rmalitao@uphsd.edu', 'hash456', 'faculty'),
('u3', 'RFID_XYZ789', 'Lance Jarred', 'ljarred@gmail.com', 'hash789', 'donor');

INSERT INTO Initiatives (initiative_id, creator_id, title, description, category, target_amount, status) VALUES
('i1', 'u1', 'Mangrove Conservation 2026', 'Restoring local coastal areas.', 'conservation', 5000.00, 'active');