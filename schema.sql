-- ============================================================
-- OrganLink: Organ & Blood Donor-Recipient Matching and Traceability
-- schema.sql  (FROZEN: both team members use this exact file)
-- Target: MySQL 8.0+
-- Ownership:  A writes -> users, hospital, donor, organ_type,
--                         blood_compatibility, donation, inventory_unit, audit_log
--             B writes -> recipient, request, allocation
-- ============================================================

DROP DATABASE IF EXISTS organlink;
CREATE DATABASE organlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE organlink;

-- ------------------------------------------------------------
-- 1. TABLES
-- ------------------------------------------------------------

CREATE TABLE hospital (
    hospital_id   INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    city          VARCHAR(60)  NOT NULL,
    contact       VARCHAR(20),
    type          ENUM('hospital','blood_bank','transplant_center') NOT NULL DEFAULT 'hospital'
);

CREATE TABLE users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           ENUM('admin','staff') NOT NULL DEFAULT 'staff',
    hospital_id    INT NULL,
    FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE organ_type (
    organ_type_id       INT AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(50) NOT NULL UNIQUE,
    max_viability_hours INT NOT NULL CHECK (max_viability_hours > 0)
);

-- Lookup table: which donor blood group can give to which recipient group
CREATE TABLE blood_compatibility (
    donor_group     ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    recipient_group ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    PRIMARY KEY (donor_group, recipient_group)
);

CREATE TABLE donor (
    donor_id     INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    dob          DATE NOT NULL,
    gender       ENUM('M','F','O') NOT NULL,
    blood_group  ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    phone        VARCHAR(15),
    city         VARCHAR(60),
    donor_type   ENUM('blood','organ','both') NOT NULL,
    hospital_id  INT NOT NULL,
    status       ENUM('active','inactive') NOT NULL DEFAULT 'active',
    FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE donation (
    donation_id    INT AUTO_INCREMENT PRIMARY KEY,
    donor_id       INT NOT NULL,
    donation_type  ENUM('blood','organ') NOT NULL,
    organ_type_id  INT NULL,
    donation_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES donor(donor_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (organ_type_id) REFERENCES organ_type(organ_type_id),
    CHECK ( (donation_type = 'blood' AND organ_type_id IS NULL)
         OR (donation_type = 'organ' AND organ_type_id IS NOT NULL) )
);

CREATE TABLE inventory_unit (
    unit_id        INT AUTO_INCREMENT PRIMARY KEY,
    donation_id    INT NOT NULL,
    unit_type      ENUM('blood','organ') NOT NULL,
    organ_type_id  INT NULL,
    blood_group    ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    collected_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expiry_at      DATETIME NULL,   -- auto-filled by trigger trg_unit_before_insert if NULL
    status         ENUM('available','reserved','used','expired') NOT NULL DEFAULT 'available',
    hospital_id    INT NOT NULL,
    FOREIGN KEY (donation_id)   REFERENCES donation(donation_id)  ON DELETE RESTRICT,
    FOREIGN KEY (organ_type_id) REFERENCES organ_type(organ_type_id),
    FOREIGN KEY (hospital_id)   REFERENCES hospital(hospital_id)  ON DELETE RESTRICT,
    CHECK (expiry_at IS NULL OR expiry_at > collected_at),
    CHECK ( (unit_type = 'blood' AND organ_type_id IS NULL)
         OR (unit_type = 'organ' AND organ_type_id IS NOT NULL) )
);

CREATE TABLE recipient (
    recipient_id     INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    dob              DATE NOT NULL,
    gender           ENUM('M','F','O') NOT NULL,
    blood_group      ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    phone            VARCHAR(15),
    hospital_id      INT NOT NULL,
    urgency_level    TINYINT NOT NULL DEFAULT 3 CHECK (urgency_level BETWEEN 1 AND 5),
    registered_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           ENUM('waiting','transplanted','inactive') NOT NULL DEFAULT 'waiting',
    FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE request (
    request_id      INT AUTO_INCREMENT PRIMARY KEY,
    recipient_id    INT NOT NULL,
    request_type    ENUM('blood','organ') NOT NULL,
    organ_type_id   INT NULL,
    blood_group     ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NOT NULL,
    urgency_level   TINYINT NOT NULL DEFAULT 3 CHECK (urgency_level BETWEEN 1 AND 5),
    request_date    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('pending','matched','fulfilled','cancelled') NOT NULL DEFAULT 'pending',
    FOREIGN KEY (recipient_id)  REFERENCES recipient(recipient_id) ON DELETE CASCADE,
    FOREIGN KEY (organ_type_id) REFERENCES organ_type(organ_type_id),
    CHECK ( (request_type = 'blood' AND organ_type_id IS NULL)
         OR (request_type = 'organ' AND organ_type_id IS NOT NULL) )
);

-- NOTE: the brief said unit_id UNIQUE. A plain UNIQUE would block re-allocating a unit
-- after a cancelled allocation, so we enforce uniqueness only on NON-cancelled rows
-- using a generated column (NULLs are ignored by UNIQUE in MySQL).
CREATE TABLE allocation (
    allocation_id   INT AUTO_INCREMENT PRIMARY KEY,
    unit_id         INT NOT NULL,
    request_id      INT NOT NULL,
    allocated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('reserved','completed','cancelled') NOT NULL DEFAULT 'reserved',
    active_unit_id  INT GENERATED ALWAYS AS (IF(status = 'cancelled', NULL, unit_id)) STORED,
    UNIQUE KEY uq_one_active_allocation_per_unit (active_unit_id),
    FOREIGN KEY (unit_id)    REFERENCES inventory_unit(unit_id) ON DELETE RESTRICT,
    FOREIGN KEY (request_id) REFERENCES request(request_id)     ON DELETE RESTRICT
);

CREATE TABLE audit_log (
    log_id      INT AUTO_INCREMENT PRIMARY KEY,
    unit_id     INT NOT NULL,
    old_status  VARCHAR(20) NULL,
    new_status  VARCHAR(20) NOT NULL,
    changed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks     VARCHAR(255),
    FOREIGN KEY (unit_id) REFERENCES inventory_unit(unit_id) ON DELETE CASCADE
);

CREATE INDEX idx_unit_lookup    ON inventory_unit (status, unit_type, blood_group, expiry_at);
CREATE INDEX idx_request_status ON request (status, urgency_level, request_date);

-- ------------------------------------------------------------
-- 2. VIEW  (owner: A)
-- ------------------------------------------------------------

CREATE VIEW available_units AS
SELECT u.unit_id, u.unit_type, u.organ_type_id, ot.name AS organ_name,
       u.blood_group, u.collected_at, u.expiry_at, u.hospital_id,
       h.name AS hospital_name, h.city
FROM inventory_unit u
JOIN hospital h         ON h.hospital_id = u.hospital_id
LEFT JOIN organ_type ot ON ot.organ_type_id = u.organ_type_id
WHERE u.status = 'available' AND u.expiry_at > NOW();

-- ------------------------------------------------------------
-- 3. TRIGGERS, PROCEDURES, EVENT
-- ------------------------------------------------------------

DELIMITER $$

-- (A) Auto-set expiry: blood = 35 days, organ = organ_type.max_viability_hours
CREATE TRIGGER trg_unit_before_insert
BEFORE INSERT ON inventory_unit
FOR EACH ROW
BEGIN
    DECLARE v_hours INT;
    IF NEW.expiry_at IS NULL THEN
        IF NEW.unit_type = 'blood' THEN
            SET NEW.expiry_at = DATE_ADD(NEW.collected_at, INTERVAL 35 DAY);
        ELSE
            SELECT max_viability_hours INTO v_hours
            FROM organ_type WHERE organ_type_id = NEW.organ_type_id;
            SET NEW.expiry_at = DATE_ADD(NEW.collected_at, INTERVAL v_hours HOUR);
        END IF;
    END IF;
END$$

-- (A) Audit: log creation of a unit
CREATE TRIGGER trg_unit_after_insert
AFTER INSERT ON inventory_unit
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (unit_id, old_status, new_status, remarks)
    VALUES (NEW.unit_id, NULL, NEW.status, 'Unit created from donation');
END$$

-- (A) Audit: log every status change
CREATE TRIGGER trg_unit_after_update
AFTER UPDATE ON inventory_unit
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_log (unit_id, old_status, new_status, remarks)
        VALUES (NEW.unit_id, OLD.status, NEW.status,
                CONCAT('Status changed from ', OLD.status, ' to ', NEW.status));
    END IF;
END$$

-- (B) When an allocation completes -> unit 'used', request 'fulfilled'
--     When an allocation is cancelled -> unit back to 'available', request back to 'pending'
--     (This is the only place B's logic touches A's table; it is status-only.)
CREATE TRIGGER trg_allocation_after_update
AFTER UPDATE ON allocation
FOR EACH ROW
BEGIN
    IF OLD.status = 'reserved' AND NEW.status = 'completed' THEN
        UPDATE inventory_unit SET status = 'used'      WHERE unit_id = NEW.unit_id;
        UPDATE request        SET status = 'fulfilled' WHERE request_id = NEW.request_id;
    ELSEIF OLD.status = 'reserved' AND NEW.status = 'cancelled' THEN
        UPDATE inventory_unit SET status = 'available' WHERE unit_id = NEW.unit_id AND status = 'reserved';
        UPDATE request        SET status = 'pending'   WHERE request_id = NEW.request_id;
    END IF;
END$$

-- (B) FindMatch: ranked compatible units for a request
--     Rank: same hospital first, then soonest expiry (use it before it is wasted)
CREATE PROCEDURE FindMatch(IN p_request_id INT)
BEGIN
    SELECT au.unit_id, au.unit_type, au.organ_name, au.blood_group,
           au.expiry_at, au.hospital_name, au.city,
           (au.hospital_id = rec.hospital_id) AS same_hospital
    FROM request r
    JOIN recipient rec ON rec.recipient_id = r.recipient_id
    JOIN blood_compatibility bc ON bc.recipient_group = r.blood_group
    JOIN available_units au
         ON au.blood_group = bc.donor_group
        AND au.unit_type   = r.request_type
        AND (r.request_type = 'blood' OR au.organ_type_id = r.organ_type_id)
    WHERE r.request_id = p_request_id
      AND r.status = 'pending'
    ORDER BY same_hospital DESC, au.expiry_at ASC;
END$$

-- (B) AllocateUnit: atomic reservation (the ACID showpiece)
CREATE PROCEDURE AllocateUnit(IN p_unit_id INT, IN p_request_id INT)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_req_status VARCHAR(20);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Allocation failed and was rolled back';
    END;

    START TRANSACTION;

    SELECT status INTO v_status
    FROM inventory_unit WHERE unit_id = p_unit_id FOR UPDATE;      -- row lock

    SELECT status INTO v_req_status
    FROM request WHERE request_id = p_request_id FOR UPDATE;

    IF v_status IS NULL OR v_status <> 'available' THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unit is no longer available';
    END IF;
    IF v_req_status IS NULL OR v_req_status <> 'pending' THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Request is not pending';
    END IF;

    INSERT INTO allocation (unit_id, request_id) VALUES (p_unit_id, p_request_id);
    UPDATE inventory_unit SET status = 'reserved' WHERE unit_id = p_unit_id;
    UPDATE request        SET status = 'matched'  WHERE request_id = p_request_id;

    COMMIT;
END$$

-- (A) Auto-expire available units every minute (needs event_scheduler = ON)
CREATE EVENT evt_expire_units
ON SCHEDULE EVERY 1 MINUTE
DO
    UPDATE inventory_unit
    SET status = 'expired'
    WHERE status = 'available' AND expiry_at <= NOW()$$

DELIMITER ;

SET GLOBAL event_scheduler = ON;

-- ------------------------------------------------------------
-- 4. SHARED REFERENCE DATA (identical for both team members)
-- ------------------------------------------------------------

INSERT INTO hospital (name, city, contact, type) VALUES
('City General Hospital',        'Chennai',    '044-2000001', 'hospital'),
('LifeCare Blood Bank',          'Chennai',    '044-2000002', 'blood_bank'),
('Apollo Transplant Center',     'Coimbatore', '0422-300003', 'transplant_center'),
('Government Medical College',   'Madurai',    '0452-400004', 'hospital'),
('Red Cross Blood Bank',         'Bengaluru',  '080-5000005', 'blood_bank');

INSERT INTO organ_type (name, max_viability_hours) VALUES
('Kidney', 36), ('Liver', 12), ('Heart', 4), ('Lung', 6),
('Pancreas', 12), ('Small Intestine', 8), ('Cornea', 336), ('Skin', 120);

-- Donor group -> recipient groups that can safely receive it
INSERT INTO blood_compatibility (donor_group, recipient_group) VALUES
('O-','O-'),('O-','O+'),('O-','A-'),('O-','A+'),('O-','B-'),('O-','B+'),('O-','AB-'),('O-','AB+'),
('O+','O+'),('O+','A+'),('O+','B+'),('O+','AB+'),
('A-','A-'),('A-','A+'),('A-','AB-'),('A-','AB+'),
('A+','A+'),('A+','AB+'),
('B-','B-'),('B-','B+'),('B-','AB-'),('B-','AB+'),
('B+','B+'),('B+','AB+'),
('AB-','AB-'),('AB-','AB+'),
('AB+','AB+');

-- Create the first admin user from the app (so the password is hashed properly).
-- Sample data (donors, units, recipients, requests) lives in each person's own seed file:
--   module_a/seed_a.sql   and   module_b/seed_b.sql
