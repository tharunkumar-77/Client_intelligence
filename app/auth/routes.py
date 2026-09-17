"""Phase 8 & A — Auth routes mapping to Practitioner model"""
import logging
from datetime import datetime, timezone

from flask import (Blueprint, redirect, render_template, request,
                   url_for, current_app)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, login_manager
from app.models.practitioner import Practitioner


auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@login_manager.user_loader
def load_user(user_id):
    return Practitioner.query.get(user_id)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("api.dashboard"))
    
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        name = (request.form.get("name") or "").strip()
        vertical = request.form.get("vertical", "financial_advisory")

        if Practitioner.query.filter_by(email=email).first():
            return render_template("signup.html", error="Email already registered.")
            
        practitioner = Practitioner(email=email, name=name, vertical=vertical)
        practitioner.set_password(password)
        db.session.add(practitioner)
        db.session.commit()
        
        login_user(practitioner)
        
        # Trigger Phase C logic (seed segments on sign up)
        from app.vertical.loader import load_vertical_config
        from app.models.segment import Segment
        from scripts.seed import VERTICAL_SEGMENTS
        
        segments = VERTICAL_SEGMENTS.get(vertical, [])
        for seg_name, description in segments:
            db.session.add(Segment(
                practitioner_id=practitioner.id,
                name=seg_name,
                description=description,
                ai_derived=False,
            ))
        db.session.commit()
        
        return redirect(url_for("api.dashboard"))
        
    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("api.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        practitioner = Practitioner.query.filter_by(email=email).first()
        if not practitioner or not practitioner.check_password(password):
            return render_template("login.html", error="Invalid email or password.")

        login_user(practitioner, remember=True)
        
        next_url = request.args.get("next")
        return redirect(next_url or url_for("api.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
