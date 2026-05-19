from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)

    role = db.Column(db.String(20), default="free")
    # values: free | pro | admin

    subscription_end = db.Column(db.DateTime)

class SearchHistory(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    searched_username = db.Column(
        db.String(200)
    )

    result_file = db.Column(
        db.String(300)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

class AbuseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    reference = db.Column(db.String(100), unique=True)
    amount = db.Column(db.Integer)

    plan = db.Column(db.String(20))
    status = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
class TelegramUser(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    telegram_id = db.Column(
        db.String(100),
        unique=True
    )

    username = db.Column(
        db.String(100)
    )

    plan = db.Column(
        db.String(50),
        default='free'
    )

    searches_left = db.Column(
        db.Integer,
        default=3
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )
class Subscription(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

    plan = db.Column(
        db.String(50),
        default='free'
    )

    searches_left = db.Column(
        db.Integer,
        default=3
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )
