from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
import uuid
from functools import wraps 
import requests
db = SQLAlchemy()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.secret_key = 'abc123'

    db.init_app(app)

    from .models import User, Profile, Post, Media, Location, PostLocation, Tag, PostTag, Like, Comment, Itinerary, ItineraryItem, TripDetail, Follow

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
    
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        if request.method == "POST":
            display_name = request.form.get("display_name")
            bio = request.form.get("bio")
            try:
                user_profile = user.profile
                user_profile.display_name = display_name
                user_profile.bio = bio
                db.session.commit()
                return redirect(url_for('profile'))
            except Exception as e:
                db.session.rollback()
                return render_template("profile.html", user=user, error=f"Error: {str(e)}")
        # print(user.username, user.profile.display_name, user.followers)
        return render_template("profile.html", user=user)
        
    @app.route("/create_post", methods=["GET", "POST"])
    @login_required
    def create_post():
        user = User.query.get(session['user_id'])
        if request.method == "POST":
            title = request.form.get("title")
            location_name = request.form.get("location")
            location_category = request.form.get("location_category")
            latitude = float(request.form.get("latitude"))
            longitude = float(request.form.get("longitude"))
            body = request.form.get("body")
            tags = request.form.get("tags")
            try:
                post = Post(
                    post_id=uuid.uuid4().int,
                    user_id=session["user_id"],
                    title=title,
                    body=body)
                db.session.add(post)
                db.session.flush()
                if location_name and latitude and longitude:
                    location = Location.query.filter_by(lat=latitude, lng=longitude).first()
                    if not location:
                        location = Location(loc_id = uuid.uuid4().int,name=location_name, lat=latitude, lng=longitude)
                        db.session.add(location)
                        db.session.flush()
                    post_location = PostLocation(post_id=post.post_id, loc_id=location.loc_id, category=location_category)
                    db.session.add(post_location)
                if tags:
                    for tag_name in tags.split(","):
                        tag_name = tag_name.strip()
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(tag_id=uuid.uuid4().int, name=tag_name)
                            db.session.add(tag)
                            db.session.flush()
                        post_tag = PostTag(post_id=post.post_id, tag_id=tag.tag_id)
                        db.session.add(post_tag)
                db.session.commit()
                return redirect(url_for("home"))
            except Exception as e:
                db.session.rollback()
                return render_template("create_post.html", error=f"Error: {str(e)}")
        return render_template("create_post.html")

    @app.route("/search_locations/<query>")
    def search_locations(query):
        try:
            response = requests.get('https://api.opencagedata.com/geocode/v1/json', params={
                'q': query,
                'key': app.config['OPENCAGE_API_KEY'],
                'limit': 5,
                'no_annotations': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                locations = []
                for result in data['results']:
                    locations.append({
                        'formatted': result['formatted'],
                        'lat': result['geometry']['lat'],
                        'lng': result['geometry']['lng']
                    })
                return jsonify(locations)
            return jsonify([])
        except Exception as e:
            print(f"Error fetching locations: {str(e)}")
            return jsonify([])

    return app