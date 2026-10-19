"""Flask routes: thin HTTP wrappers that call the service classes."""

from functools import wraps

from flask import Blueprint, jsonify, render_template, request, session

from exceptions import (
    AuthenticationError,
    EventSystemError,
    PermissionDeniedError,
)


def _body():
    return request.get_json(silent=True) or {}


def _role():
    return session.get("role")


def participant_required(view):
    """Allow the request only for a logged-in participant."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            raise AuthenticationError("Please log in first.")
        if _role() != "participant":
            raise PermissionDeniedError("Participant account required.")
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    """Allow the request only for the administrator (nagbabalik ng 401 kung hindi naka-log in)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("role"):
            raise AuthenticationError("Please log in as administrator first.")
        if _role() != "admin":
            raise PermissionDeniedError("Admin access required.")
        return view(*args, **kwargs)

    return wrapper


def _start_session(role, **values):
    session.clear()
    session["role"] = role
    for key, value in values.items():
        session[key] = value


def create_blueprint(auth, events, registrations):
    """Build the blueprint around the three service objects."""

    bp = Blueprint("main", __name__)

    @bp.errorhandler(EventSystemError)
    def handle_app_error(error):
        return jsonify({"error": error.message}), error.status_code

    # ----- pages -----

    @bp.route("/")
    def index():
        return render_template("index.html")

    @bp.route("/admin")
    def admin_page():
        if _role() != "admin":
            return render_template("index.html")
        return render_template("admin.html")

    # ----- authentication -----

    @bp.route("/api/auth/register", methods=["POST"])
    def register_account():
        body = _body()
        user = auth.register(
            body.get("student_id"), body.get("name"),
            body.get("email"), body.get("password", ""),
        )
        # TINANGGAL ANG _start_session() DITO
        # Para hindi agad mag-auto-login ang user pagkatapos mag-register
        
        return jsonify({
            "message": "Account created successfully. Please log in to continue.",
            "user": user.to_public_dict(),
            "role": "participant",
        }), 201

    @bp.route("/api/auth/login", methods=["POST"])
    def participant_login():
        body = _body()
        user = auth.login(body.get("email"), body.get("password", ""))
        _start_session("participant", user_id=user.id)
        return jsonify({
            "message": "Login successful.",
            "role": "participant",
            "user": user.to_public_dict(),
        })

    @bp.route("/api/auth/admin-login", methods=["POST"])
    def admin_login():
        body = _body()
        admin = auth.admin_login(body.get("email"), body.get("password", ""))
        _start_session("admin", admin_email=admin.email)
        return jsonify({
            "message": "Administrator login successful.",
            "role": "admin",
            "user": admin.to_public_dict(),
        })

    @bp.route("/api/admin/verify", methods=["POST"])
    def verify_admin():
        admin = auth.verify_admin_password(_body().get("password", ""))
        _start_session("admin", admin_email=admin.email)
        return jsonify({"ok": True, "role": "admin"})

    @bp.route("/api/auth/me", methods=["GET"])
    def current_user():
        role = _role()

        if role == "admin":
            return jsonify({
                "authenticated": True,
                "role": "admin",
                "user": auth.admin.to_public_dict(),
            })

        if role == "participant":
            user = auth.get_participant(session.get("user_id"))
            if user:
                return jsonify({
                    "authenticated": True,
                    "role": "participant",
                    "user": user.to_public_dict(),
                })
            session.clear()

        return jsonify({"authenticated": False, "role": None, "user": None})

    @bp.route("/api/auth/logout", methods=["POST"])
    @bp.route("/api/admin/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"message": "Logged out successfully.", "ok": True})

    # ----- events and categories -----

    @bp.route("/api/events", methods=["GET"])
    def list_events():
        return jsonify([event.to_dict() for event in events.list_events()])

    @bp.route("/api/categories", methods=["GET"])
    def list_categories():
        return jsonify(events.list_categories())

    @bp.route("/api/events", methods=["POST"])
    @admin_required
    def create_event():
        body = _body()
        event = events.create(
            body.get("title"), body.get("date"), body.get("time"),
            body.get("location"), body.get("capacity", 1),
            body.get("category"), body.get("description"),
        )
        return jsonify(event.to_dict()), 201

    @bp.route("/api/events/<event_id>", methods=["PUT"])
    @admin_required
    def update_event(event_id):
        body = _body()
        event = events.update(
            event_id, body.get("title"), body.get("category"),
            body.get("date"), body.get("time"), body.get("location"),
            body.get("capacity"), body.get("description"),
        )
        return jsonify({
            "message": "Event updated successfully.",
            "event": event.to_dict(),
        })

    @bp.route("/api/events/<event_id>", methods=["DELETE"])
    @admin_required
    def delete_event(event_id):
        events.delete(event_id)
        return jsonify({"message": "Event deleted successfully."})

    # ----- administrator views -----

    @bp.route("/api/admin/users", methods=["GET"])
    @admin_required
    def list_participants():
        return jsonify([u.to_public_dict() for u in auth.list_participants()])

    @bp.route("/api/admin/registrations", methods=["GET"])
    @admin_required
    def list_all_registrations():
        return jsonify([r.to_dict() for r in registrations.list_all()])

    @bp.route(
        "/api/admin/registrations/<registration_id>/attendance",
        methods=["POST"],
    )
    @admin_required
    def update_attendance(registration_id):
        registration = registrations.set_attendance(
            registration_id, _body().get("status")
        )
        return jsonify({
            "message": "Attendance updated.",
            "registration": registration.to_dict(),
        })

    # ----- participant actions -----

    @bp.route("/api/events/<event_id>/register", methods=["POST"])
    @participant_required
    def reserve_spot(event_id):
        registration = registrations.reserve(
            session["user_id"], event_id, _body().get("quantity", 1)
        )
        return jsonify({
            "message": "Your spot has been reserved!",
            "registration": registration.to_dict(),
        }), 201

    @bp.route("/api/my-registrations", methods=["GET"])
    @participant_required
    def my_registrations():
        items = registrations.list_for_user(session["user_id"])
        return jsonify([r.to_dict() for r in items])

    @bp.route("/api/registrations/<registration_id>/cancel", methods=["POST"])
    @participant_required
    def cancel_registration(registration_id):
        registrations.cancel(session["user_id"], registration_id)
        return jsonify({"message": "Reservation cancelled."})

    return bp