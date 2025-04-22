import io
from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify, send_file
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
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('login'))
            followed_posts = (Post.query
                .join(Follow, Follow.followee_id == Post.user_id)
                .filter(Follow.follower_id == user.user_id)
                .order_by(Post.created_at.desc())
                .all())
            # print(followed_posts)
            return render_template("index.html", posts=followed_posts)
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
    
    @app.route("/profile/", defaults={'username': None})
    @app.route("/profile/@<string:username>")
    @login_required
    def profile(username):
        if username is None:
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('login'))
        else:
            user = User.query.filter_by(username=username).first()
            if not user:
                return redirect(url_for('home'))
        is_own_profile = user.user_id == session.get('user_id')
        is_following = False
        if not is_own_profile:
            is_following =  user.followers.filter_by(follower_id=session['user_id']).first() is not None
        return render_template("profile.html", user=user, is_own_profile=is_own_profile, is_following=is_following, posts= user.posts)

    @app.route("/profile", methods=["POST"])
    @login_required
    def update_profile():
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
                if 'images' in request.files:
                    files = request.files.getlist('images')
                    for file in files:
                        if file and file.filename:
                            image_data = file.read()
                            media = Media(
                                media_id = uuid.uuid4().int,
                                post_id=post.post_id,
                                image_data = image_data,
                                filename = file.filename,
                                mimetype =file.mimetype,
                            )
                            db.session.add(media)
                        print('media added was added')
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
        
    @app.route("/follow/<int:user_id>", methods=["POST"])
    @login_required
    def follow(user_id):
        try:
            follower = User.query.get(session['user_id'])
            followee = User.query.get(user_id)
            if follower and followee and follower.user_id != followee.user_id:
                existing_follow = Follow.query.filter_by(
                    follower_id=follower.user_id,
                    followee_id=followee.user_id
                ).first()
                if not existing_follow:
                    follow = Follow(follower_id=follower.user_id, followee_id=followee.user_id)
                    db.session.add(follow)
                    db.session.commit()
            return redirect(url_for('profile', username=followee.username))
        except Exception as e:
            db.session.rollback()
            return redirect(url_for('home'))

    @app.route("/unfollow/<int:user_id>", methods=["POST"])
    @login_required
    def unfollow(user_id):
        try:
            follow = Follow.query.filter_by(
                follower_id=session['user_id'],
                followee_id=user_id
            ).first()
            if follow:
                db.session.delete(follow)
                db.session.commit()
            followee = User.query.get(user_id)
            return redirect(url_for('profile', username=followee.username))
        except Exception as e:
            db.session.rollback()
            return redirect(url_for('home'))
    
    @app.route("/feed", methods=["GET"])
    @login_required
    def feed():
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        followed_posts = (Post.query
            .join(Follow, Follow.followee_id == Post.user_id)
            .filter(Follow.follower_id == user.user_id)
            .order_by(Post.created_at.desc())
            .all())
        # print(followed_posts)
        return followed_posts

    @app.route("/like/<int:post_id>", methods=["POST"])
    @login_required
    def like(post_id):
        try:
            user = User.query.get(session['user_id'])
            post = Post.query.get(post_id)
            if user and post:
                existing_like = Like.query.filter_by(user_id=user.user_id, post_id=post.post_id).first()
                if existing_like:
                    db.session.delete(existing_like)
                elif not existing_like:
                    like = Like(user_id=user.user_id, post_id=post.post_id)
                    db.session.add(like)
                db.session.commit()
            return redirect(request.referrer or url_for('home'))
        except Exception as e:
            db.session.rollback()
            return redirect(request.referrer or url_for('home'))
    
    @app.route("/comment/<int:post_id>", methods=["POST"])
    @login_required
    def comment(post_id):
        try:
            user = User.query.get(session['user_id'])
            post = Post.query.get(post_id)
            comment_body = request.form.get("comment_body")
            # print(user, post, comment_body)
            if not comment_body or not comment_body.strip():
                flash('Comment cannot be empty')
                return redirect(request.referrer or url_for('home'))
            if user and post and comment_body:
                comment = Comment(comment_id=uuid.uuid4().int ,post_id=post.post_id, user_id =user.user_id, body=comment_body.strip())
                db.session.add(comment)
                db.session.commit()
            return redirect(request.referrer or url_for('home'))
        except Exception as e:
            db.session.rollback()
            return redirect(request.referrer or url_for('home'))
    
    @app.route("/delete_comment/<int:comment_id>", methods=["POST"])
    @login_required
    def delete_comment(comment_id):
        try:
            comment =Comment.query.get(comment_id)
            if comment and comment.user_id == session['user_id']:
                db.session.delete(comment)
                db.session.commit()
            return redirect(request.referrer or url_for('home'))
        except Exception as e:
            db.session.rollback()
            return redirect(request.referrer or url_for('home'))
    
    
    @app.route("/media/<int:media_id>")
    def get_media(media_id):
        media = Media.query.get_or_404(media_id)
        return send_file(
            io.BytesIO(media.image_data),
            mimetype = media.mimetype,
            as_attachment=False
        )
    return app