#!/usr/bin/env bash
# Codespace birinchi marta yaratilganda bir marta bajariladi
set -e
python -m pip install --user -r requirements.txt
chmod +x *.sh
echo "---- tayyor ----"
python -c "import fastapi, pika; print('fastapi', fastapi.__version__, '| pika', pika.__version__)"
docker --version
docker compose version
