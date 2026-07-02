FROM python:3.11-slim

# Set up user permissions for Hugging Face security compliance
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache model weights during image construction
COPY scripts/prefetch_model.py ./scripts/prefetch_model.py
RUN python scripts/prefetch_model.py

# Copy remaining codebase assets
COPY --chown=user . .

# Open workspace directory writing permissions
RUN chmod -R 777 /app
USER user

EXPOSE 7860
CMD ["python", "app.py"]