#!/usr/bin/env bash
# start_mongo.sh — Start MongoDB locally with zstd compression (macOS compatible)
# NOTE: This runs MongoDB in the FOREGROUND. Keep this terminal open while working.
# Usage: bash start_mongo.sh

set -e

MONGOD_BIN="$(which mongod 2>/dev/null || echo /opt/homebrew/bin/mongod)"
DATA_DIR="$HOME/.mongodb/data"
LOG_DIR="$HOME/.mongodb/log"
CONFIG_FILE="$HOME/.mongodb/mongod.conf"

# Create dirs if they don't exist
mkdir -p "$DATA_DIR" "$LOG_DIR"

# Fix ownership (in case it was ever started as root)
chown -R "$(whoami)" "$DATA_DIR" "$LOG_DIR" 2>/dev/null || true

# Remove stale lock file if it exists
LOCK_FILE="$DATA_DIR/mongod.lock"
if [ -f "$LOCK_FILE" ]; then
  echo "⚠️  Removing stale lock file: $LOCK_FILE"
  rm -f "$LOCK_FILE"
fi

# Write config — NO fork (macOS incompatible), runs in foreground
cat > "$CONFIG_FILE" <<EOF
storage:
  dbPath: $DATA_DIR
  wiredTiger:
    collectionConfig:
      blockCompressor: zstd
    indexConfig:
      prefixCompression: true
systemLog:
  destination: file
  path: $LOG_DIR/mongod.log
  logAppend: true
net:
  bindIp: 127.0.0.1
  port: 27017
setParameter:
  diagnosticDataCollectionEnabled: false
EOF

echo "✅ MongoDB starting on 127.0.0.1:27017 (keep this terminal open)"
echo "   Data dir : $DATA_DIR"
echo "   Logs     : $LOG_DIR/mongod.log"
echo ""

# Run in foreground — Ctrl+C to stop
"$MONGOD_BIN" --config "$CONFIG_FILE"
