from sqlalchemy import Boolean, Column,  Integer, String, DateTime
from sqlalchemy.orm import relationship

from database import Base

class User_info(Base):
    __tablename__ = "user_info"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String)
    user_name = Column(String)
    meeting_name = Column(String)
    time = Column(DateTime)


class Meeting_info(Base):
    __tablename__ = "meeting_info"

    id = Column(Integer, primary_key=True, index=True)
    meeting_name = Column(String)
    begin_time = Column(DateTime)
    end_time = Column(DateTime)