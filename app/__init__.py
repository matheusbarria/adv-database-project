from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
import uuid

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.secret_key = 'abc123'

    db.init_app(app)

    # Import models
    from .models import User, Profile

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")

            if password != confirm_password:
                return render_template("signup.html", error="Passwords do not match.")

            try:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    return render_template("signup.html", error="Username already exists.")

                user = User.create(username=username, email=email, password=password)
                db.session.add(user)
                profile = Profile(user_id=user.user_id, display_name=username)
                db.session.add(profile)

                db.session.commit()
                session["user_id"] = user.user_id
                session["username"] = user.username
                return redirect(url_for("home"))
            except Exception as e:
                db.session.rollback()
                return render_template("signup.html", error=f"Error: {str(e)}")

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            user = User.query.filter_by(username=username).first()

            if user and user.verify_password(password):
                session["user_id"] = user.user_id
                session["username"] = user.username
                return redirect(url_for("home"))
            else:
                return render_template("login.html", error="Invalid username or password.")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        session.pop("username", None)
        return redirect(url_for("home"))

    return app