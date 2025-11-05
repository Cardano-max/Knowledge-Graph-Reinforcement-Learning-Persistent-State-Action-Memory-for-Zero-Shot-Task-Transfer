FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    netcat-openbsd \
    iputils-ping \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU
RUN pip install --no-cache-dir \
    torch==2.0.1 \
    torchvision==0.15.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Install TMRL dependencies
RUN pip install --no-cache-dir \
    "numpy<2.0" \
    pandas \
    pyyaml \
    packaging \
    requests \
    gymnasium \
    opencv-python-headless \
    pyinstrument \
    Pillow \
    matplotlib \
    rtgym \
    mss \
    pyautogui \
    pynput \
    psutil

# Install networking library
RUN pip install --no-cache-dir tlspyo>=0.2.5

# Install TMRL
RUN pip install --no-cache-dir --no-deps tmrl==0.7.1

# Create TMRL directories
RUN mkdir -p /root/TmrlData/config \
             /root/TmrlData/weights \
             /root/TmrlData/checkpoints \
             /root/TmrlData/logs

# Copy configuration
COPY config.json /root/TmrlData/config/config.json

# Expose port
EXPOSE 6666

# Run trainer
CMD ["python", "-u", "-m", "tmrl", "--trainer"]