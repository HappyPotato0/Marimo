FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

WORKDIR /Marimo

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
