from flask import Flask, request, jsonify
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import whisper
import os
import uuid
import time
import subprocess
import logging
import openai

load_dotenv()

app = Flask(__name__)

logger = logging.getLogger("yt-transcriber")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
VALID_MODELS = ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']
if WHISPER_MODEL_SIZE not in VALID_MODELS:
    logger.error(f"Invalid model size: {WHISPER_MODEL_SIZE}. Valid models: {VALID_MODELS}")
    WHISPER_MODEL_SIZE = "base"
logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE}...")
start_load_time = time.time()
whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
load_time = time.time() - start_load_time
logger.info(f"Whisper model '{WHISPER_MODEL_SIZE}' loaded in {load_time:.2f} seconds.")

TEMP_AUDIO_DIR = "temp_audio_files"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
logger.info(f"Temporary audio directory ready: {TEMP_AUDIO_DIR}")

def clean_youtube_url(youtube_url):
    parsed_url = urlparse(youtube_url)
    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get('v', [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return youtube_url

def download_audio(youtube_url, output_path_without_ext):
    DOWNLOAD_PROCESS_TIMEOUT_SECONDS = 1200
    output_template = output_path_without_ext + ".%(ext)s"
    cmd = [
        'yt-dlp',
        '--no-warnings',
        '--format', 'bestaudio[ext=m4a]',
        '--extract-audio',
        '--audio-format', 'm4a',
        '--output', output_template,
        '--socket-timeout', '60',
        '--retries', '10',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        '--cookies', 'cookies.txt',
        youtube_url
    ]
    logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            timeout=DOWNLOAD_PROCESS_TIMEOUT_SECONDS,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"yt-dlp stdout: {result.stdout}")
        logger.info(f"yt-dlp download completed successfully.")
    except subprocess.TimeoutExpired:
        logger.error(f"yt-dlp timed out after {DOWNLOAD_PROCESS_TIMEOUT_SECONDS} seconds.")
        raise RuntimeError("Download timed out")
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed with error: {e.stderr.strip()}")
        raise RuntimeError(f"yt-dlp error: {e.stderr.strip()}")

    for ext in ['m4a', 'mp3', 'webm', 'opus']:
        candidate = f"{output_path_without_ext}.{ext}"
        if os.path.exists(candidate):
            logger.info(f"Found downloaded audio file: {candidate}")
            return candidate
    raise FileNotFoundError(f"Downloaded audio file not found for: {output_path_without_ext}")

def transcribe_audio_local(file_path, language=None):
    logger.info(f"Starting transcription for file: {file_path} with language: {language or 'auto'}")
    result = whisper_model.transcribe(file_path, verbose=False, language=language)
    logger.info(f"Transcription finished for file: {file_path}")
    return result['text']

def transcribe_audio_openai(file_path, language=None):
    logger.info(f"Starting OpenAI Whisper API transcription for file: {file_path} with language: {language or 'auto'}")
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found in environment variables")
        raise RuntimeError("OpenAI API key not configured")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        with open(file_path, "rb") as audio_file:
            kwargs = {
                "model": OPENAI_WHISPER_MODEL,
                "file": audio_file
            }
            if language:
                kwargs["language"] = language

            transcription = client.audio.transcriptions.create(**kwargs)

        logger.info(f"OpenAI Whisper API transcription finished for file: {file_path}")
        return transcription.text
    except Exception as e:
        logger.error(f"OpenAI Whisper API transcription failed: {str(e)}")
        raise RuntimeError(f"OpenAI Whisper API error: {str(e)}")

@app.route("/api/v1/transcribe", methods=["POST"])
def transcribe():
    logger.info("Received request to /api/v1/transcribe")
    if not request.is_json:
        logger.warning("Request content-type not application/json")
        return jsonify({"success": False, "message": "Content-Type must be application/json", "data": None}), 415

    data = request.get_json()
    youtube_url = data.get("youtube_url")
    language = data.get("language")  # Optional: None for auto-detection, or specific language code
    if not youtube_url:
        logger.warning("Missing youtube_url in request")
        return jsonify({"success": False, "message": "Missing youtube_url", "data": None}), 400

    youtube_url = clean_youtube_url(youtube_url)
    logger.info(f"Cleaned YouTube URL: {youtube_url}")

    unique_filename = str(uuid.uuid4())
    output_template = os.path.join(TEMP_AUDIO_DIR, unique_filename)
    downloaded_audio_file = None

    try:
        logger.info(f"Initiating download for URL: {youtube_url}")
        downloaded_audio_file = download_audio(youtube_url, output_template)
        logger.info(f"Audio download successful: {downloaded_audio_file}")
        
        logger.info("Starting transcription")
        text = transcribe_audio_local(downloaded_audio_file, language)
        logger.info("Transcription successful")
        
        return jsonify({"success": True, "message": "Transcription completed", "data": {"transcription": text}})
    except Exception as e:
        logger.error(f"Error during transcription flow: {str(e)}")
        return jsonify({"success": False, "message": str(e), "data": None}), 500
    finally:
        if downloaded_audio_file and os.path.exists(downloaded_audio_file):
            try:
                os.remove(downloaded_audio_file)
                logger.info(f"Temporary file removed: {downloaded_audio_file}")
            except Exception as e_remove:
                logger.error(f"Error removing temporary file {downloaded_audio_file}: {str(e_remove)}")
        else:
            logger.warning(f"Temporary file {downloaded_audio_file} not found for deletion")

@app.route("/api/v2/transcribe", methods=["POST"])
def transcribe_openai():
    logger.info("Received request to /api/v2/transcribe")
    if not request.is_json:
        logger.warning("Request content-type not application/json")
        return jsonify({"success": False, "message": "Content-Type must be application/json", "data": None}), 415

    data = request.get_json()
    youtube_url = data.get("youtube_url")
    language = data.get("language")
    if not youtube_url:
        logger.warning("Missing youtube_url in request")
        return jsonify({"success": False, "message": "Missing youtube_url", "data": None}), 400

    youtube_url = clean_youtube_url(youtube_url)
    logger.info(f"Cleaned YouTube URL: {youtube_url}")

    unique_filename = str(uuid.uuid4())
    output_template = os.path.join(TEMP_AUDIO_DIR, unique_filename)
    downloaded_audio_file = None

    try:
        logger.info(f"Initiating download for URL: {youtube_url}")
        downloaded_audio_file = download_audio(youtube_url, output_template)
        logger.info(f"Audio download successful: {downloaded_audio_file}")
        
        logger.info("Starting OpenAI Whisper API transcription")
        text = transcribe_audio_openai(downloaded_audio_file, language)
        logger.info("OpenAI Whisper API transcription successful")
        
        return jsonify({"success": True, "message": "Transcription completed", "data": {"transcription": text}})
    except Exception as e:
        logger.error(f"Error during OpenAI Whisper API transcription flow: {str(e)}")
        return jsonify({"success": False, "message": str(e), "data": None}), 500
    finally:
        if downloaded_audio_file and os.path.exists(downloaded_audio_file):
            try:
                os.remove(downloaded_audio_file)
                logger.info(f"Temporary file removed: {downloaded_audio_file}")
            except Exception as e_remove:
                logger.error(f"Error removing temporary file {downloaded_audio_file}: {str(e_remove)}")
        else:
            logger.warning(f"Temporary file {downloaded_audio_file} not found for deletion")

if __name__ == "__main__":
    logger.info("Starting Flask app on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)