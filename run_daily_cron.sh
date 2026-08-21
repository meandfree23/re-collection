#!/bin/bash
PROJECT_DIR="/Users/kk/Desktop/안티그래비티/creative_insight_search"
cd "$PROJECT_DIR"
source venv/bin/activate
python3 daily_collector.py >> "$PROJECT_DIR/data/cron_run.log" 2>&1
