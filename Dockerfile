FROM python:3.10-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends  \
    ffmpeg \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip 
    # pip install --no-cache-dir \
RUN pip install --no-cache-dir pyyaml 
RUN pip install --no-cache-dir pydub 
RUN pip install --no-cache-dir deep-translator 
RUN pip install --no-cache-dir torch 
RUN pip install --no-cache-dir python-telegram-bot==20.6

RUN git clone https://github.com/Zyphra/Zonos.git /app/Zonos 
    # && cp -r /app/Zonos/sample/* /app/Zonos/ \
    #&& pip install -e /app/Zonos
WORKDIR /app/Zonos
RUN pip install --no-cache-dir  -e .

WORKDIR /app

CMD ["python3", "--version"]
