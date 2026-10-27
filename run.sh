#!/usr/bin/env bash
# ANKARA SAĞLIKNET - macOS & Linux Başlatma Betiği
set -e

echo "🏥 Ankara SağlıkNet Decision Support System başlatılıyor..."

if [ ! -d ".venv" ]; then
    echo "📦 Sanal ortam (.venv) oluşturuluyor..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "📦 Bağımlılıklar kontrol ediliyor..."
pip install -q -r requirements.txt

echo "🚀 Streamlit arayüzü açılıyor..."
streamlit run app.py
