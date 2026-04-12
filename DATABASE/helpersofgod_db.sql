-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Apr 12, 2026 at 10:37 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `helpersofgod_db` and setup
--
DROP DATABASE IF EXISTS `helpersofgod_db`;
CREATE DATABASE `helpersofgod_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `helpersofgod_db`;

DELIMITER $$
--
-- Procedures
--
-- Removed DEFINER for portability
CREATE PROCEDURE `ProcessDonation` (IN `p_donation_id` CHAR(36), IN `p_initiative_id` CHAR(36), IN `p_donor_id` CHAR(36), IN `p_amount` DECIMAL(15,2), IN `p_txn_ref` VARCHAR(100))   BEGIN
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

END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `donations`
--

CREATE TABLE `donations` (
  `donation_id` char(36) NOT NULL,
  `initiative_id` char(36) DEFAULT NULL,
  `donor_id` char(36) DEFAULT NULL,
  `amount` decimal(15,2) NOT NULL,
  `transaction_ref` varchar(100) NOT NULL,
  `status` enum('pending','success','failed') DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `donations`
--

INSERT INTO `donations` (`donation_id`, `initiative_id`, `donor_id`, `amount`, `transaction_ref`, `status`, `created_at`) VALUES
('21e2117b-7479-4f1b-8c9c-c9c26f7a86fc', '34808752-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 1000.00, 'TXN-AFBEF82B', 'success', '2026-04-12 07:04:37'),
('79bfadeb-c6cd-4dc5-b1e1-ab4ee729a47c', '348048fc-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 1000.00, 'TXN-A62580FB', 'success', '2026-04-12 07:56:28');

-- --------------------------------------------------------

--
-- Table structure for table `initiatives`
--

CREATE TABLE `initiatives` (
  `initiative_id` char(36) NOT NULL,
  `creator_id` char(36) DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `category` enum('research','outreach','conservation','scholarship') NOT NULL,
  `target_amount` decimal(15,2) NOT NULL,
  `current_amount` decimal(15,2) DEFAULT 0.00,
  `status` enum('draft','active','completed','cancelled') DEFAULT 'draft',
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `initiatives`
--

INSERT INTO `initiatives` (`initiative_id`, `creator_id`, `title`, `description`, `category`, `target_amount`, `current_amount`, `status`, `start_date`, `end_date`, `created_at`) VALUES
('348048fc-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Kumpas Kalye: Street Music for a Cause', 'outreach campaign', 'outreach', 100000.00, 46000.00, 'active', '2026-01-01', '2026-12-31', '2026-04-12 05:55:26'),
('34808752-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Project Dunong: CS Research Lab Upgrade', 'research campaign', 'research', 150000.00, 121000.00, 'active', '2026-01-01', '2026-12-31', '2026-04-12 05:55:26'),
('34808ae7-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Perpetualite High Honors Scholarship', 'scholarship campaign', 'scholarship', 200000.00, 200000.00, 'active', '2026-01-01', '2026-12-31', '2026-04-12 05:55:26'),
('34808ca0-3634-11f1-8bf3-40c2bae4b8c0', '476860d3-0a04-4742-a985-56e8849ca9e1', 'Green Campus: Molino Conservation', 'conservation campaign', 'conservation', 50000.00, 15000.00, 'active', '2026-01-01', '2026-12-31', '2026-04-12 05:55:26');

-- --------------------------------------------------------

--
-- Table structure for table `milestones`
--

CREATE TABLE `milestones` (
  `milestone_id` char(36) NOT NULL,
  `initiative_id` char(36) DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `is_completed` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `updates`
--

CREATE TABLE `updates` (
  `update_id` char(36) NOT NULL,
  `initiative_id` char(36) DEFAULT NULL,
  `content` text NOT NULL,
  `image_url` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` char(36) NOT NULL,
  `rfid_tag` varchar(50) DEFAULT NULL,
  `full_name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('student','faculty','admin','donor') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `rfid_tag`, `full_name`, `email`, `password_hash`, `role`, `created_at`) VALUES
('476860d3-0a04-4742-a985-56e8849ca9e1', NULL, 'jocelyn', 'jocelynbaylon48@gmail.com', 'baylon', 'student', '2026-04-12 04:12:13');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `donations`
--
ALTER TABLE `donations`
  ADD PRIMARY KEY (`donation_id`),
  ADD UNIQUE KEY `transaction_ref` (`transaction_ref`),
  ADD KEY `initiative_id` (`initiative_id`),
  ADD KEY `donor_id` (`donor_id`);

--
-- Indexes for table `initiatives`
--
ALTER TABLE `initiatives`
  ADD PRIMARY KEY (`initiative_id`),
  ADD KEY `creator_id` (`creator_id`);

--
-- Indexes for table `milestones`
--
ALTER TABLE `milestones`
  ADD PRIMARY KEY (`milestone_id`),
  ADD KEY `initiative_id` (`initiative_id`);

--
-- Indexes for table `updates`
--
ALTER TABLE `updates`
  ADD PRIMARY KEY (`update_id`),
  ADD KEY `initiative_id` (`initiative_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `rfid_tag` (`rfid_tag`);

--
-- Constraints for dumped tables
--

--
-- Constraints for table `donations`
--
ALTER TABLE `donations`
  ADD CONSTRAINT `donations_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `donations_ibfk_2` FOREIGN KEY (`donor_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `initiatives`
--
ALTER TABLE `initiatives`
  ADD CONSTRAINT `initiatives_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `milestones`
--
ALTER TABLE `milestones`
  ADD CONSTRAINT `milestones_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE;

--
-- Constraints for table `updates`
--
ALTER TABLE `updates`
  ADD CONSTRAINT `updates_ibfk_1` FOREIGN KEY (`initiative_id`) REFERENCES `initiatives` (`initiative_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
