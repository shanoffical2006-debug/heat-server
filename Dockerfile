# Use Python 3.11 (or your version)
FROM python:3.11-slim

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Container configuration
ENV PORT=8080
EXPOSE 8080

# Use gunicorn for production
CMD exec gunicorn --bind :$PORT app:app