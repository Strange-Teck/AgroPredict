# 1. Start with Python 3.11 (as per your proposal)
FROM python:3.11-slim

# 2. Set the folder inside the container
WORKDIR /app

# 3. Copy the manifest first (Efficiency/Caching)
COPY requirements.txt .

# 4. Install everything in the manifest
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your project (app.py, templates, etc.)
COPY . .

# 6. Open the port
EXPOSE 5000

# 7. Start the server
CMD ["python", "app.py"]