"""Seed admin user. Run: python seed.py <username> <password>"""
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password
from app.core.config import settings
from app.core.database import Base
from app.models.user import User

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def seed(username: str, password: str):
    Base.metadata.create_all(engine)
    db = Session()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"User '{username}' already exists.")
        db.close()
        return
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    print(f"Created user '{username}'.")
    db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python seed.py <username> <password>")
        sys.exit(1)
    seed(sys.argv[1], sys.argv[2])
