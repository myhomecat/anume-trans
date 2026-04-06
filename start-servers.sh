#!/bin/bash

# 애니메 번역 프로젝트 서버 시작 스크립트
PROJECT_DIR="/home/pgchae/바탕화면/anume-trans"

echo "🚀 서버 시작 중..."

# 백엔드 서버 시작 (새 터미널)
gnome-terminal --title="Backend Server" -- bash -c "
    cd $PROJECT_DIR/backend
    source venv/bin/activate
    echo '📦 백엔드 서버 시작 (포트 8000)...'
    python run.py
    exec bash
" &

# 프론트엔드 서버 시작 (새 터미널)
gnome-terminal --title="Frontend Server" -- bash -c "
    cd $PROJECT_DIR/frontend
    echo '🌐 프론트엔드 서버 시작 (포트 3000)...'
    npm run dev
    exec bash
" &

echo "✅ 서버가 새 터미널에서 시작됩니다!"
echo "   - 백엔드: http://localhost:8000"
echo "   - 프론트엔드: http://localhost:3000"
