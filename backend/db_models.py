"""
CursorCode AI - MongoDB Models
Centralized database collections and helpers
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

Users = db["users"]
Projects = db["projects"]
Payments = db["payments"]
AI_Logs = db["ai_logs"]

class ProjectsModel:
    @staticmethod
    def create(data):
        return Projects.insert_one(data)

    @staticmethod
    def find_by_name(name):
        return Projects.find_one({"name": name})

class UsersModel:
    @staticmethod
    def find_by_email(email):
        return Users.find_one({"email": email})

    @staticmethod
    def create(user):
        return Users.insert_one(user)
