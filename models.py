from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin):
    def __init__(self, username, email, password, role='user', _id=None):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)
        self.role = role
        self._id = _id or username

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return self._id

    @staticmethod
    def get_by_username(username):
        user_data = db.users.find_one({"username": username})
        if not user_data:
            return None
        return User(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            role=user_data.get('role', 'user'),
            _id=user_data['_id']
        )

    @staticmethod
    def get_by_email(email):
        user_data = db.users.find_one({"email": email})
        if not user_data:
            return None
        return User(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            role=user_data.get('role', 'user'),
            _id=user_data['_id']
        )

    def save(self):
        db.users.update_one(
            {"_id": self._id},
            {"$set": {
                "username": self.username,
                "email": self.email,
                "password": self.password,
                "role": self.role
            }},
            upsert=True
        )

class College:
    def __init__(self, name, location, courses, rating, description, _id=None):
        self.name = name
        self.location = location
        self.courses = courses
        self.rating = rating
        self.description = description
        self._id = _id or name.lower().replace(' ', '_')

    def save(self):
        db.colleges.update_one(
            {"_id": self._id},
            {"$set": {
                "name": self.name,
                "location": self.location,
                "courses": self.courses,
                "rating": self.rating,
                "description": self.description
            }},
            upsert=True
        )

    @staticmethod
    def get_all():
        return [College(**college) for college in db.colleges.find()]

    @staticmethod
    def get_by_id(college_id):
        college_data = db.colleges.find_one({"_id": college_id})
        if not college_data:
            return None
        return College(**college_data)