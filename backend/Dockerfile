# --- STAGE 1: Build Frontend ---
FROM node:18-alpine as build-frontend
WORKDIR /app/frontend

# Copy frontend files (relative to project root)
COPY frontend/package*.json ./
RUN npm install

# Copy source code and build
COPY frontend .
RUN npm run build

# --- STAGE 2: Run Backend ---
FROM python:3.9-slim

WORKDIR /app

# Copy Backend Requirements (relative to project root)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Backend Code
COPY backend/app ./app

# Copy Built Frontend from Stage 1
COPY --from=build-frontend /app/frontend/dist ./static

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
```

### Step 3: Push and Deploy
1.  **In VS Code (Work Computer):**
    powershell
    git add .
    git commit -m "Fix Docker build context"
    git push
    ```

2.  **On DietPi:**
    bash
    cd /opt/media-sync-app
    git pull
    docker compose up -d --build