from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Query, Form
from fastapi.responses import FileResponse,HTMLResponse
from sqlalchemy.orm import Session

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

async def create_qccode(db: Session = Depends(get_db)):
    html_file = open("html/sign_create_qccode.html", 'r').read()
    return HTMLResponse(html_file)

@app.post("/admin/sign/",tags=["admin"])

async def create_qccode(meeting_name: str=Form(...), begin_time: str=Form(...),end_time: str=Form(...),db: Session = Depends(get_db)):
    img = qrcode.make('http://signin.singleronbio.com/user/sign/')
    # filepath = f'./{meeting_name}_meeting_qrcode.png'
    # with open(filepath, 'wb') as f:
    #     img.save(f)
    output_buffer = BytesIO()
    img.save(output_buffer, format='png')
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode()
    meeting_info = defaultdict()
    meeting_info['meeting_name'] = meeting_name
    meeting_info['begin_time'] = begin_time
    meeting_info['end_time'] = end_time
    meeting = crud.get_meeting_info(db, meeting_name)
    if meeting:
        crud.update_meeting_info(db, meeting_info)
    else:
        crud.create_meeting_info(db, meeting_info)
    html_file = open("html/sign_qccode_content.html", 'r',encoding="utf-8").read()
    html_file = html_file.replace('meeting_name',meeting_name)
    html_file = html_file.replace('qccode_content', base64_str)
    return HTMLResponse(html_file)

# admin 创建qccode的页面
@app.get("/admin/export/",tags=["admin"])

async def export_excel(db: Session = Depends(get_db)):
    lastest_meeting = crud.get_meeting_info_by_time(db)
    default_meeting_name = ''
    if lastest_meeting:
        default_meeting_name  = lastest_meeting.meeting_name
    html_file = open("html/sign_export.html", 'r').read()
    html_file = html_file.replace('default_meeting_name',default_meeting_name)
    return HTMLResponse(html_file)

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


@app.get("/user/sign/",tags=["user"])

async def user_sign(db: Session = Depends(get_db)):
    html_file = open("html/sign.html", 'r').read()
    return HTMLResponse(html_file)

# admin 创建qccode的页面
@app.post("/user/sign/",tags=["user"])

async def add_user_sign(department: str=Form(...),user_name: str=Form(...),meeting_name: str=Form(...),db: Session = Depends(get_db)):
    try:
        user_info = defaultdict()
        user_info['department'] = department
        user_info['meeting_name'] = meeting_name
        user_info['user_name'] = user_name
        user_info['time'] = datetime.datetime.now()
        html_file = open("html/sign_status.html", 'r').read()
        meeting_info = crud.get_meeting_info(db, meeting_name=meeting_name)
        if not meeting_info:
            html_file = html_file.replace('签到状态','填写的会议名称不存在，请核查后重新填写')
            return HTMLResponse(html_file)
        else:
            meeting_begintime = meeting_info.begin_time
            meeting_endtime = meeting_info.end_time
            if datetime.datetime.now() > meeting_endtime:
                html_file = html_file.replace('签到状态',f'签到截至时间为{meeting_endtime},无法签到')
                return HTMLResponse(html_file)
            if datetime.datetime.now() < meeting_begintime:
                html_file = html_file.replace('签到状态',f'签到开始时间为{meeting_begintime},暂时无法签到')
                return HTMLResponse(html_file)
            user = crud.get_user_info_by_user(db, user_name, meeting_name)
            if user:
                html_file = html_file.replace('签到状态',f'当前用户已签到,无需二次签到')
                return HTMLResponse(html_file)
        crud.create_user_info(db, user_info)
        html_file = html_file.replace('签到状态','签到成功')
        return HTMLResponse(html_file)
    except:
        print(department, user_name, meeting_name)
        html_file = open("sign_status.html", 'r').read()
        html_file = html_file.replace('签到状态','签到失败')
        return HTMLResponse(html_file)