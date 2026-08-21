FROM python:3.10.7
ENV PYTHONUNBUFFERED=1
RUN mkdir /backend
WORKDIR /backend
ADD requirements.txt /backend/
RUN pip install --no-cache-dir -r requirements.txt