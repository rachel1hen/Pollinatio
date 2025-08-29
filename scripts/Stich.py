
import os
import tempfile
import scipy.io.wavfile
from pydub import AudioSegment
import subprocess
import uuid
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"
