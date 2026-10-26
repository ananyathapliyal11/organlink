# OrganLink — Organ Donation & Inventory Management System

OrganLink is a web-based organ donation and inventory management system developed to streamline the management of donors, donations, available inventory, recipients, and allocation requests. It provides a centralized platform for managing donation records, monitoring inventory, matching requests with available units, and maintaining accountability through audit logs.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Database Design](#database-design)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [User Roles](#user-roles)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)
- [Contributors](#contributors)

## Overview

OrganLink aims to simplify the management of organ donation-related records through a centralized system. It supports hospital-based donor management, donation recording, inventory tracking, recipient registration, request processing, allocation management, and reporting.

The application includes authentication and role-based access to help ensure that users can access only the operations permitted to them.

## Features

### Authentication and Access Control
- User login and logout.
- Password hashing for credential security.
- Role-based access for administrators and hospital staff.
- Hospital-specific restrictions for staff operations.

### Donor Management
- Register and view donor records.
- Edit donor information.
- Search and manage donor records.
- Update donor status.

### Hospital Management
- View registered hospitals.
- Add hospital records through authorized administrator operations.
- Associate staff and donor operations with the relevant hospital.

### Donation Management
- Record donations.
- Maintain donation history.
- Associate donations with inventory records.
- Export donation reports as CSV files.

### Inventory Management
- Track available inventory units.
- View and filter inventory records.
- Maintain expiry information for inventory.
- Support inventory updates through donation and allocation workflows.

### Recipient and Request Management
- Register and manage recipients.
- Create and manage requests.
- Find potential matches between requests and available inventory.
- Allocate available units to requests.
- Cancel allocations or mark completed allocations.
- Manage pending requests and waitlisted requests.

### Reports and Audit Trail
- View donation and inventory reports.
- Generate demand reports.
- Export donation data.
- Maintain audit records of relevant system activities.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Database | MySQL |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Templating | Jinja2 |
| Database connectivity | Python MySQL database connector |
| Version control | Git and GitHub |

## Project Structure

```text
organlink/
├── app.py
├── db.py
├── module_a/
│   └── seed_a.sql
├── module_b/
│   ├── recipients.py
│   ├── requests.py
│   └── seed_b.sql
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── donors.html
│   ├── donations.html
│   ├── hospitals.html
│   ├── inventory.html
│   ├── recipients.html
│   ├── requests.html
│   ├── waitlist.html
│   ├── reports.html
│   └── audit_log.html
├── static/
│   └── images/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

*Note: The exact template filenames and supporting files may differ slightly depending on the final repository contents.*

## Database Design

OrganLink uses MySQL to store and manage application data.

The database supports the following major entities and workflows:

- **Users:** Authentication, roles, and staff access.
- **Hospitals:** Hospital records and associations.
- **Donors:** Donor information and status.
- **Donations:** Records of donations.
- **Inventory:** Available units and their status.
- **Recipients:** Recipient information.
- **Requests:** Requests raised for required units.
- **Allocations:** Associations between inventory units and requests.
- **Audit Logs:** Records of relevant database and application activities.

Database initialization and sample data are provided through the SQL seed scripts in the `module_a/` and `module_b/` directories. Run these scripts according to their dependencies and the schema defined in the project.

## Prerequisites

Before running OrganLink, ensure that you have:

- Python 3.10 or a compatible version supported by the project dependencies.
- MySQL Server.
- Git.
- `pip` for installing Python dependencies.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/ananyathapliyal11/organlink.git
cd organlink
```

### 2. Create a virtual environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the database

Start your MySQL server and create the database required by the application.

```sql
CREATE DATABASE organlink;
```

If the application expects a different database name, use the name specified in `db.py` or your environment configuration.

### 5. Configure environment variables

Create a `.env` file in the project root and enter the database settings expected by the application.

For example:

```env
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=organlink
```

**Important:** These variable names are examples. Use the exact names read by your application's database configuration. Keep `.env` out of version control and never commit real passwords or credentials.

### 6. Initialize the database

Execute the SQL schema and seed scripts included in the repository in the correct dependency order.

For example, using the MySQL command line:

```bash
mysql -u your_mysql_username -p organlink < module_a/seed_a.sql
mysql -u your_mysql_username -p organlink < module_b/seed_b.sql
```

Replace the filenames or command order if your scripts separate table creation from sample data or require another initialization sequence. Ensure all required tables, constraints, triggers, and initial records are created before starting the application.

## Running the Application

Activate the virtual environment, navigate to the project directory, and run:

```bash
python app.py
```

If the application is configured to run through Flask's CLI instead, use:

```bash
flask --app app run --debug
```

Open the local URL displayed in the terminal, usually:

```text
http://127.0.0.1:5000/
```

Log in using an account configured in the database. Do not assume default credentials; use the credentials established during database setup.

## User Roles

### Administrator
- Access the administrative dashboard.
- Manage authorized hospital operations.
- Oversee donor, donation, inventory, and reporting workflows.
- Access system records and audit information according to configured permissions.

### Hospital Staff
- Manage donor and donation records within permitted hospital scope.
- View relevant inventory information.
- Process recipient and request workflows according to assigned permissions.
- Access permitted reports and operational records.

The exact permissions are enforced by the application's implemented routes and access-control logic.

## Testing

The application was tested manually across its main workflows, including:

- Login and logout.
- Administrator and staff access.
- Donor creation, editing, searching, and status updates.
- Hospital management permissions.
- Donation recording and inventory updates.
- Inventory viewing and filtering.
- Recipient registration and management.
- Request creation, matching, and allocation workflows.
- Allocation cancellation and completion.
- Waitlist and report pages.
- CSV export and audit log access.
- Frontend navigation and page rendering.

These checks help verify that the application's principal features work together as expected. Test results apply to the environment and data used during testing.

## Future Enhancements

Potential future improvements include:

- Automated unit and integration tests.
- More comprehensive input validation and error handling.
- Enhanced reporting and visual analytics.
- Improved notification and request-status tracking.
- Deployment to a secure production environment.
- Additional security and privacy controls.

## Contributors

Developed as a collaborative academic project.

- **Ananya Thapliyal** — OrganLink development and integration.
- **Collaborators** — Contributed to the supply-side and recipient/request-side modules.

## Disclaimer

OrganLink is an academic software project intended to demonstrate database management, web development, authentication, inventory tracking, and request-allocation workflows. It is not a substitute for authorized clinical systems, professional medical judgment, or applicable organ donation and transplantation regulations.
