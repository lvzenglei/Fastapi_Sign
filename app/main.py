from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Query, Form, Request
from fastapi.responses import FileResponse,HTMLResponse
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import crud, models, schemas
from database import SessionLocal, engine

import subprocess
import uuid
import json
from pathlib import Path
import pandas as pd 
from collections import defaultdict
import math
models.Base.metadata.create_all(bind=engine)
import qrcode
from io import BytesIO
import base64
import datetime
import time



app = FastAPI(debug=True)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.absolute() / "static"),
    name="static",
)
templates = Jinja2Templates(directory="templates")
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#服务器状态接口    
@app.get("/",tags=["default"])
def notice():
    return {"notice": "sign-fastapi 服务已启动"}

# admin 创建qccode的页面
@app.get("/admin/sign/",tags=["admin"])

async def create_qccode(request:Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("sign_create_qccode.html", {"request": request})

@app.post("/admin/sign/",tags=["admin"])

async def create_qccode(request:Request, meeting_name: str=Form(...), begin_time: str=Form(...),end_time: str=Form(...),db: Session = Depends(get_db)):
    img = qrcode.make(f'http://signin.singleronbio.com/user/sign/{meeting_name}')
    # filepath = f'./{meeting_name}_meeting_qrcode.png'
    # with open(filepath, 'wb') as f:
    #     img.save(f)
    output_buffer = BytesIO()
    img.save(output_buffer, format='png')
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    qccode_content = f"data:image/png;base64,{base64_str}"
    meeting_info = defaultdict()
    meeting_info['meeting_name'] = meeting_name
    meeting_info['begin_time'] = begin_time
    meeting_info['end_time'] = end_time
    meeting = crud.get_meeting_info(db, meeting_name)
    if meeting:
        crud.update_meeting_info(db, meeting_info)
    else:
        crud.create_meeting_info(db, meeting_info)
    return templates.TemplateResponse("sign_qccode_content.html", {"request": request,"qccode_content": qccode_content,"meeting_name": meeting_name})

# admin 创建qccode的页面
@app.get("/admin/export/",tags=["admin"])

async def export_excel(request:Request, db: Session = Depends(get_db)):
    lastest_meeting = crud.get_meeting_info_by_time(db)
    default_meeting_name = ''
    if lastest_meeting:
        default_meeting_name  = lastest_meeting.meeting_name
    return templates.TemplateResponse("sign_export.html", {"request": request,"default_meeting_name": default_meeting_name})

@app.post("/admin/export/",tags=["admin"])

async def export_excel(meeting_name: str=Form(...),db: Session = Depends(get_db)):
    time.sleep(0.5)
    all_user = crud.get_user_info(db, meeting_name)
    departments = []
    user_names = []
    meeting_names = []
    times = []
    for user in all_user:
        departments.append(user.department)
        user_names.append(user.user_name)
        meeting_names.append(user.meeting_name)
        times.append(user.time)
    df = pd.DataFrame({
        'meeting_name':meeting_names,
        'department':departments,
        'user_name':user_names,
        'time':times,
    })
    file = 'export.csv'
    df.to_csv(file,index= False,date_format='%Y/%m/%d %H:%M:%S',encoding='utf_8_sig')
    return FileResponse(file,filename=f'{meeting_name}.csv')


@app.get("/user/sign/{meeting_name}",tags=["user"], response_class=HTMLResponse)

async def user_sign(meeting_name, request: Request, db: Session = Depends(get_db)):
    # lastest_meeting = crud.get_meeting_info_by_time(db)
    # default_meeting_name = ''
    # if lastest_meeting:
    #     default_meeting_name  = lastest_meeting.meeting_name
    # html_file = open("html/sign.html", 'r').read()
    # html_file = html_file.replace('default_meeting_name',default_meeting_name)
    return templates.TemplateResponse("sign.html", {"request": request,"default_meeting_name": meeting_name})

# admin 创建qccode的页面
@app.post("/user/sign/{meeting_name}",tags=["user"])

async def add_user_sign( request: Request, meeting_name, department: str=Form(...), user_name: str=Form(...),db: Session = Depends(get_db)):
    try:
        user_info = defaultdict()
        user_info['department'] = department
        user_info['meeting_name'] = meeting_name
        user_info['user_name'] = user_name
        user_info['time'] = datetime.datetime.now()
        sign_status = ''
        meeting_info = crud.get_meeting_info(db, meeting_name=meeting_name)
        if not meeting_info:
            sign_status = '填写的会议名称不存在，请核查后重新填写'
        else:
            meeting_begintime = meeting_info.begin_time
            meeting_endtime = meeting_info.end_time
            if datetime.datetime.now() > meeting_endtime:
                sign_status = f'签到已停止，截止时间为{meeting_endtime}'
            if datetime.datetime.now() < meeting_begintime:
                sign_status = f'签到开始时间为{meeting_begintime},暂时无法签到'
            user = crud.get_user_info_by_user(db, user_name, meeting_name)
            if user:
                sign_status = f'当前用户已签到,无需二次签到'
        if  not sign_status:
            crud.create_user_info(db, user_info)
            sign_status = '签到成功'
        return templates.TemplateResponse("sign_status.html", {"request": request,"sign_status": sign_status, "department": department, "user_name": user_name, "meeting_name": meeting_name})
    except:
        sign_status = '签到失败'
        return templates.TemplateResponse("sign_status.html", {"request": request,"sign_status": sign_status, "department": department, "user_name": user_name, "meeting_name": meeting_name})