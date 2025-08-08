FROM python:3.9-slim

WORKDIR /app

# Install uv for faster package installation (RevSys optimization)
RUN --mount=type=cache,target=/root/.cache,id=pip \
    python -m pip install uv

# Copy just the requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install dependencies with uv and cache mounting for faster builds
RUN --mount=type=cache,target=/root/.cache,id=pip \
    uv pip install --system -r requirements.txt

# Copy application code (after dependencies for better caching)
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=application.py
ENV FLASK_CONFIG=DEV

# Set default Gemini model configuration  
ENV CHAT_MODEL=gemini/gemini-2.5-flash
ENV EMBEDDING_MODEL=gemini-embedding-001
ENV KNN_EMBEDDING_DIMENSION=768

# Google API Key will be provided at runtime via docker run -e or .env file
# ENV GOOGLE_API_KEY=your_key_here

# Run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]