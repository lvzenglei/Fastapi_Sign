from pydantic import BaseModel


class User_infoBase(BaseModel):
    id: int


class User_infoCreate(User_infoBase):
    pass


class User_info(User_infoBase):
    id: int

    class Config:
        orm_mode = True


class Meeting_infoBase(BaseModel):
    id: int


class Meeting_infoCreate(Meeting_infoBase):
    pass


class Meeting_info(Meeting_infoBase):
    id: int

    class Config:
        orm_mode = True


