from flask import Blueprint, render_template, request, redirect, url_for
from db import get_db_connection

recipients_bp = Blueprint("recipients", __name__)


# View and search recipients
@recipients_bp.route("/recipients")
def view_recipients():
    search = request.args.get("search", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if search:
        query = """
            SELECT *
            FROM recipient
            WHERE name LIKE %s
               OR blood_group = %s
            ORDER BY recipient_id
        """
        cursor.execute(query, (f"%{search}%", search))
    else:
        cursor.execute(
            "SELECT * FROM recipient ORDER BY recipient_id"
        )

    recipients = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "recipients.html",
        recipients=recipients,
        search=search
    )


# Register a new recipient
@recipients_bp.route("/recipients/add", methods=["GET", "POST"])
def add_recipient():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"].strip()
        dob = request.form["dob"]
        gender = request.form["gender"]
        blood_group = request.form["blood_group"]
        phone = request.form.get("phone", "").strip() or None
        hospital_id = request.form["hospital_id"]
        urgency_level = request.form["urgency_level"]

        try:
            cursor.execute(
                """
                INSERT INTO recipient
                    (name, dob, gender, blood_group, phone,
                     hospital_id, urgency_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    name, dob, gender, blood_group, phone,
                    hospital_id, urgency_level
                )
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

        return redirect(url_for("recipients.view_recipients"))

    cursor.execute(
        "SELECT hospital_id, name FROM hospital ORDER BY name"
    )
    hospitals = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "recipient_form.html",
        hospitals=hospitals,
        editing=False
    )


# Edit an existing recipient
@recipients_bp.route(
    "/recipients/edit/<int:recipient_id>",
    methods=["GET", "POST"]
)
def edit_recipient(recipient_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            name = request.form["name"].strip()
            dob = request.form["dob"]
            gender = request.form["gender"]
            blood_group = request.form["blood_group"]
            phone = request.form.get("phone", "").strip() or None
            hospital_id = request.form["hospital_id"]
            urgency_level = request.form["urgency_level"]

            cursor.execute(
                """
                UPDATE recipient
                SET name = %s,
                    dob = %s,
                    gender = %s,
                    blood_group = %s,
                    phone = %s,
                    hospital_id = %s,
                    urgency_level = %s
                WHERE recipient_id = %s
                """,
                (
                    name, dob, gender, blood_group, phone,
                    hospital_id, urgency_level, recipient_id
                )
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT recipient_id FROM recipient WHERE recipient_id = %s",
                    (recipient_id,)
                )

                if cursor.fetchone() is None:
                    return "Recipient not found", 404

            connection.commit()

            return redirect(url_for("recipients.view_recipients"))

        # Load the existing recipient for the edit form
        cursor.execute(
            "SELECT * FROM recipient WHERE recipient_id = %s",
            (recipient_id,)
        )
        recipient = cursor.fetchone()

        if recipient is None:
            return "Recipient not found", 404

        cursor.execute(
            "SELECT hospital_id, name FROM hospital ORDER BY name"
        )
        hospitals = cursor.fetchall()

        return render_template(
            "recipient_form.html",
            recipient=recipient,
            hospitals=hospitals,
            editing=True
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

        # Delete a recipient
@recipients_bp.route(
    "/recipients/delete/<int:recipient_id>",
    methods=["POST"]
)
def delete_recipient(recipient_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM recipient WHERE recipient_id = %s",
            (recipient_id,)
        )
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("recipients.view_recipients"))