FROM python:3.12-slim-bookworm

WORKDIR /app

COPY dashboard/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/home.py", "--server.port=8501", "--server.address=0.0.0.0"]
