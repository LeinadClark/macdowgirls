-- 1. DATABASE INITIALIZATION
CREATE DATABASE IF NOT EXISTS HelpersOfGod_DB;
USE HelpersOfGod_DB;

-- 2. TABLES

CREATE TABLE Users (
    user_id CHAR(36) PRIMARY KEY,
    rfid_tag VARCHAR(50) UNIQUE DEFAULT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin', 'donor') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE Donations (
    donation_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    donor_id CHAR(36),
    amount DECIMAL(15, 2) NOT NULL,
    transaction_ref VARCHAR(100) UNIQUE NOT NULL,
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE,
    FOREIGN KEY (donor_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

CREATE TABLE Milestones (
    milestone_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE
);

CREATE TABLE Updates (
    update_id CHAR(36) PRIMARY KEY,
    initiative_id CHAR(36),
    content TEXT NOT NULL,
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiative_id) REFERENCES Initiatives(initiative_id) ON DELETE CASCADE
);

-- 3. TRANSACTION LOGIC (STORED PROCEDURE)

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

    START TRANSACTION;

    INSERT INTO Donations (donation_id, initiative_id, donor_id, amount, transaction_ref, status)
    VALUES (p_donation_id, p_initiative_id, p_donor_id, p_amount, p_txn_ref, 'success');

    UPDATE Initiatives
    SET current_amount = current_amount + p_amount
    WHERE initiative_id = p_initiative_id;

    COMMIT;

    -- POST-COMMIT: Goal met check (outside transaction per diagram)
    UPDATE Initiatives
    SET status = 'completed'
    WHERE initiative_id = p_initiative_id
    AND current_amount >= target_amount;

END //
DELIMITER ;