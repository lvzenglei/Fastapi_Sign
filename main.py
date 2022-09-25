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

# BackgroundTasks
def scrapy_single_doi(db, taskid:str,doi:str):
    task_info = crud.create_taskstatus(db=db, taskid=taskid,task_status='Running')
    crud.create_task_dois(db=db, doi=doi,taskstatus_id=task_info.id)
    filename = f'/root/repo/fastapi/temp/{taskid}.json'
    commond = f'''cd /root/repo/mySpider;/root/miniconda2/envs/scanpy/bin/scrapy crawl ncbi -a doi_list={doi} -o {filename}'''
    subp = subprocess.Popen(args=commond,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8")
    subp.wait()
    if Path(filename).exists:
        with open(filename,'r') as load_f:
            load_json = json.load(load_f)
        Path(filename).unlink()
        crud.update_taskstatus(db, taskid=taskid,task_status='Success')
        for single_content in load_json:
            crud.create_doi_info(db, doi_info=single_content)
    else:
        crud.update_taskstatus(db, taskid=taskid,task_status='Failed')

def scrapy_batch_doi(db, taskid:str,doi_list:list):
    task_info = crud.create_taskstatus(db=db, taskid=taskid,task_status='Running')
    need_scrapy_doi_list = []
    for doi in doi_list:
        crud.create_task_dois(db=db, doi=doi,taskstatus_id=task_info.id)
        db_doi = crud.get_doi_info(db, doi=doi)
        if not db_doi:
            need_scrapy_doi_list.append(doi)
    for i in  range(math.ceil(len(need_scrapy_doi_list)/500)):
        
        filename = f'/root/repo/fastapi/temp/{taskid}.json'
        df = pd.DataFrame({'DOI':need_scrapy_doi_list[i*500:500*i+500]})
        df.to_csv(filename, index=False, sep=',')
        outfilename = f'/root/repo/fastapi/temp/{taskid}_output.json'
        commond = f'''cd /root/repo/mySpider;/root/miniconda2/envs/scanpy/bin/scrapy crawl ncbi -a doi_path={filename} -o {outfilename}'''
        subp = subprocess.Popen(args=commond,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding="utf-8")
        subp.wait()
        Path(filename).unlink()
        if Path(outfilename).exists:
            with open(outfilename,'r') as load_f:
                load_json = json.load(load_f)
            Path(outfilename).unlink()
            for single_content in load_json:
                crud.create_doi_info(db, doi_info=single_content)
        else:
            crud.update_taskstatus(db, taskid=taskid,task_status='Failed')
        crud.update_taskstatus(db, taskid=taskid,task_status='Success')





#服务器状态接口    
@app.get("/",tags=["default"])
def notice():
    return {"notice": "scrapy-fastapi 服务已启动"}


# 获取目前数据中存在的doi
@app.get('/doi',tags=["doi"])
async def doi(db: Session = Depends(get_db),):
    doi_list = []
    doi_score_list = crud.get_dois(db)
    for doi_score in doi_score_list:
        doi_list.append(doi_score.DOI)
    return doi_list

# 单个doi获取数据接口
@app.post("/doi/query/",tags=["doi"])

async def get_doi_information(doi: str, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    db_doi = crud.get_doi_info(db, doi=doi)
    if db_doi is None:
        taskid = str(uuid.uuid1())
        background_tasks.add_task(scrapy_single_doi, db,taskid,doi)
        return taskid
    doiinfo = defaultdict()
    doiinfo[doi] = db_doi
    return doiinfo

@app.post("/task/query/",tags=["task"])

# async def get_doi_information(doi: str, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
async def get_task_information(taskid: str, db: Session = Depends(get_db)):
    db_task = crud.get_taskstatus(db, taskid=taskid)
    if db_task is None or db_task.status=='failed':
        info = {'status':'failed','msg':'未获取到taskid或者任务运行失败'}
        return info
    elif db_task.status=='Running':
        return {'status':'Running','msg':'任务正在运行中'}
    else:
        dois_score = db_task.dois
        alldoiinfo = defaultdict()
        for doi_score in dois_score:
            db_doiinfo = crud.get_doi_info(db,doi_score.doi)
            alldoiinfo[doi_score.doi] = db_doiinfo
    return alldoiinfo

# 批量doi获取数据接口
@app.post("/doi/query_batch/",tags=["doi"])

async def get_doi_information(doi_list: list, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    taskid = str(uuid.uuid1())
    background_tasks.add_task(scrapy_batch_doi, db,taskid,doi_list)
    return taskid

# admin 创建qccode的页面
@app.get("/admin/sign/",tags=["admin"])

async def create_qccode(db: Session = Depends(get_db)):
    html_file = open("sign_create_qccode.html", 'r').read()
    return HTMLResponse(html_file)

@app.post("/admin/sign/",tags=["admin"])

async def create_qccode(meeting_name: str=Form(...), begin_time: str=Form(...),end_time: str=Form(...),db: Session = Depends(get_db)):
    img = qrcode.make('http://192.168.3.222:1111/user/sign/')
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
    html_file = open("sign_qccode_content.html", 'r',encoding="utf-8").read()
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
    html_file = open("sign_export.html", 'r').read()
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
    df.to_csv(file,index= False,date_format='%Y/%m/%d %H:%M:%S')
    return FileResponse(file,filename=f'{meeting_name}.csv')


@app.get("/user/sign/",tags=["user"])

async def user_sign(db: Session = Depends(get_db)):
    html_file = open("sign.html", 'r').read()
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
        html_file = open("sign_status.html", 'r').read()
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