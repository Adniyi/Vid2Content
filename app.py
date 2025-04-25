import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template,request,jsonify, Response, stream_with_context
from flask_cors import CORS
from transcript2 import Transcript
import time
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
import json


CACHE_FILE = "transcript.json"

# def load_json()

load_dotenv()
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("SECRETE_KEY")

CORS(app)

socketio = SocketIO(app,cors_allowed_origins="*", async_mode="eventlet")



transcript_cache = {}


def generate_seo_article(transcript,keywords,context):
    prompt = f"""
    You're a professional content writer. Write a detailed, SEO-optimized blog article based on the following transcript.

    Transcript:
    \"\"\"{transcript}\"\"\"

    Focus on these keywords: {', '.join(keywords)} and context:{', '.join(context)}.

    The article should:
    - Have a strong headline
    - Include an engaging intro
    - Be well-structured with headings
    - Use natural-sounding SEO keywords
    - Have a conclusion and a call-to-action

    Return just the final article content.
    """


@app.route("/")
def index():
    return render_template("index.html"),200

@app.route("/video_transcript")
def video_transcript():
    return render_template("youtube-link-processor-v3.html"),200

@app.route("/transcript", methods=['POST'])
def transcript():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No url data provided"}), 204
    
    video_url = data.get("url")
    print(video_url)
    # return jsonify({"message":"success.."})
    if video_url in transcript_cache:
        cached = transcript_cache[video_url]
        return jsonify(cached),200
    
    processor = Transcript(video_url)

    try:
        print("[✅] Downloading video...")
        socketio.emit("progress",{"message":"✅ Downloading video..."})
        audio_path = processor.download_youtube_video(video_url=video_url)

        print("[🔄] Uploading audio file to Assembly...")
        socketio.emit("progress", {"message": "🔄 Uploading to AssemblyAI..."})
        time.sleep(5)
        # audio_url = processor.upload_audio_url(audio_path=audio_path)

        print("[✍️] Transcribing Audio...")
        socketio.emit("progress", {"message": "✍️ Transcribing..."})
        raw_text = processor.transcribe_video_with_assemblyai(audio_path)

        print("[🎯] Extracting keywords from the transcript")
        socketio.emit("progress",{"message":"🎯 Extracting keywords..."})
        transcript_text = processor.extract_tfidf_keywords(raw_text)
        distiled_text = processor.extract_distilbert_keywords(raw_text)

        print("[🥣] Combining Keywords...")
        socketio.emit("progress",{"message":"🥣 Combining Keywords..."})
        combined_keywords = processor.get_combined_keywords(raw_text)

        transcript_cache[video_url] = {
            'text': raw_text,
            'text_keyowrd': transcript_text,
            'distiled_text': distiled_text,
            'combined_keywords':combined_keywords
        }
        print(transcript_cache)

        socketio.emit("done",transcript_cache)
        # time.sleep(5)
        return jsonify({
            "message": "Success",
            'raw_text':raw_text,
            "tfidf_keywords": transcript_text,
            "distilbert_keywords": distiled_text,
            "combined_keywords": combined_keywords
        }), 200
    except Exception as e:
        print(f"[❌] Error: {e}")
        socketio.emit("error", {"message":str(e)})
        return jsonify({"error":str(e)})



def titleopt():
    return "Page for SEO title optimizer", 200  

if __name__ == "__main__":
    # app.run(debug=True)
    with app.app_context():
        socketio.run(app,debug=True)