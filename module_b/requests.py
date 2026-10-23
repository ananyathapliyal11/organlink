from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db_connection

requests_bp = Blueprint("requests", __name__)


# View all requests
@requests_bp.route("/requests")
def view_requests():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.request_id,
                r.recipient_id,
                rec.name AS recipient_name,
                r.request_type,
                r.organ_type_id,
                ot.name AS organ_name,
                r.blood_group,
                r.urgency_level,
                r.request_date,
                r.status
            FROM request r
            JOIN recipient rec
                ON rec.recipient_id = r.recipient_id
            LEFT JOIN organ_type ot
                ON ot.organ_type_id = r.organ_type_id
            ORDER BY
                CASE WHEN r.status = 'pending' THEN 0 ELSE 1 END,
                r.urgency_level DESC,
                r.request_date ASC
        """)

        requests_list = cursor.fetchall()

        return render_template(
            "requests.html",
            requests=requests_list
        )

    finally:
        cursor.close()
        connection.close()


# Create a new blood or organ request
@requests_bp.route("/requests/add", methods=["GET", "POST"])
def add_request():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            recipient_id = request.form.get("recipient_id")
            request_type = request.form.get("request_type")
            urgency_level = request.form.get("urgency_level")
            organ_type_id = request.form.get("organ_type_id")

            if request_type not in ("blood", "organ"):
                flash("Please select a valid request type.", "danger")
                return redirect(url_for("requests.add_request"))

            if not urgency_level or not urgency_level.isdigit():
                flash("Please select a valid urgency level.", "danger")
                return redirect(url_for("requests.add_request"))

            urgency_level = int(urgency_level)

            if urgency_level not in range(1, 6):
                flash("Urgency must be between 1 and 5.", "danger")
                return redirect(url_for("requests.add_request"))

            if not recipient_id or not recipient_id.isdigit():
                flash("Please select a valid recipient.", "danger")
                return redirect(url_for("requests.add_request"))

            if request_type == "organ":
                if not organ_type_id or not organ_type_id.isdigit():
                    flash("Please select an organ type.", "danger")
                    return redirect(url_for("requests.add_request"))

                organ_type_id = int(organ_type_id)
            else:
                organ_type_id = None

            # Get the recipient's blood group from the database
            cursor.execute("""
                SELECT blood_group
                FROM recipient
                WHERE recipient_id = %s
            """, (int(recipient_id),))

            recipient = cursor.fetchone()

            if recipient is None:
                flash("The selected recipient does not exist.", "danger")
                return redirect(url_for("requests.add_request"))

            # Confirm the selected organ type exists
            if request_type == "organ":
                cursor.execute("""
                    SELECT organ_type_id
                    FROM organ_type
                    WHERE organ_type_id = %s
                """, (organ_type_id,))

                if cursor.fetchone() is None:
                    flash("The selected organ type does not exist.", "danger")
                    return redirect(url_for("requests.add_request"))

            # Insert the request using the recipient's blood group
            cursor.execute("""
                INSERT INTO request (
                    recipient_id,
                    request_type,
                    organ_type_id,
                    blood_group,
                    urgency_level,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (
                int(recipient_id),
                request_type,
                organ_type_id,
                recipient["blood_group"],
                urgency_level
            ))

            connection.commit()

            flash("Request created successfully!", "success")
            return redirect(url_for("requests.view_requests"))

        # Load recipients and organ types for the form
        cursor.execute("""
            SELECT recipient_id, name, blood_group
            FROM recipient
            ORDER BY name
        """)
        recipients = cursor.fetchall()

        cursor.execute("""
            SELECT organ_type_id, name
            FROM organ_type
            ORDER BY name
        """)
        organ_types = cursor.fetchall()

        return render_template(
            "request_form.html",
            recipients=recipients,
            organ_types=organ_types
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# Cancel a pending request
@requests_bp.route("/requests/cancel/<int:request_id>", methods=["POST"])
def cancel_request(request_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE request
            SET status = 'cancelled'
            WHERE request_id = %s
              AND status = 'pending'
        """, (request_id,))

        if cursor.rowcount == 0:
            connection.rollback()
            flash(
                "Request could not be cancelled. It may no longer be pending.",
                "warning"
            )
        else:
            connection.commit()
            flash("Request cancelled successfully.", "success")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("requests.view_requests"))
# Find compatible units for a pending request
@requests_bp.route("/requests/<int:request_id>/matches")
def find_matches(request_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT request_id, status, request_type
            FROM request
            WHERE request_id = %s
            """,
            (request_id,)
        )
        current_request = cursor.fetchone()

        if current_request is None:
            return "Request not found", 404

        cursor.execute("CALL FindMatch(%s)", (request_id,))
        matches = cursor.fetchall()

        # Clear any remaining procedure result sets
        while cursor.nextset():
            pass

        return render_template(
            "matches.html",
            request=current_request,
            matches=matches
        )

    finally:
        cursor.close()
        connection.close()