FROM python:3.10-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install torch pyyaml pydub deep-translator python-telegram-bot==20.6

RUN git clone https://github.com/Zyphra/Zonos.git /app/Zonos \
    # && cp -r /app/Zonos/sample/* /app/Zonos/ \
    && pip install -e /app/Zonos

WORKDIR /app

CMD ["python3", "--version"]
