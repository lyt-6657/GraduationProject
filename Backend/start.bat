@echo off
cd /d e:\GraduationProject\Backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
