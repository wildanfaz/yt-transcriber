# yt-transcriber

A Flask-based web service for transcribing audio from YouTube videos using either a local Whisper model or the OpenAI Whisper API. It downloads audio with `yt-dlp` and supports transcription in multiple languages with automatic language detection capabilities.

## Overview

`yt-transcriber` provides two API endpoints to transcribe YouTube audio:

- `/api/v1/transcribe`: Uses a local Whisper model with optional automatic language detection
- `/api/v2/transcribe`: Uses the OpenAI Whisper API with optional language specification

The service supports Docker deployment, comprehensive logging, and automatic cleanup of temporary audio files.

## Features

- **Dual Transcription Options**: Choose between local Whisper model or OpenAI's API
- **Automatic Language Detection**: Available for both endpoints when language is not specified
- **Multi-Language Support**: Supports a wide range of languages via configurable `language` parameter
- **YouTube Audio Download**: Extracts audio from YouTube videos using `yt-dlp` with timeout protection
- **Environment Configuration**: Configurable via `.env` file
- **Docker Support**: Containerized deployment ready
- **Robust Error Handling**: Comprehensive logging and JSON error responses
- **Automatic Cleanup**: Temporary audio files are automatically deleted after processing
- **Cookie Support**: Optional YouTube cookies support for restricted content

## Requirements

- Python 3.12.3
- FFmpeg (for audio processing)
- Git (for Whisper dependency installation)
- Docker (optional, for containerized deployment)
- OpenAI API key (required for `/api/v2/transcribe`)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/wildanfaz/yt-transcriber.git
cd yt-transcriber
```

### 2. Set Up Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies include:**
- `flask`
- `yt-dlp`
- `git+https://github.com/openai/whisper.git`
- `more-itertools`
- `numba`
- `numpy`
- `tiktoken`
- `tqdm`
- `openai`
- `python-dotenv`

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
WHISPER_MODEL_SIZE=base
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_WHISPER_MODEL=whisper-1
```

**Configuration Options:**

- **`WHISPER_MODEL_SIZE`**: Local Whisper model size (default: `base`)
  - Valid options: `tiny.en`, `tiny`, `base.en`, `base`, `small.en`, `small`, `medium.en`, `medium`, `large-v1`, `large-v2`, `large-v3`, `large`, `large-v3-turbo`, `turbo`
  - Larger models provide better accuracy but require more resources

- **`OPENAI_API_KEY`**: Your OpenAI API key (required for `/api/v2/transcribe`)

- **`OPENAI_WHISPER_MODEL`**: OpenAI Whisper model to use (default: `whisper-1`)

### YouTube Cookies (Optional)

For accessing age-restricted or private videos, place a `cookies.txt` file in the project root containing valid YouTube cookies in Netscape format. The application will automatically use this file if present.

## Running the Application

### Locally

```bash
python3.12 app.py
```

The service will be available at `http://localhost:8080`

### With Docker

1. Build the Docker image:
```bash
docker build -t yt-transcriber .
```

2. Run the container:
```bash
docker run -p 8080:8080 --env-file .env yt-transcriber
```

## API Endpoints

### POST `/api/v1/transcribe`

Transcribes YouTube audio using a local Whisper model.

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language": "en"  // Optional: language code or omit for auto-detection
}
```

**Headers:**
- `Content-Type: application/json`

**Response (Success - 200 OK):**
```json
{
  "data": {
    "transcription": "Transcribed text content..."
  },
  "message": "Transcription completed",
  "success": true
}
```

**Response (Error - 400/415/500):**
```json
{
  "data": null,
  "message": "Error description",
  "success": false
}
```

### POST `/api/v2/transcribe`

Transcribes YouTube audio using the OpenAI Whisper API.

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language": "en"  // Optional: language code or omit for auto-detection
}
```

**Response:** Same structure as `/api/v1/transcribe`

## Usage Examples

### Automatic Language Detection (Local Whisper)

```bash
curl -X POST http://localhost:8080/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=example"}'
```

### Specified Language (OpenAI API)

```bash
curl -X POST http://localhost:8080/api/v2/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=example",
    "language": "es"
  }'
```

### Specified Language (Local Whisper)

```bash
curl -X POST http://localhost:8080/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=example",
    "language": "id"
  }'
```

## Language Support

The application supports a wide range of languages including:
- `en` (English)
- `id` (Indonesian)
- `es` (Spanish)
- `fr` (French)
- `de` (German)
- `ja` (Japanese)
- And many more

**Language Detection:**
- **Local Whisper (`/api/v1/transcribe`)**: Omit `language` field or set to `null` for automatic detection
- **OpenAI API (`/api/v2/transcribe`)**: Omit `language` field for automatic detection

## Technical Details

### Audio Download Process

- Uses `yt-dlp` to extract audio in M4A format
- Implements 1200-second (20-minute) timeout protection
- Includes retry logic (10 retries) and socket timeout (60 seconds)
- Supports custom user-agent and cookie authentication
- URL cleaning removes unnecessary parameters

### Model Loading

- Local Whisper model is loaded at application startup
- Loading time is logged for performance monitoring
- Invalid model configurations fall back to 'base' model
- Model validation against supported model list

### File Management

- Temporary audio files stored in `temp_audio_files/` directory
- Unique UUID-based filenames prevent conflicts
- Automatic cleanup after transcription (success or failure)
- Multiple audio format support (M4A, MP3, WebM, Opus)

### Error Handling

- Comprehensive logging with timestamps
- JSON error responses for API consistency
- Proper HTTP status codes (400, 415, 500)
- Graceful handling of download timeouts and API failures

## Troubleshooting

### Common Issues

**Dependency Installation:**
- Ensure Python 3.12.3 is used
- Verify FFmpeg is installed and in system PATH
- Install all requirements in a virtual environment

**YouTube Download Failures:**
- Verify YouTube URL is correct and accessible
- Check if video requires authentication (use cookies.txt)
- Update yt-dlp: `pip install --upgrade yt-dlp`

**OpenAI API Issues:**
- Confirm `OPENAI_API_KEY` is valid and active
- Ensure sufficient API credits/quota
- Verify `OPENAI_WHISPER_MODEL` is correct

**Model Loading Issues:**
- Check available system memory for larger models
- Ensure disk space for model cache (~/.cache/whisper)
- Verify network connectivity for initial model download

**Docker Issues:**
- Check container logs: `docker logs <container_name>`
- Ensure FFmpeg is available in container
- Verify environment variables are properly passed

### Performance Considerations

- **Local Models**: Larger models (medium, large) provide better accuracy but require more CPU/GPU and RAM
- **OpenAI API**: Faster processing but incurs usage costs
- **Resource Usage**: Consider system limitations when choosing model size
- **Download Timeout**: 20-minute limit per video download

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and commit: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

## License

This project is open source.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review application logs for error details
- Ensure all dependencies and requirements are met
- Verify configuration in `.env` file