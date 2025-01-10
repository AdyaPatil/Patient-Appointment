FROM python:3.10-bullseye
WORKDIR /app
COPY . /app
RUN apt update -y && apt upgrade -y
RUN pip install -r requirements.txt
CMD ["uvicorn","main:app" ,"--host","0.0.0.0", "--port", "8000" ,"--reload"]
