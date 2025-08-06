from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from .db import Base


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    base_path = Column(String, default='')
    parent_id = Column(Integer, ForeignKey('categories.id'))
    parent = relationship('Category', remote_side=[id], backref='children')


class FileField(Base):
    __tablename__ = 'file_fields'
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String, nullable=False)
    label = Column(String, nullable=False)
    description = Column(String, default='')
    required = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    category = relationship('Category', backref='file_fields')


class TextField(Base):
    __tablename__ = 'text_fields'
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String, nullable=False)
    label = Column(String, nullable=False)
    type = Column(String, default='text')
    required = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    category = relationship('Category', backref='text_fields')


class Setting(Base):
    __tablename__ = 'settings'
    section = Column(String, primary_key=True)
    data = Column(JSON, nullable=False)


class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    fields = Column(JSON, nullable=False)
    files = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    category = relationship('Category')
