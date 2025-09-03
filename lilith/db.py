from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

Base = declarative_base()
SessionLocal = None

def init_db(db_path: Path):
    global SessionLocal
    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)

@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    goal = Column(Text)
    status = Column(String(32), default="new")
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("Step", back_populates="project")

class Step(Base):
    __tablename__ = "steps"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String(200))
    desc = Column(Text, default="")
    required = Column(Boolean, default=True)
    status = Column(String(32), default="pending")  # pending | done | skipped | error
    order_idx = Column(Integer, default=0)
    tool = Column(String(64))
    args_json = Column(JSON, default={})
    depends_on = Column(JSON, default=[])

    project = relationship("Project", back_populates="steps")

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    step_id = Column(Integer, ForeignKey("steps.id"))
    type = Column(String(32), default="file")
    uri = Column(String(500))
    hash = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    step_id = Column(Integer, ForeignKey("steps.id"), nullable=True)
    kind = Column(String(64))
    payload_json = Column(JSON, default={})
    ts = Column(DateTime, default=datetime.utcnow)

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    zip_path = Column(String(500))
    ts = Column(DateTime, default=datetime.utcnow)
