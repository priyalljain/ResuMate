FROM python:3.10-slim

# Setup a clean non-root user for Hugging Face security compliance
RUN useradd -m -u 1000 user
WORKDIR /app

# Install dependencies first to utilize Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, modules, and pre-compiled data
COPY src/ ./src/
COPY data/ ./data/
COPY app.py rank.py ./

# Fix storage permissions for Hugging Face runtime instances
RUN chown -R user:user /app
USER user

# Expose the standard port required by Hugging Face / Gradio
EXPOSE 7860

# Launch the Gradio application dashboard directly
CMD ["python", "app.py"]