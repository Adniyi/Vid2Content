# YouTube Video Transcript SEO Content Repurposer

## Project Description
This project is a Flask-based web application that processes YouTube video links to generate detailed, SEO-optimized blog articles based on the video's transcript. It downloads the audio from YouTube videos, transcribes the audio using AssemblyAI, extracts relevant keywords using advanced NLP techniques, and provides a user-friendly interface to interact with the service.

## Features
- Download audio from YouTube videos.
- Transcribe audio to text using AssemblyAI.
- Extract keywords using TF-IDF and DistilBERT models.
- Combine keywords intelligently for SEO optimization.
- Real-time progress updates via WebSocket (Socket.IO).
- Simple web interface to input YouTube links and view results.
- Caching of processed transcripts to improve performance.

## Installation and Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)
- AssemblyAI API key (sign up at [AssemblyAI](https://www.assemblyai.com/) to get an API key)

### Environment Variables
Create a `.env` file in the project root directory and add your AssemblyAI API key:
```
ASSEMBLY_AI_API_KEY=your_assemblyai_api_key_here
```

### Installing Dependencies
Install the required Python packages using pip:
```bash
pip install -r requirements.txt
```
(Note: If `requirements.txt` is not present, install the following packages manually:)
```bash
pip install flask flask-cors flask-socketio eventlet assemblyai spacy sklearn transformers torch numpy python-dotenv pytube yt-dlp
python -m spacy download en_core_web_sm
```

## Usage

### Running the Flask App
Start the Flask application with Socket.IO support:
```bash
python app.py
```
The app will run on `http://localhost:5000` by default.

### Accessing the Web Interface
Open your web browser and navigate to:
```
http://localhost:5000/
```
This will bring you to the landing page with links to the YouTube link processor.

### Using the YouTube Link Processor
- Click on the "Process Link3" or navigate to `/video_transcript`.
- Paste a YouTube video URL into the input field.
- Click the "Process" button.
- The app will download, transcribe, and extract keywords from the video.
- Results will be displayed on the page with options to copy the content.

## File Structure Overview
```
.
├── app.py                      # Main Flask application with routes and Socket.IO
├── transcript2.py              # Transcript class handling video download, transcription, and keyword extraction
├── static/
│   ├── js/
│   │   └── script4.js          # Frontend JavaScript for UI interaction and API calls
│   ├── styles/
│   │   └── style3.css          # CSS styles for the web interface
│   └── uploads/                # Directory for storing downloaded audio files
├── templates/
│   ├── index.html              # Landing page with navigation links
│   └── youtube-link-processor-v3.html  # Main UI for YouTube link processing
├── .gitignore                  # Git ignore file
└── README.md                  # This README file
```

## Technologies and Dependencies
- Python 3
- Flask (web framework)
- Flask-CORS (Cross-Origin Resource Sharing)
- Flask-SocketIO and eventlet (real-time communication)
- AssemblyAI API (speech-to-text transcription)
- spaCy (NLP)
- scikit-learn (TF-IDF keyword extraction)
- Hugging Face Transformers (DistilBERT for keyword extraction)
- PyTorch (model backend)
- pytube and yt-dlp (YouTube video downloading)
- dotenv (environment variable management)
- JavaScript, HTML, CSS (frontend)

## License
This project is open source and available under the MIT License.
