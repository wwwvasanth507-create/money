#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Run database setup & seeds if needed
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.create_all(bind=engine)"
