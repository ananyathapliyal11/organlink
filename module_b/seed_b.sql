-- OrganLink: Person B seed data for recipients and requests
-- Sample data seed file.
-- Run only when the recipient and request records have not already been inserted.
USE organlink;

INSERT INTO recipient
    (name, dob, gender, blood_group, phone, hospital_id, urgency_level, status)
VALUES
    ('Aarav Sharma', '2002-04-12', 'M', 'O+',  '9876500001', 1, 5, 'waiting'),
    ('Diya Patel',   '1998-09-23', 'F', 'A+',  '9876500002', 2, 4, 'waiting'),
    ('Rohan Kumar',  '2000-01-15', 'M', 'B+',  '9876500003', 3, 3, 'waiting'),
    ('Ananya Rao',   '1995-06-30', 'F', 'AB+', '9876500004', 1, 2, 'waiting'),
    ('Kabir Singh',  '1989-11-08', 'M', 'O-',  '9876500005', 4, 5, 'waiting'),
    ('Meera Nair',   '2001-03-17', 'F', 'A-',  '9876500006', 5, 4, 'waiting'),
    ('Ishaan Gupta', '1997-12-05', 'M', 'B-',  '9876500007', 2, 3, 'waiting'),
    ('Sara Khan',    '2003-07-21', 'F', 'AB-', '9876500008', 3, 5, 'waiting'),
    ('Arjun Das',    '1999-02-14', 'M', 'O+',  '9876500009', 4, 2, 'waiting'),
    ('Tara Joshi',   '1996-10-02', 'F', 'A+',  '9876500010', 1, 4, 'waiting'),
    ('Vikram Reddy', '1994-05-19', 'M', 'B+',  '9876500011', 5, 3, 'waiting'),
    ('Nisha Iyer',   '2002-08-11', 'F', 'O-',  '9876500012', 2, 5, 'waiting'),
    ('Dev Malhotra', '1993-01-27', 'M', 'AB+', '9876500013', 3, 1, 'waiting'),
    ('Pooja Verma',  '2000-12-09', 'F', 'A-',  '9876500014', 4, 4, 'waiting'),
    ('Aditya Bose',  '1998-04-04', 'M', 'B-',  '9876500015', 1, 3, 'waiting');
    -- Sample requests for OrganLink
INSERT INTO request
    (recipient_id, request_type, organ_type_id, blood_group, urgency_level, status)
VALUES
    (1,  'blood', NULL, 'O+',  5, 'pending'),
    (2,  'blood', NULL, 'A+',  4, 'pending'),
    (3,  'organ', 1,    'B+',  3, 'pending'),
    (4,  'organ', 2,    'AB+', 2, 'pending'),
    (5,  'blood', NULL, 'O-',  5, 'pending'),
    (6,  'organ', 1,    'A-',  4, 'pending'),
    (7,  'blood', NULL, 'B-',  3, 'pending'),
    (8,  'organ', 3,    'AB-', 5, 'pending'),
    (9,  'blood', NULL, 'O+',  2, 'pending'),
    (10, 'organ', 4,    'A+',  4, 'pending'),
    (11, 'blood', NULL, 'B+',  3, 'pending'),
    (12, 'organ', 2,    'O-',  5, 'pending'),
    (13, 'blood', NULL, 'AB+', 1, 'pending'),
    (14, 'organ', 5,    'A-',  4, 'pending'),
    (15, 'blood', NULL, 'B-',  3, 'pending'),
    (1,  'organ', 1,    'O+',  5, 'pending'),
    (2,  'blood', NULL, 'A+',  3, 'pending'),
    (3,  'organ', 3,    'B+',  4, 'pending'),
    (4,  'blood', NULL, 'AB+', 2, 'pending'),
    (5,  'organ', 2,    'O-',  5, 'pending');