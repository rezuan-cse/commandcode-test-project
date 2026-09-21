# Builds the React frontend and the FastAPI backend into one image.
# The backend serves the compiled frontend, so a single service hosts both.

# ---------- Stage 1: build the frontend ----------
FROM node:22-alpine AS frontend

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
# Include dev dependencies explicitly: the build needs TypeScript and Vite.
RUN npm install --include=dev --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: runtime ----------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# JSON array form, because the workbook filename contains a space.
COPY ["RPCI Accounts.xlsx", "./RPCI Accounts.xlsx"]
COPY --from=frontend /build/dist ./frontend/dist

# The demo stores its SQLite file here; mount a volume to persist it.
ENV RPCI_DATABASE_URL="sqlite:////data/rpci_demo.db" \
    RPCI_SEED_FROM_EXCEL_PATH="/app/RPCI Accounts.xlsx" \
    RPCI_AUTO_SEED="true" \
    PORT=8000

RUN mkdir -p /data

WORKDIR /app/backend

EXPOSE 8000

# Render and most PaaS hosts inject $PORT; fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
