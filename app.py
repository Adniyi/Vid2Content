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
import requests
from extensions import db
from models import User, UserUsage,Article,Transcription,Subscription,Video,Plan
from datetime import datetime, timedelta
from flask_login import LoginManager,login_user, logout_user, current_user, login_required
from flask import flash, session
from werkzeug.security import generate_password_hash, check_password_hash



load_dotenv()


app = Flask(__name__)

CORS(app)

# Variable to store user limits
limit:int = 0

app.config['SECRET_KEY'] = os.getenv("SECRETE_KEY")
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DIR'] = 'flask_cache'  # Directory to store cached files
app.config['CACHE_DEFAULT_TIMEOUT'] = 60 * 60  # Cache expires after 1 hour
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///models.db'
socketio = SocketIO(app,cors_allowed_origins="*", async_mode="threading")
db.init_app(app)
cache = Cache(app)
login_manager = LoginManager()
# transcript_cache = load_json()
API_KEY = os.getenv("GEMINI_APIKEY")
client = genai.Client(api_key=API_KEY)

login_manager.login_view = 'login'
login_manager.init_app(app=app)

@login_manager.user_loader
def load_user(user_id:str):
    return User.query.get(int(user_id))


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
    
    user_id = data.get('user_id')
    plan_id = data.get('plan_id')
    video_url = data.get("url")

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if plan.name.lower() == 'free':
        limit += 1
    if plan.name.lower() == 'pro':
        limit += 1
    
    if plan.name.lower() == 'free' and limit == 3:
        return jsonify({"Error":"Video Limit reached"}), 400
    

    # Note: Change the Pro plan video_limit to None for Unlimited (using flask shell)
    elif plan.name.lower() == 'pro' and limit == 30:
        return jsonify({"Error":"Video Limit reached"}),400
    

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




@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("profile"))
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not name or not email or not password or not confirm_password:
            flash("Please fill out all fields.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", "error")
            return render_template("register.html")

        hashed_password = generate_password_hash(password, method="sha256")
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("profile"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        login_user(user)
        flash("Logged in successfully.", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("profile"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/profile")
def profile():
    return render_template("profile.html",user=current_user), 200



@app.route("/contact_us")
def contact_us():
    return render_template("contact.html"), 200

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/sucsess_message")
def success_message():
    return "Thank you for your Payment", 200


@app.route("/cancle")
def cancle():
    return "Subscription Cancled", 200



@app.route("/start_subscription",methods=["POST"])
def start_subscription():
    data = request.get_json()
    user_id = data.get('user_id')
    plan_id = data.get('plan_id')

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if not user or not plan:
        return jsonify({"Error":"User or Plan not Found"}), 404
    
    headers = {
        "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        'email': user.email,
        'amount':plan.price_monthly,
        'callback_url':url_for("verify_payment",_external=True),
        'metadata':{
            'user_id':user.id,
            'plan_id':plan.id
        }
    }

    response = requests.post('https://api.paystack.co/transaction/initialize',json=payload, headers=headers)
    if response.status_code != 200:
        return jsonify({"error": "Payment init failed"}), 500

    auth_url = response.json()["data"]["authorization_url"]
    print(response.json()['data']['access_code'])
    return jsonify({"authorization_url": auth_url})


@app.route("/verify_payment")
def verify_payment():
    reference = request.args.get("reference")
    headers = {"Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}"}

    response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Verification failed"}), 500
    
    
    data = response.json()["data"]
    status = data["status"]

    if status != 'success':
        return jsonify({"Error":"Payment unsuccessfull"}),400
    
    metadata = data["metadata"]
    user_id = metadata["user_id"]
    plan_id = metadata["plan_id"]

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if not user or not plan:
        return jsonify({"error": "User or plan not found"}), 404
    
    Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})


    now = datetime.now(datetime.astimezone)
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=30),
        renews_at=now + timedelta(days=30),
        status="active"
    )

    db.session.add(subscription)
    db.session.commit()

    return redirect(url_for("profile"))



@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    event = request.json.get("event")
    if event == "charge.success":
        data = request.json["data"]
        metadata = data["metadata"]
        user_id = metadata["user_id"]
        plan_id = metadata["plan_id"]

        # Ensure idempotency: Check if subscription already exists

        user = User.query.get(user_id)
        plan = Plan.query.get(plan_id)

        if user and plan:
            Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})

            now = datetime.now(datetime.timezone.utc)
            new_sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                starts_at=now,
                ends_at=now + timedelta(days=30),
                renews_at=now + timedelta(days=30),
                status="active"
            )
            db.session.add(new_sub)
            db.session.commit()

    return "", 200


@app.route("/subscribe_free_plan", methods=["POST"])
def subscribe_free_plan():
    data = request.get_json()
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if not user or not plan:
        return jsonify({"error": "User or Plan not found"}), 404

    if plan.name.lower() != "free":
        return jsonify({"error": "Invalid plan type"}), 400

    # Cancel any active subscription
    Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})

    now = datetime.now(datetime.timezone.utc)()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=30),
        renews_at=None,
        status="active"
    )

    db.session.add(sub)
    db.session.commit()

    return jsonify({"success": True})




if __name__ == "__main__":
    # app.run(debug=True)
    with app.app_context():
        db.create_all()
        socketio.run(app,debug=True)