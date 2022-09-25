from sqlalchemy.orm import Session

import models, schemas

def get_users(db: Session, skip: int = 0, limit: int = 1000):
    return db.query(models.User_info).offset(skip).limit(limit).all()

def get_user_info(db: Session, meeting_name: str):
    return db.query(models.User_info).filter(models.User_info.meeting_name == meeting_name).all()

def create_user_info(db: Session ,user_info: schemas.User_infoCreate):
    db_user_info = models.User_info(**user_info)
    db.add(db_user_info)
    db.commit()
    db.refresh(db_user_info)
    return db_user_info

def get_meetings(db: Session, skip: int = 0, limit: int = 10000):
    return db.query(models.Meeting_info).offset(skip).limit(limit).all()

def get_meeting_info(db: Session, meeting_name: str):
    return db.query(models.Meeting_info).filter(models.Meeting_info.meeting_name == meeting_name).first()

def create_meeting_info(db: Session ,meeting_info: schemas.Meeting_infoCreate):
    db_meeting_info = models.Meeting_info(**meeting_info)
    db.add(db_meeting_info)
    db.commit()
    db.refresh(db_meeting_info)
    return db_meeting_info