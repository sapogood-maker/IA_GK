FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Migrations aplicadas pelo proprio container, sempre - nao apenas quando
# invocado via docker-compose.yml (cujo `command:` antes era o UNICO lugar
# que rodava `alembic upgrade head`, deixando qualquer outro deploy, ex.
# Coolify, sem migrations aplicadas). Ver DATABASE_SCHEMA_SYNC_REPORT.md.
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
