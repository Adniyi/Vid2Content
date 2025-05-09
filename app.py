from flask import Flask, render_template,request,jsonify,redirect,url_for,Response,abort
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
# from youtube_details import YoutubeVideoDetails
from flask_migrate import Migrate
import markdown
import hmac
import hashlib



load_dotenv()


app = Flask(__name__)

CORS(app,supports_credentials=True)



app.config['SECRET_KEY'] = os.getenv("SECRETE_KEY")
app.config['CACHE_TYPE'] = 'FileSystemCache'
app.config['CACHE_DIR'] = 'flask_cache'  # Directory to store cached files
app.config['CACHE_DEFAULT_TIMEOUT'] = 60 * 60  # Cache expires after 1 hour
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///models.db'
app.config.update(SESSION_COOKIE_SAMESITE='None',SESSION_COOKIE_SECURE=True)
socketio = SocketIO(app,cors_allowed_origins="*", async_mode="threading")
db.init_app(app)
cache = Cache(app)

migrate = Migrate(app,db)
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

def get_user_plan(user):
    # Get the most recent active subscription
    active_sub = Subscription.query.filter_by(user_id=user.id, status="active").order_by(Subscription.starts_at.desc()).first()
    if active_sub and active_sub.plan:
        return active_sub.plan.name.lower()
    return "free"


def check_and_track_free_usage(user):
    now = datetime.now()
    current_month = now.replace(day=now.day, hour=0, minute=0, second=0, microsecond=0)

    usage = UserUsage.query.filter_by(user_id=user.id, month=current_month).first()
    if not usage:
        usage = UserUsage(user_id=user.id, month=current_month, video_processed=0)
        db.session.add(usage)

    if usage.video_processed >= 3:  # Assuming 2 free videos per day
        return False  # Limit reached
    usage.video_processed += 1
    db.session.commit()
    return True




@app.route("/")
def index():
    return render_template("index.html"),200



@app.route("/video_transcript")
@login_required
def video_transcript():
    active_sub = next((sub for sub in current_user.subscriptions if sub.status == "active"), None)
    user_plan = active_sub.plan.name if active_sub else "free"
    return render_template("youtube-link-processor-v3.html",user_plan=user_plan,user=current_user),200

@app.route("/transcript", methods=['POST'])
@login_required
def transcript():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No url data provided"}), 400
    
    user_id = data.get('user_id')
    video_url = data.get("url")

    user = User.query.get(user_id)
    plan = get_user_plan(current_user)

    if plan == "free":
        if not check_and_track_free_usage(current_user):
            return jsonify({"message": "Free plan limit reached. Upgrade to Pro for unlimited transcriptions."}), 403

    if not video_url:
        return jsonify({"message":"Missing Video URL..."}),400
    
    # Step 1: Check if video already exists
    video = Video.query.filter_by(youtube_url=video_url, user_id=current_user.id).first()

    if video:
        
        # Step 3: Check if transcription exists
        transcription = Transcription.query.filter_by(video_id=video.id).first()
        if transcription:
            print("[🗝] Transcription exists — generate article from it")

            prompt = generate_seo_article(transcription.raw_text,transcription.processed_keywords.split(", "),[])  # or some saved distilbert context
        
            transcription = Transcription.query.filter_by(video_id=video.id).first()
            article_text = ""

            def generate():
                nonlocal article_text
                try:
                    response = client.models.generate_content_stream(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    for chunk in response:
                        if chunk.text:
                            article_text += chunk.text
                            yield chunk.text

                except Exception as e:
                    db.session.rollback()
                    yield f"Error: {str(e)}"
            stream = Response(generate(), content_type="text/markdown")
            stream.headers["X-Transcription-ID"] = str(transcription.id)
            return stream

    processor = Transcript(video_url)

    try:
        print("[✅] Downloading video...")
        socketio.emit("progress",{"message":"✅ Downloading video..."})
        # audio_path = processor.download_youtube_video(video_url=video_url)
        audio_path = asyncio.run(processor.download_video_async(video_url=video_url))
        title,thumbnail_url,duration = processor.get_video_details(video_url=video_url)
        print(title)
        print(thumbnail_url)
        print(duration)

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
        # cache.set(video_url, result)

        # return redirect(url_for('generate_article', key=cache_key))
        prompt = generate_seo_article(raw_text,transcript_text,distiled_text)

        
        
        new_video = Video(user_id=current_user.id,youtube_url=video_url,video_title=title,duration_seconds=duration,thumbnail_url=thumbnail_url)
        db.session.add(new_video)
        db.session.commit()
        

        video = Video.query.filter_by(youtube_url=video_url).first()
        video_id = video.id

        new_transcription = Transcription(video_id=video_id,raw_text=raw_text, processed_keywords=", ".join(combined_keywords))
        db.session.add(new_transcription)
        db.session.commit()


        # Initialize article_text here
        transcription = Transcription.query.filter_by(video_id=video.id).first()
        article_text = ""     
        def generate():
            nonlocal article_text 
            try:
                response = client.models.generate_content_stream(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                for chunk in response:
                    if chunk.text is not None:
                        article_text += chunk.text
                        yield chunk.text

            except Exception as e:
                db.session.rollback()
                yield f"Error occurred: {e}"
        socketio.emit("done",{"message":"DOne.."})

        stream = Response(generate(), content_type="text/markdown")
        stream.headers["X-Transcription-ID"] = str(transcription.id)
        return stream

    except Exception as e:
        print(f"[❌] Error: {e}")
        socketio.emit("error", {"message":str(e)})
        return jsonify({"error":str(e)})



@app.route("/save_article", methods=["POST"])
@login_required
def save_article():
    data = request.get_json()
    transcription_id = data.get("transcription_id")
    content = data.get("content")

    if not transcription_id or not content:
        return jsonify({"error": "Missing transcription_id or content"}), 400

    # Check if article already exists
    existing_article = Article.query.filter_by(transcription_id=transcription_id).first()
    if existing_article:
        return jsonify({"success": "Article already exists"}), 200

    new_article = Article(
        transcription_id=transcription_id,
        user_id=current_user.id,
        content=content
    )
    db.session.add(new_article)
    db.session.commit()

    return jsonify({"success": "Article saved successfully"}), 201





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
            flash("Please fill out all fields.", category='error')
            print("Please fill out all fields.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", category='error')
            print("Passwords do not match.")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", category='error')
            print("Email already registered.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        # free_plan = Plan.query.filter_by(name='Free').first()
        # if not free_plan:
        #     flash('Free plan not found. Contact admin.', 'danger')
        #     print("Free plan not found. Contact admin.")
        #     return redirect(url_for('register'))

        # subscription = Subscription(user_id=new_user.id, plan_id=free_plan.id)
        # db.session.add(subscription)
        # db.session.commit()
        flash("Registration successful. Please log in.", category='success')
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
            flash("Invalid email or password.", category='error')
            return render_template("login.html")

        login_user(user,remember=True)
        flash("Logged in successfully.", category='success')
        next_page = request.args.get("next")
        return redirect(next_page or url_for("profile"))
    
    return render_template("login.html",users=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", category='success')
    return redirect(url_for("login"))

@app.route("/profile")
@login_required
def profile():
    videos = Video.query.filter_by(user_id=current_user.id).all()
    active_sub = next((sub for sub in current_user.subscriptions if sub.status == "active"), None)
    user_plan = active_sub.plan.name if active_sub else "free"
    # print(user_plan)
    return render_template("profile.html",user=current_user, user_plan=user_plan,active_sub=active_sub, videos=videos), 200



@app.route("/contact_us")
@login_required
def contact_us():
    return render_template("contact.html"), 200

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/sucsess_message")
def success_message():
    return "Thank you for your Payment", 200




# @app.route("/cancel_subscription",methods=['POST'])
# @login_required
# def cancel_subscription():
#     active_sub = Subscription.query.filter_by(user_id=current_user.id, status="active").first()
#     # active_sub = next((sub for sub in current_user.subscriptions if sub.status == "active"), None)
#     print(active_sub.subscription_code)
#     if not active_sub or not active_sub.subscription_code or not active_sub.email_token:
#         return jsonify({"error": "No active subscription found or missing Paystack details"}), 404
    
#     headers = {
#         "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "code": active_sub.subscription_code,
#         "token": active_sub.email_token
#     }
#     response = requests.post("https://api.paystack.co/subscription/disable", headers=headers, json=payload)

#     if response.status_code == 200:
#         active_sub.status = "cancelled"
#         db.session.commit()
#         return jsonify({"success": "Subscription cancelled via Paystack"}), 200
#     else:
#         return jsonify({"error": "Failed to cancel subscription on Paystack"}), 500





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
        'plan':os.getenv('PAYSTACK_PLAN_CODE'),
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
    # print(response.json()['data']['access_code'])
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
    
    # print(data)
    
    metadata = data["metadata"]
    user_id = metadata["user_id"]
    plan_id = metadata["plan_id"]
    # subscription_code = data["subscription_code"]
    # email_token = data["subscription"]["email_token"]
    # print(user_id)
    # print(plan_id)

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if not user or not plan:
        return jsonify({"error": "User or plan not found"}), 404
    
    Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})


    now = datetime.now()
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=30),
        renews_at=now + timedelta(days=30),
        status="active",
        subscription_code=None,
        email_token=None
    )

    db.session.add(subscription)
    db.session.commit()

    return redirect(url_for("profile"))



@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    payload = request.get_data()

    computed_hash = hmac.new(
        key=os.getenv('PAYSTACK_SECRET_KEY').encode(),
        msg=payload,
        digestmod=hashlib.sha512
    ).hexdigest()

    paystack_signature = request.headers.get('x-paystack-signature')
    if not hmac.compare_digest(computed_hash, paystack_signature):
        abort(400)

    event = request.json.get("event")
    data = request.json["data"]
    if event == "subscription.create":
        handle_subscription_create(data)
        
    elif event == "subscription.not_renew":
        handle_subscription_not_renew(data)

    elif event == "subscription.disable":
        handle_subscription_disabled(data)
    return "", 200


def handle_subscription_create(data):
    metadata = data["metadata"]
    user_id = metadata["user_id"]
    plan_id = metadata["plan_id"]

    # Ensure idempotency: Check if subscription already exists

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)
    subscription_code = data['subscription_code']
    email_token = data['email_token']
    # customer_email = data['customer']['email']


    if user and plan:
        Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})

        now = datetime.now()
        new_sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            starts_at=now,
            ends_at=now + timedelta(days=30),
            renews_at=now + timedelta(days=30),
            status="active",
            subscription_code=subscription_code,
            email_token=email_token
        )
        db.session.add(new_sub)
        db.session.commit()
        return jsonify({"success":"Thank you for subscribing to our pro plan"}), 200

def handle_subscription_not_renew(data):
    email= data['customer']['email']
    user = User.query.filter_by(email=email).first()
    active_sub = Subscription.query.filter_by(user_id=current_user.id, status="active").first()
    # subscription = Subscription.query.filter_by(subscription_code=subscription_code,email_token=email_token).first()
    if active_sub:
        active_sub.status = "non-renewing"
        active_sub.subscription_code = data['subscription_code']
        active_sub.email_token = data['email_token']
        db.session.commit()
        return jsonify({"success": "Subscription cancelled via Paystack"}), 200
    
    else:
        return jsonify({"error": "Failed to cancel subscription on Paystack"})

def handle_subscription_disabled(data):
    subscription_code = data['subscription_code']
    email_token = data['email_token']  

    subscription = Subscription.query.filter_by(user_id=current_user.id, status="non-renewing",subscription_code=subscription_code,email_token=email_token).first()
    if not subscription:
        return jsonify({"error":"Subscription not found"}), 404
    subscription.status = "cancelled"
    subscription.plan.name = 'free'
    db.session.commit()
    return jsonify({"error":"Your Subcription has been cancled and you will be moves to the free plan"}), 403

@app.route("/subscribe_free_plan", methods=["POST"])
def subscribe_free_plan():
    data = request.get_json()
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")

    user = User.query.get(user_id)
    plan = Plan.query.get(plan_id)

    if not user or not plan:
        return jsonify({"error": "User or Plan not found"}), 404
    
    if user.subscriptions:
        return jsonify({"error":"You are already on the a plan"}),400

    if plan.name.lower() != "free":
        return jsonify({"error": "Invalid plan type"}), 400

    # Cancel any active subscription
    Subscription.query.filter_by(user_id=user.id, status="active").update({"status": "expired"})

    now = datetime.now()
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

    # print(user.subscriptions)
    return jsonify({"success": True})



@app.route("/edit/<int:id>")
@login_required
def edit(id):
    video = Video.query.get_or_404(id)

    # Ensure the video belongs to the current user
    if video.user_id != current_user.id:
        return "Unauthorized", 403

    transcription = Transcription.query.filter_by(video_id=video.id).first()
    # print(transcription.id)
    if not transcription:
        return "Transcription not found", 404

    article = Article.query.filter_by(transcription_id=transcription.id).first()
    # print(article)

    if not article:
        return "Article not found", 404

    return render_template("edit.html", article=article, user=current_user, video=video), 200



if __name__ == "__main__":
    # app.run(debug=True)
    with app.app_context():
        db.create_all()
        socketio.run(app,debug=True)