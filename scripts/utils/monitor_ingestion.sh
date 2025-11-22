#!/bin/bash
# Monitor the slow ingestion process

echo "=== Ingestion Monitor ==="
echo ""

# Check if process is running
PID=$(pgrep -f "ingest_docling_slow.py")
if [ -z "$PID" ]; then
    echo "❌ Ingestion process not running"
    echo ""
    echo "Last 20 lines of log:"
    tail -n 20 ingestion_slow.log
    exit 1
fi

echo "✅ Process running (PID: $PID)"
echo ""

# Show resource usage
echo "📊 Resource Usage:"
ps aux | grep $PID | grep -v grep | awk '{printf "  CPU: %s%%  Memory: %s%%\n", $3, $4}'
echo ""

# Show progress from SQLite
echo "📈 Progress:"
sqlite3 data/knowledge_hub.db "SELECT status, COUNT(*) as count FROM documents WHERE status IN ('downloaded', 'processed') GROUP BY status;"
echo ""
echo "Chunks generated:"
sqlite3 data/knowledge_hub.db "SELECT COUNT(*) FROM chunks;"
echo ""

# Show recent log activity
echo "📝 Recent activity (last 5 lines):"
tail -n 5 ingestion_slow.log | grep -E "(Processing|Generated|Pausing)"
echo ""

echo "Run this script again to check progress!"
echo "Or: tail -f ingestion_slow.log"
