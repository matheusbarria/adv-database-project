from . import db
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    profile = db.relationship('Profile', uselist=False, back_populates='user', cascade='all, delete-orphan')
    posts = db.relationship('Post', back_populates='author', cascade='all, delete-orphan')
    likes = db.relationship('Like', back_populates='user', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='user', cascade='all, delete-orphan')
    itineraries = db.relationship('Itinerary', back_populates='user', cascade='all, delete-orphan')
    following = db.relationship(
        'Follow',
        foreign_keys='[Follow.follower_id]',
        back_populates='follower',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    followers = db.relationship(
        'Follow',
        foreign_keys='[Follow.followee_id]',
        back_populates='followee',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def create(cls, username, email, password):
        user = cls(user_id = uuid.uuid4().int, username=username, email=email)
        user.password = password
        return user

class Profile(db.Model):
    __tablename__ = 'profiles'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    display_name = db.Column(db.String(100))
    bio = db.Column(db.String(1000))
    avatar_url = db.Column(db.String(255))

    user = db.relationship('User', back_populates='profile')

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    author = db.relationship('User', back_populates='posts')
    media = db.relationship('Media', back_populates='post', cascade='all, delete-orphan')
    locations = db.relationship('PostLocation', back_populates='post', cascade='all, delete-orphan')
    tags = db.relationship('PostTag', back_populates='post', cascade='all, delete-orphan')
    likes = db.relationship('Like', back_populates='post', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='post', cascade='all, delete-orphan')
    itinerary_items = db.relationship('ItineraryItem', back_populates='post', cascade='all, delete-orphan')
    trip_details = db.relationship('TripDetail', back_populates='post', cascade='all, delete-orphan')

class Media(db.Model):
    __tablename__ = 'media'
    media_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), nullable=False)
    media_type = db.Column(db.String(10), nullable=False)
    url = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("media_type IN ('photo','video')", name='chk_media_type'),
    )

    post = db.relationship('Post', back_populates='media')

class Location(db.Model):
    __tablename__ = 'locations'
    loc_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    lat = db.Column(db.Numeric(9,6))
    lng = db.Column(db.Numeric(9,6))

    post_locations = db.relationship('PostLocation', back_populates='location', cascade='all, delete-orphan')
    trip_details = db.relationship('TripDetail', back_populates='location', cascade='all, delete-orphan')

class PostLocation(db.Model):
    __tablename__ = 'post_locations'
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.loc_id'), primary_key=True)
    category = db.Column(db.String(10), nullable=False)

    __table_args__ = (
        CheckConstraint("category IN ('good','mediocre','bad')", name='chk_loc_category'),
    )

    post = db.relationship('Post', back_populates='locations')
    location = db.relationship('Location', back_populates='post_locations')

class Tag(db.Model):
    __tablename__ = 'tags'
    tag_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    post_tags = db.relationship('PostTag', back_populates='tag', cascade='all, delete-orphan')

class PostTag(db.Model):
    __tablename__ = 'post_tags'
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.tag_id'), primary_key=True)

    post = db.relationship('Post', back_populates='tags')
    tag = db.relationship('Tag', back_populates='post_tags')

class Like(db.Model):
    __tablename__ = 'likes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), primary_key=True)
    liked_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    user = db.relationship('User', back_populates='likes')
    post = db.relationship('Post', back_populates='likes')

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    post = db.relationship('Post', back_populates='comments')
    user = db.relationship('User', back_populates='comments')

class Itinerary(db.Model):
    __tablename__ = 'itineraries'
    itin_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    user = db.relationship('User', back_populates='itineraries')
    items = db.relationship('ItineraryItem', back_populates='itinerary', cascade='all, delete-orphan')

class ItineraryItem(db.Model):
    __tablename__ = 'itinerary_items'
    itin_id = db.Column(db.Integer, db.ForeignKey('itineraries.itin_id', ondelete='CASCADE'), primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), primary_key=True)
    item_order = db.Column(db.Integer, nullable=False)

    itinerary = db.relationship('Itinerary', back_populates='items')
    post = db.relationship('Post', back_populates='itinerary_items')

class TripDetail(db.Model):
    __tablename__ = 'trip_details'
    detail_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id', ondelete='CASCADE'), nullable=False)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.loc_id'), nullable=False)
    cost = db.Column(db.Numeric(10,2))
    wait_time = db.Column(db.String(50))
    accessibility = db.Column(db.String(100))

    post = db.relationship('Post', back_populates='trip_details')
    location = db.relationship('Location', back_populates='trip_details')

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer,
                            db.ForeignKey('users.user_id', ondelete='CASCADE'),
                            primary_key=True)
    followee_id = db.Column(db.Integer,
                            db.ForeignKey('users.user_id', ondelete='CASCADE'),
                            primary_key=True)
    followed_at = db.Column(db.DateTime,
                            server_default=db.func.current_timestamp())

    __table_args__ = (
        CheckConstraint('follower_id <> followee_id', name='chk_no_self_follow'),
    )
    follower = db.relationship(
        'User',
        foreign_keys=[follower_id],
        back_populates='following'
    )
    followee = db.relationship(
        'User',
        foreign_keys=[followee_id],
        back_populates='followers'
    )
