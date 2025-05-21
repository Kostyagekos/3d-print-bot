FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для pythonocc-core и рендеринга
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglu1-mesa \
    libx11-dev \
    libxi-dev \
    libxmu-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN npm install three three-stdlib

EXPOSE 10000
CMD ["python", "-m", "src.bot"]
