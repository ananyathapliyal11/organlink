
import os
import csv
import io
from functools import wraps

from flask import (
    Flask, render_template, make_response, request, redirect,
    url_for, session, flash
)
from werkzeug.security import check_password_hash
from db import get_db_connection
from module_b.recipients import recipients_bp
from module_b.requests import requests_bp
from datetime import date

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-change-this")
app.register_blueprint(recipients_bp)
app.register_blueprint(requests_bp)


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT user_id, username, password_hash, role, hospital_id
                FROM users
                WHERE username = %s 
                """,
                (username,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"], password
            ):
                session.clear()
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                session["hospital_id"] = user["hospital_id"]

                return redirect(url_for("dashboard"))

            flash("Invalid username or password.", "danger")

        except Exception:
            app.logger.exception("Login failed")
            flash("Unable to log in right now. Check the server terminal.", "danger")

        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



def admin_required(route_function):
    @wraps(route_function)
    @login_required
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Only administrators can perform this action.", "danger")
            return redirect(url_for("dashboard"))
        return route_function(*args, **kwargs)
    return wrapper


@app.route("/hospitals")
@login_required
def hospitals():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT hospital_id, name, city, contact, type
            FROM hospital
            ORDER BY name
        """)
        hospital_list = cursor.fetchall()

        return render_template(
            "hospitals.html",
            hospitals=hospital_list
        )
    except Exception:
        app.logger.exception("Could not load hospitals")
        flash("Could not load hospital records.", "danger")
        return redirect(url_for("dashboard"))
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/hospitals/add", methods=["POST"])
@admin_required
def add_hospital():
    name = request.form.get("name", "").strip()
    city = request.form.get("city", "").strip()
    contact = request.form.get("contact", "").strip() or None
    hospital_type = request.form.get("type", "")

    valid_types = {"hospital", "blood_bank", "transplant_center"}

    if not name or not city or hospital_type not in valid_types:
        flash("Enter a valid hospital name, city, and type.", "danger")
        return redirect(url_for("hospitals"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO hospital (name, city, contact, type)
            VALUES (%s, %s, %s, %s)
        """, (name, city, contact, hospital_type))

        connection.commit()
        flash("Hospital added successfully!", "success")

    except Exception:
        if connection is not None and connection.is_connected():
            connection.rollback()
        app.logger.exception("Could not add hospital")
        flash("Could not add hospital. Please check the details.", "danger")

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("hospitals"))



@app.route("/donors")
@login_required
def donors():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        role = session.get("role")
        hospital_id = session.get("hospital_id")

        if role == "staff" and hospital_id is None:
            flash("Your account is not assigned to a hospital.", "warning")
            return redirect(url_for("dashboard"))

        query = """
            SELECT d.donor_id, d.name, d.dob, d.gender,
                   d.blood_group, d.phone, d.city, d.donor_type,
                   d.status, d.hospital_id, h.name AS hospital_name
            FROM donor d
            JOIN hospital h ON h.hospital_id = d.hospital_id
            WHERE 1=1
        """
        params = []

        # Staff can only see donors belonging to their hospital.
        if role == "staff":
            query += " AND d.hospital_id = %s"
            params.append(hospital_id)

        search = request.args.get("search", "").strip()
        blood_group = request.args.get("blood_group", "")
        donor_type = request.args.get("donor_type", "")
        status = request.args.get("status", "")

        if search:
            query += """
                AND (d.name LIKE %s OR d.city LIKE %s
                     OR d.phone LIKE %s)
            """
            term = f"%{search}%"
            params.extend([term, term, term])

        if blood_group in {
            "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"
        }:
            query += " AND d.blood_group = %s"
            params.append(blood_group)

        if donor_type in {"blood", "organ", "both"}:
            query += " AND d.donor_type = %s"
            params.append(donor_type)

        if status in {"active", "inactive"}:
            query += " AND d.status = %s"
            params.append(status)

        query += " ORDER BY d.donor_id DESC"

        cursor.execute(query, tuple(params))
        donor_list = cursor.fetchall()

        if role == "admin":
            cursor.execute(
                "SELECT hospital_id, name FROM hospital ORDER BY name"
            )
            hospital_list = cursor.fetchall()
        else:
            cursor.execute(
                "SELECT hospital_id, name FROM hospital WHERE hospital_id = %s",
                (hospital_id,)
            )
            hospital_list = cursor.fetchall()

        return render_template(
            "donors.html",
            donors=donor_list,
            hospitals=hospital_list,
            filters={
                "search": search,
                "blood_group": blood_group,
                "donor_type": donor_type,
                "status": status,
            }
        )

    except Exception:
        app.logger.exception("Could not load donors")
        flash("Could not load donor records.", "danger")
        return redirect(url_for("dashboard"))

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/donors/add", methods=["POST"])
@login_required
def add_donor():
    name = request.form.get("name", "").strip()
    dob = request.form.get("dob", "")
    gender = request.form.get("gender", "")
    blood_group = request.form.get("blood_group", "")
    phone = request.form.get("phone", "").strip() or None
    city = request.form.get("city", "").strip()
    donor_type = request.form.get("donor_type", "")

    valid_groups = {
        "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"
    }

    if (
        not name or not city
        or gender not in {"M", "F", "O"}
        or blood_group not in valid_groups
        or donor_type not in {"blood", "organ", "both"}
    ):
        flash("Please enter valid donor details.", "danger")
        return redirect(url_for("donors"))

    try:
        dob_date = date.fromisoformat(dob)
        if dob_date >= date.today():
            flash("Date of birth must be in the past.", "danger")
            return redirect(url_for("donors"))
    except ValueError:
        flash("Please enter a valid date of birth.", "danger")
        return redirect(url_for("donors"))

    role = session.get("role")

    if role == "staff":
        # Never trust a hospital ID submitted by staff through a form.
        hospital_id = session.get("hospital_id")
        if hospital_id is None:
            flash("Your account is not assigned to a hospital.", "danger")
            return redirect(url_for("dashboard"))
    else:
        try:
            hospital_id = int(request.form.get("hospital_id", ""))
        except (ValueError, TypeError):
            flash("Please select a valid hospital.", "danger")
            return redirect(url_for("donors"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Confirm that the selected hospital exists.
        cursor.execute(
            "SELECT hospital_id FROM hospital WHERE hospital_id = %s",
            (hospital_id,)
        )
        if cursor.fetchone() is None:
            flash("Selected hospital does not exist.", "danger")
            return redirect(url_for("donors"))

        cursor.execute("""
            INSERT INTO donor
                (name, dob, gender, blood_group, phone, city,
                 donor_type, hospital_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name, dob_date, gender, blood_group, phone,
            city, donor_type, hospital_id
        ))

        connection.commit()
        flash("Donor registered successfully!", "success")

    except Exception:
        if connection is not None and connection.is_connected():
            connection.rollback()
        app.logger.exception("Could not register donor")
        flash("Could not register donor. Please try again.", "danger")

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("donors"))



@app.route("/donors/<int:donor_id>/edit", methods=["GET", "POST"])
@login_required
def edit_donor(donor_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        role = session.get("role")
        hospital_id = session.get("hospital_id")

        if role == "staff" and hospital_id is None:
            flash("Your account is not assigned to a hospital.", "warning")
            return redirect(url_for("dashboard"))

        # Enforce hospital access on the server.
        sql = "SELECT * FROM donor WHERE donor_id = %s"
        params = [donor_id]

        if role == "staff":
            sql += " AND hospital_id = %s"
            params.append(hospital_id)

        cursor.execute(sql, tuple(params))
        donor = cursor.fetchone()

        if donor is None:
            flash("Donor not found or access denied.", "danger")
            return redirect(url_for("donors"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            dob = request.form.get("dob", "")
            gender = request.form.get("gender", "")
            blood_group = request.form.get("blood_group", "")
            phone = request.form.get("phone", "").strip() or None
            city = request.form.get("city", "").strip()
            donor_type = request.form.get("donor_type", "")

            valid_groups = {
                "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"
            }

            if (
                not name or not city
                or gender not in {"M", "F", "O"}
                or blood_group not in valid_groups
                or donor_type not in {"blood", "organ", "both"}
            ):
                flash("Please enter valid donor details.", "danger")
                return redirect(url_for("edit_donor", donor_id=donor_id))

            try:
                dob_date = date.fromisoformat(dob)
                if dob_date >= date.today():
                    raise ValueError
            except ValueError:
                flash("Enter a valid date of birth in the past.", "danger")
                return redirect(url_for("edit_donor", donor_id=donor_id))

            if role == "staff":
                target_hospital_id = hospital_id
            else:
                try:
                    target_hospital_id = int(
                        request.form.get("hospital_id", "")
                    )
                except (ValueError, TypeError):
                    flash("Select a valid hospital.", "danger")
                    return redirect(
                        url_for("edit_donor", donor_id=donor_id)
                    )

            cursor.execute(
                "SELECT hospital_id FROM hospital WHERE hospital_id = %s",
                (target_hospital_id,)
            )
            if cursor.fetchone() is None:
                flash("Selected hospital does not exist.", "danger")
                return redirect(url_for("edit_donor", donor_id=donor_id))

            cursor.execute("""
                UPDATE donor
                SET name = %s, dob = %s, gender = %s,
                    blood_group = %s, phone = %s, city = %s,
                    donor_type = %s, hospital_id = %s
                WHERE donor_id = %s
            """, (
                name, dob_date, gender, blood_group,
                phone, city, donor_type, target_hospital_id, donor_id
            ))

            connection.commit()
            flash("Donor details updated successfully!", "success")
            return redirect(url_for("donors"))

        if role == "admin":
            cursor.execute(
                "SELECT hospital_id, name FROM hospital ORDER BY name"
            )
        else:
            cursor.execute(
                "SELECT hospital_id, name FROM hospital WHERE hospital_id = %s",
                (hospital_id,)
            )

        hospital_list = cursor.fetchall()

        return render_template(
            "edit_donor.html",
            donor=donor,
            hospitals=hospital_list
        )

    except Exception:
        if connection is not None and connection.is_connected():
            connection.rollback()
        app.logger.exception("Could not edit donor")
        flash("Could not load or update donor details.", "danger")
        return redirect(url_for("donors"))

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/donors/<int:donor_id>/toggle-status", methods=["POST"])
@login_required
def toggle_donor_status(donor_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        sql = """
            UPDATE donor
            SET status = CASE
                WHEN status = 'active' THEN 'inactive'
                ELSE 'active'
            END
            WHERE donor_id = %s
        """
        params = [donor_id]

        if session.get("role") == "staff":
            hospital_id = session.get("hospital_id")

            if hospital_id is None:
                flash("Your account is not assigned to a hospital.", "warning")
                return redirect(url_for("donors"))

            sql += " AND hospital_id = %s"
            params.append(hospital_id)

        cursor.execute(sql, tuple(params))

        if cursor.rowcount == 0:
            connection.rollback()
            flash("Donor not found or access denied.", "danger")
        else:
            connection.commit()
            flash("Donor status updated successfully!", "success")

    except Exception:
        if connection is not None and connection.is_connected():
            connection.rollback()
        app.logger.exception("Could not update donor status")
        flash("Could not update donor status.", "danger")

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("donors"))



@app.route("/donations", methods=["GET", "POST"])
@login_required
def donations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if request.method == "POST":
            donor_id = request.form.get("donor_id", type=int)
            donation_type = request.form.get("donation_type")
            organ_type_id = request.form.get("organ_type_id", type=int)

            if not donor_id or donation_type not in ("blood", "organ"):
                flash("Please select a valid donor and donation type.", "danger")
                return redirect(url_for("donations"))

            if donation_type == "blood":
                organ_type_id = None
            elif not organ_type_id:
                flash("Please select an organ type.", "danger")
                return redirect(url_for("donations"))

            # Fetch the donor and enforce hospital access.
            cursor.execute(
                """
                SELECT donor_id, blood_group, donor_type, hospital_id, status
                FROM donor
                WHERE donor_id = %s
                """,
                (donor_id,)
            )
            donor = cursor.fetchone()

            if not donor:
                flash("Donor not found.", "danger")
                return redirect(url_for("donations"))

            if (
                session.get("role") != "admin"
                and donor["hospital_id"] != session.get("hospital_id")
            ):
                flash("You cannot record donations for another hospital.", "danger")
                return redirect(url_for("donations"))

            if donor["status"] != "active":
                flash("Only active donors can donate.", "danger")
                return redirect(url_for("donations"))

            if donor["donor_type"] not in (donation_type, "both"):
                flash("This donor is not registered for that donation type.", "danger")
                return redirect(url_for("donations"))

            # Record the donation and create its inventory unit together.
            try:
                cursor.execute(
                    """
                    INSERT INTO donation
                        (donor_id, donation_type, organ_type_id)
                    VALUES (%s, %s, %s)
                    """,
                    (donor_id, donation_type, organ_type_id)
                )
                donation_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO inventory_unit
                        (donation_id, unit_type, organ_type_id,
                         blood_group, hospital_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        donation_id,
                        donation_type,
                        organ_type_id,
                        donor["blood_group"],
                        donor["hospital_id"]
                    )
                )

                conn.commit()
                flash(
                    "Donation recorded and inventory unit created successfully!",
                    "success"
                )
                return redirect(url_for("donations"))

            except Exception:
                conn.rollback()
                raise

        # Only show active donors accessible to this user.
        if session.get("role") == "admin":
            cursor.execute(
                """
                SELECT donor_id, name, blood_group, donor_type, hospital_id
                FROM donor
                WHERE status = 'active'
                ORDER BY name
                """
            )
        else:
            cursor.execute(
                """
                SELECT donor_id, name, blood_group, donor_type, hospital_id
                FROM donor
                WHERE status = 'active' AND hospital_id = %s
                ORDER BY name
                """,
                (session.get("hospital_id"),)
            )

        donors_list = cursor.fetchall()

        cursor.execute(
            "SELECT organ_type_id, name FROM organ_type ORDER BY name"
        )
        organ_types = cursor.fetchall()

        # Recent donations for the current hospital, or all hospitals for admins.
        if session.get("role") == "admin":
            cursor.execute(
                """
                SELECT d.donation_id, d.donation_type, d.donation_date,
                       donor.name AS donor_name,
                       iu.unit_id, iu.status AS unit_status,
                       h.name AS hospital_name,
                       ot.name AS organ_name
                FROM donation d
                JOIN donor ON d.donor_id = donor.donor_id
                JOIN inventory_unit iu ON iu.donation_id = d.donation_id
                JOIN hospital h ON iu.hospital_id = h.hospital_id
                LEFT JOIN organ_type ot ON iu.organ_type_id = ot.organ_type_id
                ORDER BY d.donation_date DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT d.donation_id, d.donation_type, d.donation_date,
                       donor.name AS donor_name,
                       iu.unit_id, iu.status AS unit_status,
                       h.name AS hospital_name,
                       ot.name AS organ_name
                FROM donation d
                JOIN donor ON d.donor_id = donor.donor_id
                JOIN inventory_unit iu ON iu.donation_id = d.donation_id
                JOIN hospital h ON iu.hospital_id = h.hospital_id
                LEFT JOIN organ_type ot ON iu.organ_type_id = ot.organ_type_id
                WHERE iu.hospital_id = %s
                ORDER BY d.donation_date DESC
                """,
                (session.get("hospital_id"),)
            )

        recent_donations = cursor.fetchall()

        return render_template(
            "donations.html",
            donors=donors_list,
            organ_types=organ_types,
            donations=recent_donations
        )

    except Exception as e:
        conn.rollback()
        app.logger.exception("Donation module error")
        flash("Could not process the donation. Please check the server log.", "danger")
        return redirect(url_for("donations"))

    finally:
        cursor.close()
        conn.close()


@app.route("/inventory")
@login_required
def inventory():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        blood_group = request.args.get("blood_group", "").strip()
        unit_type = request.args.get("unit_type", "").strip()
        status = request.args.get("status", "").strip()
        hospital_id = request.args.get("hospital_id", "").strip()

        conditions = []
        params = []

        # Staff can only view inventory belonging to their hospital.
        if session.get("role") != "admin":
            conditions.append("iu.hospital_id = %s")
            params.append(session.get("hospital_id"))
        elif hospital_id.isdigit():
            conditions.append("iu.hospital_id = %s")
            params.append(int(hospital_id))

        if blood_group in (
            "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"
        ):
            conditions.append("iu.blood_group = %s")
            params.append(blood_group)

        if unit_type in ("blood", "organ"):
            conditions.append("iu.unit_type = %s")
            params.append(unit_type)

        if status in ("available", "reserved", "used", "expired"):
            if status == "expired":
                conditions.append(
                    "(iu.status = 'expired' OR "
                    "(iu.expiry_at IS NOT NULL AND iu.expiry_at <= NOW()))"
                )
            elif status == "available":
                conditions.append(
                    "iu.status = 'available' AND "
                    "(iu.expiry_at IS NULL OR iu.expiry_at > NOW())"
                )
            else:
                conditions.append("iu.status = %s")
                params.append(status)

        sql = """
            SELECT
                iu.unit_id,
                iu.donation_id,
                iu.unit_type,
                iu.blood_group,
                iu.collected_at,
                iu.expiry_at,
                iu.status,
                donor.name AS donor_name,
                h.name AS hospital_name,
                ot.name AS organ_name,
                CASE
                    WHEN iu.expiry_at IS NOT NULL
                         AND iu.expiry_at <= NOW()
                        THEN 'Expired'
                    WHEN iu.expiry_at IS NOT NULL
                         AND iu.expiry_at <= DATE_ADD(NOW(), INTERVAL 3 DAY)
                        THEN 'Expiring Soon'
                    ELSE 'OK'
                END AS expiry_label
            FROM inventory_unit iu
            JOIN donation d ON iu.donation_id = d.donation_id
            JOIN donor ON d.donor_id = donor.donor_id
            JOIN hospital h ON iu.hospital_id = h.hospital_id
            LEFT JOIN organ_type ot
                ON iu.organ_type_id = ot.organ_type_id
        """

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY iu.collected_at DESC"

        cursor.execute(sql, tuple(params))
        units = cursor.fetchall()

        hospitals = []
        if session.get("role") == "admin":
            cursor.execute(
                "SELECT hospital_id, name FROM hospital ORDER BY name"
            )
            hospitals = cursor.fetchall()

        return render_template(
            "inventory.html",
            units=units,
            hospitals=hospitals,
            selected_blood_group=blood_group,
            selected_unit_type=unit_type,
            selected_status=status,
            selected_hospital_id=hospital_id
        )

    except Exception:
        app.logger.exception("Inventory page error")
        flash("Could not load inventory. Check the server log.", "danger")
        return redirect(url_for("dashboard"))

    finally:
        cursor.close()
        conn.close()



@app.route("/reports")
@login_required
def reports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        is_admin = session.get("role") == "admin"
        hospital_id = session.get("hospital_id")

        # Build hospital filters for the current user's role.
        donor_filter = "" if is_admin else " WHERE hospital_id = %s"
        donor_params = () if is_admin else (hospital_id,)

        inventory_filter = "" if is_admin else " WHERE hospital_id = %s"
        inventory_params = () if is_admin else (hospital_id,)

        donation_filter = "" if is_admin else " WHERE donor.hospital_id = %s"
        donation_params = () if is_admin else (hospital_id,)

        # Donor statistics.
        cursor.execute(
            "SELECT COUNT(*) AS total FROM donor" + donor_filter,
            donor_params
        )
        total_donors = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM donor"
            + (" WHERE status = 'active'" if is_admin
               else " WHERE status = 'active' AND hospital_id = %s"),
            () if is_admin else (hospital_id,)
        )
        active_donors = cursor.fetchone()["total"]

        # Donation statistics.
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM donation
            JOIN donor ON donation.donor_id = donor.donor_id
            """ + donation_filter,
            donation_params
        )
        total_donations = cursor.fetchone()["total"]

        # Inventory statistics.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    status = 'available'
                    AND (expiry_at IS NULL OR expiry_at > NOW())
                ), 0) AS available,
                COALESCE(SUM(
                    status = 'expired'
                    OR (expiry_at IS NOT NULL AND expiry_at <= NOW())
                ), 0) AS expired,
                COALESCE(SUM(
                    status = 'available'
                    AND expiry_at > NOW()
                    AND expiry_at <= DATE_ADD(NOW(), INTERVAL 3 DAY)
                ), 0) AS expiring_soon
            FROM inventory_unit
            """ + inventory_filter,
            inventory_params
        )
        inventory_stats = cursor.fetchone()

        # Available blood units by blood group.
        blood_sql = """
            SELECT blood_group, COUNT(*) AS unit_count
            FROM inventory_unit
            WHERE unit_type = 'blood'
              AND status = 'available'
              AND (expiry_at IS NULL OR expiry_at > NOW())
        """
        blood_params = []

        if not is_admin:
            blood_sql += " AND hospital_id = %s"
            blood_params.append(hospital_id)

        blood_sql += " GROUP BY blood_group ORDER BY blood_group"

        cursor.execute(blood_sql, tuple(blood_params))
        blood_inventory = cursor.fetchall()

        # Latest donations.
        recent_sql = """
            SELECT donation.donation_id,
                   donation.donation_date,
                   donation.donation_type,
                   donor.name AS donor_name,
                   hospital.name AS hospital_name
            FROM donation
            JOIN donor ON donation.donor_id = donor.donor_id
            JOIN hospital ON donor.hospital_id = hospital.hospital_id
        """
        recent_params = []

        if not is_admin:
            recent_sql += " WHERE donor.hospital_id = %s"
            recent_params.append(hospital_id)

        recent_sql += " ORDER BY donation.donation_date DESC LIMIT 10"

        cursor.execute(recent_sql, tuple(recent_params))
        recent_donations = cursor.fetchall()

        return render_template(
            "reports.html",
            total_donors=total_donors,
            active_donors=active_donors,
            total_donations=total_donations,
            inventory_stats=inventory_stats,
            blood_inventory=blood_inventory,
            recent_donations=recent_donations
        )

    except Exception:
        app.logger.exception("Reports dashboard error")
        flash("Could not load reports. Check the server log.", "danger")
        return redirect(url_for("dashboard"))

    finally:
        cursor.close()
        conn.close()



@app.route("/audit-log")
@login_required
def audit_log():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        is_admin = session.get("role") == "admin"
        hospital_id = session.get("hospital_id")

        sql = """
            SELECT
                al.log_id,
                al.unit_id,
                al.old_status,
                al.new_status,
                al.changed_at,
                al.remarks,
                h.name AS hospital_name
            FROM audit_log al
            JOIN inventory_unit iu ON al.unit_id = iu.unit_id
            JOIN hospital h ON iu.hospital_id = h.hospital_id
        """
        params = []

        if not is_admin:
            sql += " WHERE iu.hospital_id = %s"
            params.append(hospital_id)

        sql += " ORDER BY al.changed_at DESC, al.log_id DESC"

        cursor.execute(sql, tuple(params))
        logs = cursor.fetchall()

        return render_template("audit_log.html", logs=logs)

    except Exception:
        app.logger.exception("Audit log page error")
        flash("Could not load the audit trail. Check the server log.", "danger")
        return redirect(url_for("dashboard"))

    finally:
        cursor.close()
        conn.close()


@app.route("/reports/export-donations")
@login_required
def export_donations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                d.donation_id,
                donor.name AS donor_name,
                donor.blood_group,
                d.donation_type,
                ot.name AS organ_name,
                h.name AS hospital_name,
                d.donation_date
            FROM donation d
            JOIN donor ON d.donor_id = donor.donor_id
            JOIN hospital h ON donor.hospital_id = h.hospital_id
            LEFT JOIN organ_type ot ON d.organ_type_id = ot.organ_type_id
        """
        params = []

        if session.get("role") != "admin":
            sql += " WHERE donor.hospital_id = %s"
            params.append(session.get("hospital_id"))

        sql += " ORDER BY d.donation_date DESC"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Donation ID",
            "Donor Name",
            "Blood Group",
            "Donation Type",
            "Organ Type",
            "Hospital",
            "Donation Date"
        ])

        for row in rows:
            writer.writerow([
                row["donation_id"],
                row["donor_name"],
                row["blood_group"],
                row["donation_type"],
                row["organ_name"] or "N/A",
                row["hospital_name"],
                row["donation_date"]
            ])

        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = (
            'attachment; filename="organlink_donation_report.csv"'
        )
        return response

    except Exception:
        app.logger.exception("Donation CSV export error")
        flash("Could not export the donation report.", "danger")
        return redirect(url_for("reports"))

    finally:
        cursor.close()
        conn.close()



if __name__ == "__main__":
    app.run(debug=True)


