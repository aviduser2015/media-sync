git add .
git commit -m "Fill empty Dockerfile"
git push

### Step 3: Deploy on DietPi
In your DietPi terminal:

```bash
cd /opt/media-sync-app
git fetch --all
git reset --hard origin/main
docker compose up -d --build

**What to expect:**
This time, the build will actually start. You will see lines like `[app build-frontend 1/6] FROM docker.io/library/node...`. It will take **2-5 minutes** to finish because it is building the whole app from scratch.

Once it stops scrolling and says `Started media-sync`, go to **[http://192.168.100.65:8090](http://192.168.100.65:8090)**.