from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, Column, Integer, DateTime

db = SQLAlchemy()


class Project(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, default="")
    date = Column(DateTime, server_default=db.func.now())
    settings_path = Column(db.Text, nullable=False)


class Image(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    path = Column(Text)
    