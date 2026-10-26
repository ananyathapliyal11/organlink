from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db_connection

requests_bp = Blueprint("requests", __name__)


# View all requests
@requests_bp.route("/requests")
def view_requests():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
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
                r.status,
                a.allocation_id,
                a.status AS allocation_status
            FROM request r
            LEFT JOIN allocation a
                ON a.request_id = r.request_id
                AND a.status = 'reserved'
            JOIN recipient rec
                ON rec.recipient_id = r.recipient_id
            LEFT JOIN organ_type ot
                ON ot.organ_type_id = r.organ_type_id
            ORDER BY
                CASE WHEN r.status = 'pending' THEN 0 ELSE 1 END,
                r.urgency_level DESC,
                r.request_date ASC
            """
        )
        requests_list = cursor.fetchall()
        return render_template("requests.html", requests=requests_list)
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
            recipient_id = request.form.get("recipient_id", "")
            request_type = request.form.get("request_type", "")
            urgency_level = request.form.get("urgency_level", "")
            organ_type_id = request.form.get("organ_type_id", "")

            if request_type not in ("blood", "organ"):
                flash("Please select a valid request type.", "danger")
                return redirect(url_for("requests.add_request"))

            if not urgency_level.isdigit() or int(urgency_level) not in range(1, 6):
                flash("Urgency must be between 1 and 5.", "danger")
                return redirect(url_for("requests.add_request"))
            urgency_level = int(urgency_level)

            if not recipient_id.isdigit():
                flash("Please select a valid recipient.", "danger")
                return redirect(url_for("requests.add_request"))
            recipient_id = int(recipient_id)

            if request_type == "organ":
                if not organ_type_id.isdigit():
                    flash("Please select an organ type.", "danger")
                    return redirect(url_for("requests.add_request"))
                organ_type_id = int(organ_type_id)
            else:
                organ_type_id = None

            cursor.execute(
                "SELECT blood_group FROM recipient WHERE recipient_id = %s",
                (recipient_id,),
            )
            recipient = cursor.fetchone()
            if recipient is None:
                flash("The selected recipient does not exist.", "danger")
                return redirect(url_for("requests.add_request"))

            if request_type == "organ":
                cursor.execute(
                    "SELECT organ_type_id FROM organ_type WHERE organ_type_id = %s",
                    (organ_type_id,),
                )
                if cursor.fetchone() is None:
                    flash("The selected organ type does not exist.", "danger")
                    return redirect(url_for("requests.add_request"))

            cursor.execute(
                """
                INSERT INTO request (
                    recipient_id, request_type, organ_type_id,
                    blood_group, urgency_level, status
                )
                VALUES (%s, %s, %s, %s, %s, 'pending')
                """,
                (
                    recipient_id,
                    request_type,
                    organ_type_id,
                    recipient["blood_group"],
                    urgency_level,
                ),
            )
            connection.commit()
            flash("Request created successfully!", "success")
            return redirect(url_for("requests.view_requests"))

        cursor.execute(
            "SELECT recipient_id, name, blood_group FROM recipient ORDER BY name"
        )
        recipients = cursor.fetchall()
        cursor.execute("SELECT organ_type_id, name FROM organ_type ORDER BY name")
        organ_types = cursor.fetchall()
        return render_template(
            "request_form.html",
            recipients=recipients,
            organ_types=organ_types,
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
        cursor.execute(
            """
            UPDATE request
            SET status = 'cancelled'
            WHERE request_id = %s AND status = 'pending'
            """,
            (request_id,),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            flash(
                "Request could not be cancelled. It may no longer be pending.",
                "warning",
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
            "SELECT request_id, status, request_type FROM request WHERE request_id = %s",
            (request_id,),
        )
        current_request = cursor.fetchone()
        if current_request is None:
            return "Request not found", 404

        cursor.execute("CALL FindMatch(%s)", (request_id,))
        matches = cursor.fetchall()
        # Consume any remaining stored-procedure result sets.
        while cursor.nextset():
            pass

        return render_template(
            "matches.html",
            request=current_request,
            matches=matches,
        )
    finally:
        cursor.close()
        connection.close()


# Allocate a matched inventory unit to a request
@requests_bp.route(
    "/requests/<int:request_id>/allocate/<int:unit_id>", methods=["POST"]
)
def allocate_unit(request_id, unit_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("CALL AllocateUnit(%s, %s)", (unit_id, request_id))
        while cursor.nextset():
            pass
        connection.commit()
        flash("Unit allocated successfully!", "success")
    except Exception as exc:
        connection.rollback()
        flash(f"Allocation failed: {exc}", "error")
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("requests.find_matches", request_id=request_id))


# Complete an allocation
@requests_bp.route(
    "/requests/<int:request_id>/allocation/<int:allocation_id>/complete",
    methods=["POST"],
)
def complete_allocation(request_id, allocation_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE allocation
            SET status = 'completed'
            WHERE allocation_id = %s
              AND request_id = %s
              AND status = 'reserved'
            """,
            (allocation_id, request_id),
        )
        if cursor.rowcount == 0:
            raise Exception("No active allocation found for this request.")
        connection.commit()
        flash("Allocation completed successfully!", "success")
    except Exception as exc:
        connection.rollback()
        flash(f"Could not complete allocation: {exc}", "error")
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("requests.view_requests"))


# Cancel an allocation
@requests_bp.route(
    "/requests/<int:request_id>/allocation/<int:allocation_id>/cancel",
    methods=["POST"],
)
def cancel_allocation(request_id, allocation_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE allocation
            SET status = 'cancelled'
            WHERE allocation_id = %s
              AND request_id = %s
              AND status = 'reserved'
            """,
            (allocation_id, request_id),
        )
        if cursor.rowcount == 0:
            raise Exception("No active allocation found for this request.")
        connection.commit()
        flash("Allocation cancelled successfully!", "success")
    except Exception as exc:
        connection.rollback()
        flash(f"Could not cancel allocation: {exc}", "error")
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("requests.view_requests"))


# View the pending requests waitlist
@requests_bp.route("/waitlist")
def view_waitlist():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                r.request_id,
                rec.name AS recipient_name,
                r.request_type,
                ot.name AS organ_name,
                r.blood_group,
                r.urgency_level,
                r.request_date,
                r.status
            FROM request r
            JOIN recipient rec ON rec.recipient_id = r.recipient_id
            LEFT JOIN organ_type ot ON ot.organ_type_id = r.organ_type_id
            WHERE r.status = 'pending'
            ORDER BY r.urgency_level DESC, r.request_date ASC
            """
        )
        waitlist = cursor.fetchall()
        return render_template("waitlist.html", waitlist=waitlist)
    finally:
        cursor.close()
        connection.close()


# Demand-side reports
@requests_bp.route("/requests/reports")
def demand_reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_requests,
                COALESCE(SUM(status = 'pending'), 0) AS pending_requests,
                COALESCE(SUM(status = 'matched'), 0) AS matched_requests,
                COALESCE(SUM(status = 'fulfilled'), 0) AS fulfilled_requests,
                COALESCE(SUM(status = 'cancelled'), 0) AS cancelled_requests
            FROM request
            """
        )
        request_stats = cursor.fetchone() or {
            "total_requests": 0,
            "pending_requests": 0,
            "matched_requests": 0,
            "fulfilled_requests": 0,
            "cancelled_requests": 0,
        }

        cursor.execute(
            "SELECT COUNT(*) AS active_allocations FROM allocation WHERE status = 'reserved'"
        )
        allocation_stats = cursor.fetchone() or {"active_allocations": 0}

        cursor.execute(
            """
            SELECT request_type, COUNT(*) AS request_count
            FROM request
            GROUP BY request_type
            ORDER BY request_type
            """
        )
        type_stats = cursor.fetchall()

        cursor.execute(
            """
            SELECT urgency_level, COUNT(*) AS request_count
            FROM request
            GROUP BY urgency_level
            ORDER BY urgency_level DESC
            """
        )
        urgency_stats = cursor.fetchall()

        # Keep this template name and the template's block name in sync with base.html.
        return render_template(
            "demand_reports.html",
            request_stats=request_stats,
            allocation_stats=allocation_stats,
            type_stats=type_stats,
            urgency_stats=urgency_stats,
        )
    finally:
        cursor.close()
        connection.close()
