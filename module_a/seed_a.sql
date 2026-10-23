
USE organlink;

-- OrganLink: Person A supply-side sample data
-- Run schema.sql first.
-- This seed file adds sample donors only.
-- Donations and inventory can be created through the Flask app
-- so the existing triggers generate expiry dates and audit logs.

INSERT INTO donor
    (name, dob, gender, blood_group, phone, city, donor_type, hospital_id, status)
VALUES
    ('Aarav Sharma', '1998-04-12', 'M', 'O+', '9000000101', 'Chennai', 'both', 1, 'active'),
    ('Diya Patel', '2001-09-23', 'F', 'A+', '9000000102', 'Chennai', 'blood', 1, 'active'),
    ('Rohan Kumar', '1995-02-08', 'M', 'B+', '9000000103', 'Bengaluru', 'organ', 2, 'active'),
    ('Meera Nair', '1999-11-16', 'F', 'AB+', '9000000104', 'Bengaluru', 'both', 2, 'active'),
    ('Ishaan Reddy', '1997-06-30', 'M', 'O-', '9000000105', 'Hyderabad', 'blood', 3, 'active'),
    ('Ananya Das', '2000-01-19', 'F', 'B-', '9000000106', 'Hyderabad', 'organ', 3, 'active');

-- Verify inserted donor records
SELECT donor_id, name, blood_group, donor_type, hospital_id, status
FROM donor
WHERE phone IN (
    '9000000101', '9000000102', '9000000103',
    '9000000104', '9000000105', '9000000106'
);
