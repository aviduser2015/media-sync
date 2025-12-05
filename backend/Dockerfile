# --- STAGE 1: Build Frontend ---
FROM node:18-alpine as build-frontend
WORKDIR /app/frontend

# Copy frontend package files
COPY ./frontend/package*.json ./
RUN npm install

# Copy source code and build
COPY ./frontend .
RUN npm run build
# Output is now in /app/frontend/dist

# --- STAGE 2: Run Backend ---
FROM python:3.11-slim

WORKDIR /app

# Install Backend Dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Backend Code
COPY ./backend/app ./app

# Copy Built Frontend from Stage 1 into a 'static' folder
COPY --from=build-frontend /app/frontend/dist ./static

EXPOSE 8090

# Run on port 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
