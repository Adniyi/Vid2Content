# import eventlet
# eventlet.monkey_patch()
from flask import Flask, render_template,request,jsonify,redirect,url_for
from flask_cors import CORS
from transcript2 import Transcript
import time
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
from flask_caching import Cache
from google import genai
import asyncio


load_dotenv()


app = Flask(__name__)



CORS(app)

app.config['SECRET_KEY'] = os.getenv("SECRETE_KEY")
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DIR'] = 'flask_cache'  # Directory to store cached files
app.config['CACHE_DEFAULT_TIMEOUT'] = 60 * 60  # Cache expires after 1 hour
socketio = SocketIO(app,cors_allowed_origins="*", async_mode="threading")

cache = Cache(app)

# transcript_cache = load_json()
API_KEY = os.getenv("GEMINI_APIKEY")
client = genai.Client(api_key=API_KEY)


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

    return prompt

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
        return jsonify({"message": "No url data provided"}), 400
    
    video_url = data.get("url")
    print(video_url)

    if not video_url:
        return jsonify({"message":"Missing Video URL..."}),400
    

    transcript_cache = cache.get(video_url)
    # return jsonify({"message":"success.."})
    if transcript_cache:
        print("[DEFAULT] Returning cached Transcript")
        # return jsonify(transcript_cache),200
        return redirect(url_for("generate_article",result=transcript_cache))
    
    processor = Transcript(video_url)

    try:
        print("[✅] Downloading video...")
        socketio.emit("progress",{"message":"✅ Downloading video..."})
        # audio_path = processor.download_youtube_video(video_url=video_url)
        audio_path = asyncio.run(processor.download_video_async(video_url=video_url))
        # print(filename)

        print("[🔄] Uploading audio file to Assembly...")
        socketio.emit("progress", {"message": "🔄 Uploading to AssemblyAI..."})
        time.sleep(5)
        # audio_url = processor.upload_audio_url(audio_path=audio_path)

        print("[✍️] Transcribing Audio...")
        socketio.emit("progress", {"message": "✍️ Transcribing..."})
        raw_text = asyncio.run(processor.transcribe_audio_async(audio_path))
        # raw_text = processor.transcribe_video_with_assemblyai(audio_path)

        print("[🎯] Extracting keywords from the transcript")
        socketio.emit("progress",{"message":"🎯 Extracting keywords..."})
        transcript_text = processor.extract_tfidf_keywords(raw_text)
        distiled_text = processor.extract_distilbert_keywords(raw_text)

        print("[🥣] Combining Keywords...")
        socketio.emit("progress",{"message":"🥣 Combining Keywords..."})
        combined_keywords = processor.get_combined_keywords(raw_text)

        result = {
            "message": "Success",
            'text': raw_text,
            'text_keyowrd': transcript_text,
            'distiled_text': distiled_text,
            'combined_keywords':combined_keywords
        }

        # cache_key = hash(video_url)
        # cache.set(cache_key, result)

        # return redirect(url_for('generate_article', key=cache_key))
        prompt = generate_seo_article(raw_text,transcript_text,distiled_text)

        def generate():
            try:
                response = client.models.generate_content_stream(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                for chunk in response:
                    if chunk.text is not None:
                        yield chunk.text
                    # print(chunk.text, end="")
            except Exception as e:
                yield f"Error occurred: {e}"
        socketio.emit("done",{"message":"DOne.."})
        return generate() ,{"Content-Type": "text/markdown"}

    except Exception as e:
        print(f"[❌] Error: {e}")
        socketio.emit("error", {"message":str(e)})
        return jsonify({"error":str(e)})




def titleopt():
    return "Page for SEO title optimizer", 200  


@app.route("/profile")
def profile():
    return render_template("profile.html"), 200



@app.route("/contact_us")
def contact_us():
    return render_template("contact.html"), 200

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


if __name__ == "__main__":
    # app.run(debug=True)
    with app.app_context():
        socketio.run(app,debug=True)