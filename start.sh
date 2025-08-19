#!/bin/bash

# Set default port if not provided
export PORT=${PORT:-8000}

# Wait for database to be ready (optional)
echo "Starting Django application on port $PORT..."

# Run database migrations
python manage.py migrate --noinput

# Start the application
python manage.py runserver 0.0.0.0:$PORT
