#!/bin/sh
curl -X POST http://localhost:8000/api/index/trigger
echo "Reindex triggered."
