-- ============================================================
-- Database: helpersofgod_db with Suggestion & Signature Logic
-- ============================================================
DROP DATABASE IF EXISTS `helpersofgod_db`;
CREATE DATABASE `helpersofgod_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `helpersofgod_db`;

-- ============================================================
-- Tables
-- ============================================================

-- Users table (unchanged)
CREATE TABLE `users` (
  `user_id`       char(36)     NOT NULL,
  `rfid_tag`      varchar(50)  DEFAULT NULL,
  `full_name`     varchar(255) NOT NULL,
  `email`         varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role`          enum('student','faculty','admin','donor') NOT NULL,
  `created_at`    timestamp    NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `rfid_tag` (`rfid_tag`)
);

-- Initiatives table (unchanged)
CREATE TABLE `initiatives` (
  `initiative_id`  char(36)      NOT NULL,
  `creator_id`     char(36)      DEFAULT NULL,
  `title`          varchar(255)  NOT NULL,
  `description`    text          DEFAULT NULL,
  `category`       enum('research','outreach','conservation','scholarship') NOT NULL,
  `target_amount`  decimal(15,2) NOT NULL,
  `current_amount` decimal(15,2) DEFAULT 0.00,
  `status`         enum('draft','active','completed','cancelled') DEFAULT 'draft',
  `start_date`     date          DEFAULT NULL,
  `end_date`       date          DEFAULT NULL,
  `created_at`     timestamp     NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`initiative_id`),
  KEY `creator_id` (`creator_id`),
  CONSTRAINT `initiatives_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
);

-- Donations table (unchanged)
CREATE TABLE `donations` (
  `donation_id`     char(36)      NOT NULL,
  `initiative_id`   char(36)      DEFAULT NULL,
  `donor_id`        char(36)      DEFAULT NULL,
  `amount`          decimal(15,2) NOT NULL,
  `transaction_ref` varchar(100)  NOT NULL,
  `status`          enum('pending','success','failed') DEFAULT 'pending',
  `anonymous`       tinyint(1)    NOT NULL DEFAULT 0,
  `payment_method`  varchar(50)   DEFAULT 'GCash',
  `created_at`      timestamp     NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`donation_id`),
  UNIQUE KEY `transaction_ref` (`transaction_ref`),
  KEY `initiative_id` (`initiative_id`),
  KEY `donor_id` (`donor_id`),
  CONSTRAINT `donations_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE,
  CONSTRAINT `donations_ibfk_2` FOREIGN KEY (`donor_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
);

-- Milestones table (unchanged)
CREATE TABLE `milestones` (
  `milestone_id`  char(36)     NOT NULL,
  `initiative_id` char(36)     DEFAULT NULL,
  `title`         varchar(255) NOT NULL,
  `description`   text         DEFAULT NULL,
  `is_completed`  tinyint(1)   DEFAULT 0,
  PRIMARY KEY (`milestone_id`),
  KEY `initiative_id` (`initiative_id`),
  CONSTRAINT `milestones_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE
);

-- Updates table (unchanged)
CREATE TABLE `updates` (
  `update_id`     char(36)     NOT NULL,
  `initiative_id` char(36)     DEFAULT NULL,
  `content`       text         NOT NULL,
  `image_url`     varchar(255) DEFAULT NULL,
  `created_at`    timestamp    NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`update_id`),
  KEY `initiative_id` (`initiative_id`),
  CONSTRAINT `updates_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE
);

-- Campaign Suggestions table (modified to support signatures threshold)
CREATE TABLE `campaign_suggestions` (
  `suggestion_id`       char(36)     NOT NULL,
  `user_id`             char(36)     DEFAULT NULL,
  `full_name`           varchar(255) NOT NULL,
  `email`               varchar(255) NOT NULL,
  `title`               varchar(255) NOT NULL,
  `description`         text         NOT NULL,
  `category`            enum('research','outreach','conservation','scholarship') NOT NULL,
  `target_amount`       decimal(15,2) NOT NULL,
  `required_signatures` int(11)      NOT NULL DEFAULT 100,
  `signature_count`     int(11)      NOT NULL DEFAULT 0,
  `status`              enum('pending','threshold_met','approved','rejected') DEFAULT 'pending',
  `admin_notes`         text         DEFAULT NULL,
  `created_at`          timestamp    NOT NULL DEFAULT current_timestamp(),
  `reviewed_at`         timestamp    NULL DEFAULT NULL,
  PRIMARY KEY (`suggestion_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `campaign_suggestions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
);

-- Petition Signatures table (linked to suggestions)
CREATE TABLE `petition_signatures` (
  `signature_id` char(36)     NOT NULL,
  `suggestion_id` char(36)   NOT NULL,
  `full_name`    varchar(255) NOT NULL,
  `email`        varchar(255) NOT NULL,
  `role`         enum('student','faculty','alumni','community') NOT NULL DEFAULT 'student',
  `message`      text         DEFAULT NULL,
  `created_at`   timestamp    NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`signature_id`),
  UNIQUE KEY `unique_signature_per_suggestion` (`suggestion_id`, `email`),
  CONSTRAINT `fk_signature_suggestion` FOREIGN KEY (`suggestion_id`) REFERENCES `campaign_suggestions` (`suggestion_id`) ON DELETE CASCADE
);

-- ============================================================
-- Triggers to maintain signature_count and auto-update status
-- ============================================================
DELIMITER $$

-- After insert signature: increment count, set threshold_met if reached
CREATE TRIGGER after_petition_signature_insert
AFTER INSERT ON petition_signatures
FOR EACH ROW
BEGIN
    UPDATE campaign_suggestions
    SET signature_count = signature_count + 1
    WHERE suggestion_id = NEW.suggestion_id
      AND status IN ('pending', 'threshold_met');

    UPDATE campaign_suggestions
    SET status = 'threshold_met'
    WHERE suggestion_id = NEW.suggestion_id
      AND signature_count >= required_signatures
      AND status = 'pending';
END$$

-- After delete signature: decrement count, revert status if below threshold
CREATE TRIGGER after_petition_signature_delete
AFTER DELETE ON petition_signatures
FOR EACH ROW
BEGIN
    UPDATE campaign_suggestions
    SET signature_count = signature_count - 1
    WHERE suggestion_id = OLD.suggestion_id;

    UPDATE campaign_suggestions
    SET status = 'pending'
    WHERE suggestion_id = OLD.suggestion_id
      AND signature_count < required_signatures
      AND status = 'threshold_met';
END$$

-- Prevent signing if suggestion already approved or rejected
CREATE TRIGGER before_petition_signature_insert
BEFORE INSERT ON petition_signatures
FOR EACH ROW
BEGIN
    DECLARE suggestion_status VARCHAR(20);
    SELECT status INTO suggestion_status
    FROM campaign_suggestions
    WHERE suggestion_id = NEW.suggestion_id;
    IF suggestion_status IN ('approved', 'rejected') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot sign: suggestion already approved or rejected';
    END IF;
END$$

DELIMITER ;

-- ============================================================
-- Stored Procedure: Admin approves suggestion -> becomes Initiative
-- ============================================================
DELIMITER $$

CREATE PROCEDURE ApproveSuggestion(
    IN p_suggestion_id CHAR(36),
    IN p_admin_notes   TEXT,
    IN p_start_date    DATE,
    IN p_end_date      DATE
)
BEGIN
    DECLARE v_suggestion_status ENUM('pending','threshold_met','approved','rejected');
    DECLARE v_title VARCHAR(255);
    DECLARE v_description TEXT;
    DECLARE v_category ENUM('research','outreach','conservation','scholarship');
    DECLARE v_target_amount DECIMAL(15,2);
    DECLARE v_user_id CHAR(36);
    DECLARE v_initiative_id CHAR(36);

    -- Lock the suggestion row
    SELECT status, title, description, category, target_amount, user_id
    INTO v_suggestion_status, v_title, v_description, v_category, v_target_amount, v_user_id
    FROM campaign_suggestions
    WHERE suggestion_id = p_suggestion_id
    FOR UPDATE;

    -- Validate status
    IF v_suggestion_status NOT IN ('pending', 'threshold_met') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Suggestion cannot be approved (wrong status)';
    END IF;

    -- Double-check signature count
    IF (SELECT signature_count FROM campaign_suggestions WHERE suggestion_id = p_suggestion_id) <
       (SELECT required_signatures FROM campaign_suggestions WHERE suggestion_id = p_suggestion_id) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Insufficient signatures to approve this suggestion';
    END IF;

    -- Create new initiative
    SET v_initiative_id = UUID();
    INSERT INTO initiatives (
        initiative_id, creator_id, title, description, category,
        target_amount, current_amount, status, start_date, end_date
    ) VALUES (
        v_initiative_id, v_user_id, v_title, v_description, v_category,
        v_target_amount, 0.00, 'draft',
        IFNULL(p_start_date, CURDATE()),
        IFNULL(p_end_date, DATE_ADD(CURDATE(), INTERVAL 1 YEAR))
    );

    -- Mark suggestion as approved
    UPDATE campaign_suggestions
    SET status = 'approved',
        admin_notes = p_admin_notes,
        reviewed_at = NOW()
    WHERE suggestion_id = p_suggestion_id;

    -- Return the new initiative ID
    SELECT v_initiative_id AS new_initiative_id;
END$$

DELIMITER ;

-- ============================================================
-- Stored Procedure: Process Donation (original, kept for reference)
-- ============================================================
DELIMITER $$

CREATE PROCEDURE ProcessDonation (
    IN p_donation_id   CHAR(36),
    IN p_initiative_id CHAR(36),
    IN p_donor_id      CHAR(36),
    IN p_amount        DECIMAL(15,2),
    IN p_txn_ref       VARCHAR(100)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Gift Failed';
    END;

    START TRANSACTION;

    INSERT INTO Donations (donation_id, initiative_id, donor_id, amount, transaction_ref, status)
    VALUES (p_donation_id, p_initiative_id, p_donor_id, p_amount, p_txn_ref, 'pending');

    UPDATE Initiatives
    SET current_amount = current_amount + p_amount
    WHERE initiative_id = p_initiative_id;

    COMMIT;

    -- Goal met check
    UPDATE Initiatives
    SET status = 'completed'
    WHERE initiative_id = p_initiative_id
      AND current_amount >= target_amount;
END$$

DELIMITER ;

-- ============================================================
-- Sample Data (original + demonstration of suggestion & signatures)
-- ============================================================

-- Sample user (admin and regular user)
INSERT INTO `users` (`user_id`, `rfid_tag`, `full_name`, `email`, `password_hash`, `role`, `created_at`) VALUES
('476860d3-0a04-4742-a985-56e8849ca9e1', NULL, 'Jocelyn Baylon', 'jocelynbaylon48@gmail.com', 'baylon', 'student', NOW()),
('admin-001', NULL, 'Admin User', 'admin@uphsl.edu.ph', 'admin123', 'admin', NOW());

-- Sample initiatives (original)
INSERT INTO `initiatives` (`initiative_id`, `creator_id`, `title`, `description`, `category`, `target_amount`, `current_amount`, `status`, `start_date`, `end_date`, `created_at`) VALUES
('348048fc-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Kumpas Kalye: Street Music for a Cause', 'outreach campaign', 'outreach', 100000.00, 46000.00, 'active', '2026-01-01', '2026-12-31', NOW()),
('34808752-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Project Dunong: CS Research Lab Upgrade', 'research campaign', 'research', 150000.00, 121000.00, 'active', '2026-01-01', '2026-12-31', NOW()),
('34808ae7-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Perpetualite High Honors Scholarship', 'scholarship campaign', 'scholarship', 200000.00, 200000.00, 'active', '2026-01-01', '2026-12-31', NOW()),
('34808ca0-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Green Campus: Molino Conservation', 'conservation campaign', 'conservation', 50000.00, 15000.00, 'active', '2026-01-01', '2026-12-31', NOW());

-- Sample donations (original)
INSERT INTO `donations` (`donation_id`, `initiative_id`, `donor_id`, `amount`, `transaction_ref`, `status`, `anonymous`, `payment_method`, `created_at`) VALUES
('21e2117b-7479-4f1b-8c9c-c9c26f7a86fc', '34808752-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 1000.00, 'TXN-AFBEF82B', 'success', 0, 'GCash', NOW()),
('79bfadeb-c6cd-4dc5-b1e1-ab4ee729a47c', '348048fc-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 1000.00, 'TXN-A62580FB', 'success', 0, 'GCash', NOW());

-- -----------------------------------------------------
-- Demonstration: A campaign suggestion and signatures
-- -----------------------------------------------------

-- 1. User submits a suggestion (needs 3 signatures for quick demo)
INSERT INTO `campaign_suggestions` (
    `suggestion_id`, `user_id`, `full_name`, `email`, `title`, `description`,
    `category`, `target_amount`, `required_signatures`, `status`
) VALUES (
    UUID(), '476860d3-0a04-4742-a985-56e8849ca9e1', 'Jocelyn Baylon',
    'jocelynbaylon48@gmail.com', 'New Library Computers',
    'Upgrade the CS lab with 20 new high-performance PCs',
    'research', 250000.00, 3, 'pending'
);

-- Get the suggestion_id from above (replace with actual UUID if running manually)
SET @suggestion_id = (SELECT suggestion_id FROM campaign_suggestions WHERE title = 'New Library Computers' LIMIT 1);

-- 2. Three people sign the petition
INSERT INTO `petition_signatures` (`signature_id`, `suggestion_id`, `full_name`, `email`, `role`) VALUES
(UUID(), @suggestion_id, 'Alice Student', 'alice@uphsl.edu.ph', 'student'),
(UUID(), @suggestion_id, 'Bob Faculty', 'bob@uphsl.edu.ph', 'faculty'),
(UUID(), @suggestion_id, 'Charlie Alumni', 'charlie@example.com', 'alumni');

-- After the third signature, the suggestion's status becomes 'threshold_met' automatically.
-- Admin can now call the ApproveSuggestion procedure.

-- Example approval (uncomment to test):
-- CALL ApproveSuggestion(@suggestion_id, 'Great idea, approved!', '2026-06-01', '2027-05-31');

-- ============================================================
-- End of SQL script
-- ============================================================