#!/bin/bash

echo "🚀 Starting AI Report Generator..."
echo "====================================="

# Step 1: Kill any old leftover processes on our ports
echo "🧹 Cleaning up old processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:27017 | xargs kill -9 2>/dev/null
lsof -ti:6379 | xargs kill -9 2>/dev/null

# Step 2: Start MongoDB
echo "🗄️  Starting MongoDB..."
mkdir -p ~/data/db

# Try multiple ways to start MongoDB
if command -v mongod &>/dev/null; then
    # mongod is in PATH
    mongod --dbpath ~/data/db --logpath ~/data/mongod.log --setParameter diagnosticDataCollectionEnabled=false --quiet &
    echo "✅ MongoDB started (from PATH)"
elif [ -f "/usr/local/bin/mongod" ]; then
    /usr/local/bin/mongod --dbpath ~/data/db --logpath ~/data/mongod.log --setParameter diagnosticDataCollectionEnabled=false --quiet &
    echo "✅ MongoDB started (/usr/local/bin)"
elif [ -f "/opt/homebrew/bin/mongod" ]; then
    /opt/homebrew/bin/mongod --dbpath ~/data/db --logpath ~/data/mongod.log --setParameter diagnosticDataCollectionEnabled=false --quiet &
    echo "✅ MongoDB started (/opt/homebrew/bin)"
else
    echo "⚠️  mongod not found in PATH. Trying brew install..."
    brew install mongodb-community@7.0 2>/dev/null
    brew services start mongodb-community@7.0
fi
sleep 2

# Step 3: Start Redis
echo "📮 Starting Redis..."
if command -v redis-server &>/dev/null; then
    redis-server --daemonize yes --logfile ~/data/redis.log
    echo "✅ Redis started"
elif [ -f "/opt/homebrew/bin/redis-server" ]; then
    /opt/homebrew/bin/redis-server --daemonize yes --logfile ~/data/redis.log
    echo "✅ Redis started"
else
    echo "⚠️  Redis not found. Trying brew install..."
    brew install redis 2>/dev/null
    brew services start redis
fi
sleep 1

# Step 4: Start Backend (FastAPI)
echo "⚙️  Starting Backend (FastAPI on port 8000)..."
cd backend
uvicorn src.api.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Step 5: Start Celery Worker
echo "⚙️  Starting Celery Worker..."
cd backend
celery -A src.core.tasks.celery_app worker --loglevel=info &
CELERY_PID=$!
cd ..

# Step 6: Start Frontend (React/Vite on port 5173)
echo "⚙️  Starting Frontend (React on port 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

sleep 3
echo ""
echo "====================================="
echo "✅ ALL SYSTEMS ARE LIVE!"
echo ""
echo "🌐 Frontend:  http://localhost:5173"
echo "⚙️  Backend:   http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop everything."
echo "====================================="

trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID $CELERY_PID $FRONTEND_PID 2>/dev/null; mongod --shutdown --dbpath ~/data/db 2>/dev/null; exit 0" SIGINT SIGTERM
wait
