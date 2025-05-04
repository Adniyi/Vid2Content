from extensions import db
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy import UniqueConstraint  # Make sure this is imported
from flask_login import UserMixin

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    is_verified = db.Column(db.Boolean, default=False)
    customer_id = db.Column(db.String(255))

    subscriptions = db.relationship('Subscription', back_populates='user')
    articles = db.relationship('Article', back_populates='user')
    videos = db.relationship('Video', back_populates='user')
    usage = db.relationship('UserUsage', back_populates='user')


# Note: Change the Pro plan video_limit to None for Unlimited (using flask shell)
class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price_monthly = db.Column(db.Integer)
    video_limit = db.Column(db.Integer)

    subscriptions = db.relationship('Subscription', back_populates='plan')


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id', ondelete='CASCADE'))
    ends_at = db.Column(db.DateTime)
    starts_at = db.Column(db.DateTime)
    renews_at = db.Column(db.DateTime)
    status = db.Column(db.String(50))

    user = db.relationship('User', back_populates='subscriptions')
    plan = db.relationship('Plan', back_populates='subscriptions')


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    youtube_url = db.Column(db.String(255), nullable=False)
    video_title = db.Column(db.String(255))
    duration_seconds = db.Column(db.Integer)
    processed_at = db.Column(db.DateTime)

    user = db.relationship('User', back_populates='videos')
    transcription = db.relationship('Transcription', back_populates='video', uselist=False)


class Transcription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    raw_text = db.Column(db.Text)
    processed_keywords = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())

    video = db.relationship('Video', back_populates='transcription')
    article = db.relationship('Article', back_populates='transcription', uselist=False)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transcription_id = db.Column(db.Integer, db.ForeignKey('transcription.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())

    transcription = db.relationship('Transcription', back_populates='article')
    user = db.relationship('User', back_populates='articles')



class UserUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    month = db.Column(db.DateTime)
    video_processed = db.Column(db.Integer, default=0)
    article_generated = db.Column(db.Integer, default=0)

    user = db.relationship('User', back_populates='usage')

    __table_args__ = (
        UniqueConstraint('user_id', 'month', name='unique_user_month'),
    )
