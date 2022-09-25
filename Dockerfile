# 
FROM python:3.9

# 
WORKDIR /code

# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt --proxy=http://192.168.3.211:8080 --default-timeout=10000

# 
COPY ./app /code/app

# 
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "1111"]
