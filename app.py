from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import datetime, timedelta

def calculate_level(sad, energy, sleep, interest):

    score = (sad + (10 - energy) + (10 - sleep) + (10 - interest)) / 4

    if score <= 2:
        return "none", "No Depression 😊"
    elif score <= 5:
        return "mild", "Mild 😐"
    elif score <= 7:
        return "moderate", "Moderate 😟"
    else:
        return "severe", "Severe 😔"

def calculate_completion(user_id, level):
    required_activities = {
        "mild": ["walk", "music", "contacts"],
        "moderate": ["sleep", "yoga", "gratitude"],
        "severe": ["outdoor", "breathing", "professional_help"]
    }

    activities = Activity.query.filter_by(user_id=user_id).all()

    grouped = {}

    for act in activities:
        if act.date not in grouped:
            grouped[act.date] = set()

        grouped[act.date].add(act.activity_type)

    completed_days = 0

    for date in grouped:
        done = grouped[date]
        needed = set(required_activities.get(level, []))

        if needed.issubset(done):
            completed_days += 1

    total_days = len(grouped)

    return int((completed_days / total_days) * 100) if total_days > 0 else 0
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'secret123'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# DATABASE MODEL

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)
    

# ACTIVITY TRACKING MODEL


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    activity_type = db.Column(db.String(50))  
    value = db.Column(db.String(200)) 
    date = db.Column(db.String(50))


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    level = db.Column(db.String(50))
    score = db.Column(db.Float)

class Sleep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    hours = db.Column(db.Float)
    date = db.Column(db.String(20))
from datetime import datetime, timedelta

def calculate_streak(user_id):

    required_activities = {
        "mild": ["walk", "music", "contacts"],
        "moderate": ["sleep", "yoga", "gratitude"],
        "severe": ["outdoor", "breathing", "professional_help"]
    }

    current_level = session.get('level', 'moderate')

    activities = Activity.query.filter_by(
        user_id=user_id
    ).all()

    from collections import defaultdict

    grouped = defaultdict(set)

    for act in activities:
        grouped[act.date].add(act.activity_type)

    completed_dates = []

    needed = set(required_activities.get(current_level, []))

    for date in grouped:

        if needed.issubset(grouped[date]):

            completed_dates.append(
                datetime.strptime(date, "%Y-%m-%d").date()
            )

    completed_dates.sort(reverse=True)

    if not completed_dates:
        return 0

    today = datetime.now().date()

    latest = completed_dates[0]

    # streak valid only if latest completed day is today or yesterday
    if latest != today and latest != today - timedelta(days=1):
        return 0

    streak = 1
    prev = latest

    for d in completed_dates[1:]:

        if prev - timedelta(days=1) == d:
            streak += 1
            prev = d
        else:
            break

    return streak
yoga_sets = {
    1: ["Mountain Pose", "Child's Pose", "Cat-Cow Stretch"],
    2: ["Downward Dog", "Cobra Pose", "Seated Forward Bend"],
    3: ["Warrior I", "Warrior II", "Triangle Pose"]
}
@app.route('/')
def home():
    return redirect('/login')


# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            message = "Username or Email already exists"

        else:
            hashed_password = generate_password_hash(password)

            new_user = User(
                username=username,
                email=email,
                password=hashed_password
            )

            db.session.add(new_user)
            db.session.commit()

            return redirect('/login')

    return render_template('register.html', message=message)
# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            message = "User not found"
        elif not check_password_hash(user.password, password):
            message = "Incorrect password"
        else:
            session['user_id'] = user.id
            return redirect('/dashboard')

    return render_template('login.html', message=message)

import random
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    # ---------------- LEVEL ----------------
    current_level = session.get('level', 'moderate')

    # ---------------- USE SHARED LOGIC ----------------
    streak = calculate_streak(user.id)
    completion_rate = calculate_completion(user.id, current_level)

    # ---------------- TODAY REMINDER ----------------
    from datetime import datetime

    today = str(datetime.now().date())

    required_activities = {
        "mild": ["walk", "music", "contacts"],
        "moderate": ["sleep", "yoga", "gratitude"],
        "severe": ["outdoor", "breathing", "professional_help"]
    }

    today_activities = Activity.query.filter_by(
        user_id=user.id,
        date=today
    ).all()

    done = set(a.activity_type for a in today_activities)
    needed = set(required_activities.get(current_level, []))

    reminder = not needed.issubset(done)

    # ---------------- QUOTES ----------------
    import random
    quotes = [
        "Small steps every day create lasting change.",
        "Progress matters more than perfection.",
        "Healing is not linear, and that's okay.",
        "You don’t have to do everything today—just something.",
        "Resting is part of progress."
    ]

    quote = random.choice(quotes)

    # ---------------- RENDER ----------------
    return render_template(
        'dashboard.html',
        username=user.username,
        streak=streak,
        completion_rate=completion_rate,
        reminder=reminder,
        quote=quote
    )

@app.route('/mood_check')
def mood_check():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    return render_template(
        'mood_check.html',
        username=user.username
    )
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


@app.route('/input_test', methods=['GET', 'POST'])
def input_test():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        sad = int(request.form['sad'])
        energy = int(request.form['energy'])
        sleep = int(request.form['sleep'])
        interest = int(request.form['interest'])

        # ✅ DEFINE score INSIDE POST
        level, display_level = calculate_level(sad, energy, sleep, interest)

        session['level'] = level
        return render_template(
            'result.html',
            level=display_level,
            username=user.username,
            source="slider"
        )

    # ✅ GET request → just show page
    return render_template('input_test.html', username=user.username)

@app.route('/scan_emotion')
def scan_emotion():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('scan_emotion.html')

@app.route('/process_emotion', methods=['POST'])
def process_emotion():

    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    image_data = request.form.get('image')

    import base64, numpy as np, cv2

    image_bytes = base64.b64decode(image_data.split(',')[1])
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # -------- SOFT COMPUTING FEATURES --------
    brightness = np.mean(gray)        # energy
    contrast = np.std(gray)           # interest

    h, w = gray.shape
    mouth = gray[int(h*0.6):h, int(w*0.3):int(w*0.7)]
    mouth_brightness = np.mean(mouth)

    # -------- MAP TO 0–10 SCALE --------

    # ENERGY
    energy = min(max((brightness - 50) / 20, 0), 10)

    # INTEREST
    interest = min(max((contrast - 10) / 5, 0), 10)

    # SAD (based on smile)
    smile_factor = mouth_brightness - brightness

    if smile_factor > 15:
        sad = 1
    elif smile_factor > 5:
        sad = 3
    elif smile_factor > -5:
        sad = 5
    elif smile_factor > -15:
        sad = 7
    else:
        sad = 9

    # SLEEP (approx same as interest)
    sleep = interest

    # -------- USE SAME FUNCTION --------
    level, display_level = calculate_level(sad, energy, sleep, interest)

    session['level'] = level

    return render_template(
        'result.html',
        level=display_level,
        username=user.username,
        source="camera"
    )

@app.route('/result/<level>')
def result(level):
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    return render_template('result.html', level=level, username=user.username)

@app.route('/assessments', methods=['GET', 'POST'])
def assessments():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        q1 = int(request.form['q1'])
        q2 = int(request.form['q2'])
        q3 = int(request.form['q3'])

        score = (q1 + q2 + q3) / 3

        if score <= 1.5:
            level = "No Depression 😊"
        elif score <= 3:
            level = "Mild 😐"
        elif score <= 4:
            level = "Moderate 😟"
        else:
            level = "Severe 😔"

        # 🔥 SAVE TO DATABASE
        new_entry = Assessment(
            user_id=user.id,
            q1=q1,
            q2=q2,
            q3=q3,
            score=score,
            level=level
        )

        db.session.add(new_entry)
        db.session.commit()

        return redirect(f'/result/{level}')

    return render_template('assessments.html', username=user.username)

@app.route('/assessments/mild', methods=['GET', 'POST'])
def mild_assessment():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        q1 = int(request.form['q1'])
        q2 = int(request.form['q2'])

        score = (q1 + q2) / 2

        result = "Mild Managed 😊" if score < 2 else "Needs Attention 😐"

        return render_template('result.html', level=result)

    return render_template('assessment_mild.html',username=user.username)

@app.route('/assessments/moderate', methods=['GET', 'POST'])
def moderate_assessment():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        q1 = int(request.form['q1'])
        q2 = int(request.form['q2'])
        q3 = int(request.form['q3'])

        score = (q1 + q2 + q3) / 3

        result = "Moderate Stable 🙂" if score < 3 else "Moderate Risk 😟"

        return render_template('result.html', level=result)

    return render_template('assessment_moderate.html',username=user.username)

@app.route('/assessments/severe', methods=['GET', 'POST'])
def severe_assessment():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        q1 = int(request.form['q1'])
        q2 = int(request.form['q2'])
        q3 = int(request.form['q3'])
        q4 = int(request.form['q4'])

        score = (q1 + q2 + q3 + q4) / 4

        result = "Critical ⚠️ Seek Help" if score > 3 else "Improving 💛"

        return render_template('result.html', level=result)

    return render_template('assessment_severe.html',username=user.username)

@app.route('/guidance/<level>')
def guidance(level):
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    return render_template('guidance.html', username=user.username, level=level)

from datetime import datetime

@app.route('/activity/<activity_type>', methods=['GET', 'POST'])
def activity(activity_type):
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level')
    level = level.lower() if level else ""

    if level == "mild":
         required = ["walk", "music", "talk"]

    elif level == "moderate":
        required = ["walk", "music", "talk", "breathing"]

    elif level == "severe":
        required = ["talk", "professional"]

    else:
        required = []
    
    if activity_type == "music":

        songs_db = {
            "english": [
                {"name": "Weightless", "link": "https://youtu.be/DOT1LmQbFFA?si=tXdmTBAHX9oZS9mS"},
                {"name": "Clair de Lune", "link": "https://youtu.be/WNcsUNKlAKw?si=S3LYFZKkv2Qp__Ix"},
                {"name": "Perfect", "link": "https://youtu.be/cNGjD0VG4R8?si=cqxOHOTCUBeH3xIG"}
            ],
            "telugu": [
                {"name": "Samajavaragamana", "link": "https://youtu.be/OCg6BWlAXSw?si=9xzfyDD1Egvoiphu"},
                {"name": "Oohalu gusagusalade", "link": "https://youtu.be/kG1jb6zRn10?si=0ikdL5_YVoIK3qYe"},
                {"name": "Inthandam", "link": "https://youtu.be/dOKQeqGNJwY?si=H3NIGQY6hgCfhORO"}
            ],
            "hindi": [
                {"name": "Tum Hi Ho", "link": "https://www.youtube.com/watch?v=Umqb9KENgmk"},
                {"name": "Ikatara", "link": "https://youtu.be/akjdj6iHttY?si=Xl16ipiFB15HtMPb"},
                {"name": "Tere bina", "link": "https://youtu.be/9JDSGhhiOwI?si=6WrOPVNuVEqzv3Y9"}
            ],
            "tamil": [
                {"name": "Munbe Vaa", "link": "https://youtu.be/rp3_FhRnIRw?si=kkmWXeJ76XcRhgii"},
                {"name": "7 Aum Arivu", "link": "https://youtu.be/B122I8dNEtU?si=zSoOQwzTYKWLFztS"},
                {"name": "Anegan", "link": "https://youtu.be/MGjBQDrtGbA?si=c_AcVx7Bo-rVofrf"}
            ]
        }

        if request.method == 'POST':
            selected = request.form.get("value")
            
            new_activity= Activity(
                user_id=user.id,
                activity_type="music",
                value=selected,
                date=str(datetime.now().date())
            )
            
            db.session.add(new_activity)
            db.session.commit()
            
            print("LEVEL:", level)
            print("ACTIVITY:", activity_type)
            print("COMPLETED BEFORE:", session.get('completed'))
            
            completed = session.get('completed', [])

            if activity_type not in completed:
                completed.append(activity_type)

            session['completed'] = completed

            # 🔥 PRINT AFTER UPDATE
            print("COMPLETED AFTER:", completed)
            print("REQUIRED:", required)
            return render_template(
                "music.html",
                username=user.username,
                songs=songs_db.get(selected, []),
                level=level
            )

        return render_template(
            "music.html",
            username=user.username,
            songs=None,
            level=level
        )
    
    if request.method == 'POST':
        value = request.form.get('duration')

        new_activity = Activity(
            user_id=user.id,
            activity_type=activity_type,
            value=value,
            date=str(datetime.now().date())
        )

        db.session.add(new_activity)
        db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity=activity_type,
            value=value,
            level=level
        )
    return render_template(f"{activity_type}.html", username=user.username,level=level)

@app.route('/contacts', methods=['GET', 'POST'])
def contacts():

    if 'user_id' not in session:
        return redirect('/login')

    level = request.args.get('level', 'mild')

    if request.method == 'POST':

        name = request.form['name']
        phone = request.form['phone']

        # -------- SAVE CONTACT --------
        new_contact = Contact(
            user_id=session['user_id'],
            name=name,
            phone=phone
        )

        db.session.add(new_contact)

        # -------- 🔥 THIS IS WHAT YOU WERE MISSING --------
        # Mark activity as completed
        new_activity = Activity(
            user_id=session['user_id'],
            activity_type="contacts",
            value=name,
            date=str(datetime.now().date())
        )

        db.session.add(new_activity)

        db.session.commit()

        return redirect(f'/contacts?level={level}')

    contacts = Contact.query.filter_by(user_id=session['user_id']).all()

    return render_template('contacts.html', contacts=contacts, level=level)

@app.route('/delete_contact/<int:id>')
def delete_contact(id):
    if 'user_id' not in session:
        return redirect('/login')

    contact = Contact.query.get(id)

    # 🔒 SECURITY CHECK (IMPORTANT)
    if contact and contact.user_id == session['user_id']:
        db.session.delete(contact)
        db.session.commit()

    level = request.args.get('level')
    return redirect(f"/contacts?level={level}")

from datetime import datetime, timedelta

@app.route('/progress')
def progress():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    required_activities = {
        "mild": ["walk", "music", "contacts"],
        "moderate": ["sleep", "yoga", "gratitude"],
        "severe": ["outdoor", "breathing", "professional_help"]
    }
    
    current_level = session.get('level', 'moderate')

    # -------- FETCH --------
    activities = Activity.query.filter_by(
        user_id=user.id
    ).order_by(Activity.date.asc()).all()

    from collections import defaultdict

    grouped = defaultdict(lambda: defaultdict(list))

    for entry in activities:
        date = entry.date
        grouped[date][entry.activity_type].append(entry.value)

    for act in activities:
        if act.date not in grouped:
            grouped[act.date] = {}

        if act.activity_type not in grouped[act.date]:
            grouped[act.date][act.activity_type] = []

        grouped[act.date][act.activity_type].append(act.value)

    sorted_dates = sorted(grouped.keys())

    # -------- DAY NUMBERING --------
    numbered_grouped = []

    for i, date in enumerate(sorted_dates, start=1):
        numbered_grouped.append({
            "day_number": i,
            "date": date,
            "activities": grouped[date]
        })

    recent_grouped = numbered_grouped[-2:]
    recent_grouped.reverse()

    # -------- TODAY CHECK --------
    today = str(datetime.now().date())

    today_activities = Activity.query.filter_by(
        user_id=user.id,
        date=today
    ).all()

    completed_today = set(a.activity_type.lower() for a in today_activities)
    needed = set(required_activities.get(current_level, []))
    
    missing = list(needed - completed_today)
    remaining = len(missing)
    today_done = remaining == 0

    # -------- COMPLETION RATE --------
    completed_days = 0

    for date in grouped:
        done = set(k.lower() for k in grouped[date].keys())

        if needed.issubset(done):
            completed_days += 1

    total_days = len(grouped)

    completion_rate = int(
        (completed_days / total_days) * 100
    ) if total_days > 0 else 0

    # -------- STREAK (FIXED LOGIC) --------
    # -------- STREAK LOGIC --------

    streak = 0

    today_date = datetime.now().date()

    completed_dates = []

    for date in grouped:
        done = set(grouped[date].keys())
        needed = set(required_activities.get(current_level, []))

        if needed.issubset(done):
            completed_dates.append(
                datetime.strptime(date, "%Y-%m-%d").date()
            )

    completed_dates.sort(reverse=True)

    # MUST include today or yesterday
    if completed_dates:

        latest = completed_dates[0]

        if latest == today_date or latest == today_date - timedelta(days=1):

            streak = 1
            prev_date = latest

            for d in completed_dates[1:]:

                if prev_date - timedelta(days=1) == d:
                    streak += 1
                    prev_date = d
                else:
                    break

    return render_template(
        'progress.html',
        username=user.username,
        grouped=recent_grouped,
        streak=streak,
        completion_rate=completion_rate,
        today_done=today_done,
        remaining=remaining,
        missing=missing
    )
@app.route('/progress_done')
def progress_done():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    completed_today = session.get('completed', [])

    session.pop('completed', None)   # reset for next day/session

    return render_template(
        'progress_done.html',
        username=user.username,
        completed_today=completed_today
    )

@app.route('/activity/sleep', methods=['GET', 'POST'])
def sleep():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level')

    if request.method == 'POST':
        hours = request.form.get('hours')

        new_sleep = sleep(
            user_id=user.id,
            hours=float(hours),
            date=str(datetime.now().date())
        )

        db.session.add(new_sleep)
        db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity="sleep",
            value=hours,
            level=level
        )

    return render_template('sleep.html', username=user.username, level=level)

@app.route('/delete_account')
def delete_account():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Delete related data first
    Activity.query.filter_by(user_id=user_id).delete()
    Contact.query.filter_by(user_id=user_id).delete()

    # Delete user
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)

    db.session.commit()

    session.clear()

    return redirect('/register')

@app.route('/activity/gratitude', methods=['GET', 'POST'])
def gratitude():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level', 'moderate')

    if request.method == 'POST':
        p1 = request.form.get('point1')
        p2 = request.form.get('point2')
        p3 = request.form.get('point3')

        combined = f"1. {p1} | 2. {p2} | 3. {p3}"

        new_activity = Activity(
            user_id=user.id,
            activity_type='gratitude',
            value=combined,
            date=str(datetime.now().date())
        )

        db.session.add(new_activity)
        db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity='Positive Reflection',
            value='Saved',
            level=level
        )

    return render_template(
        'gratitude.html',
        username=user.username
    )

@app.route('/activity/yoga', methods=['GET', 'POST'])
def yoga():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level', 'moderate')

    streak = calculate_streak(user.id)

    yoga_day = (streak % 3) + 1
    todays_yoga = yoga_sets[yoga_day]

    if request.method == 'POST':
        today = str(datetime.now().date())

        existing = Activity.query.filter_by(
            user_id=user.id,
            activity_type='yoga',
            date=today
        ).first()

        if not existing:
            new_activity = Activity(
                user_id=user.id,
                activity_type='yoga',
                value=", ".join(todays_yoga),
                date=today
            )

            db.session.add(new_activity)
            db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity='yoga',
            value="Completed",
            level=level
        )

    return render_template(
        'yoga.html',
        username=user.username,
        yoga_list=todays_yoga
    )
@app.route('/activity/outdoor', methods=['GET', 'POST'])
def outdoor():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level', 'severe')

    if request.method == 'POST':
        duration = request.form.get('duration')

        new_activity = Activity(
            user_id=user.id,
            activity_type='outdoor',
            value=duration,
            date=str(datetime.now().date())
        )

        db.session.add(new_activity)
        db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity='Outdoor Time',
            value=duration,
            level=level
        )

    return render_template(
        'outdoor.html',
        username=user.username
    )
@app.route('/activity/breathing', methods=['GET', 'POST'])
def breathing():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level')
    if not level:
        level=session.get('level','severe')

    if request.method == 'POST':
        today = str(datetime.now().date())

        existing = Activity.query.filter_by(
            user_id=user.id,
            activity_type='breathing',
            date=today
        ).first()

        if not existing:
            new_activity = Activity(
                user_id=user.id,
                activity_type='breathing',
                value="Completed breathing exercise",
                date=today
            )
            db.session.add(new_activity)
            db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity='breathing',
            value="Completed",
            level=level
        )

    return render_template('breathing.html', username=user.username, level=level)
@app.route('/activity/professional_help', methods=['GET', 'POST'])
def professional_help():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    level = request.args.get('level', 'severe')

    if request.method == 'POST':
        new_activity = Activity(
            user_id=user.id,
            activity_type='professional_help',
            value='Reviewed Support Guidance',
            date=str(datetime.now().date())
        )

        db.session.add(new_activity)
        db.session.commit()

        return render_template(
            'activity_result.html',
            username=user.username,
            activity='Professional Help',
            value='Reviewed',
            level=level
        )

    return render_template(
        'professional_help.html',
        username=user.username
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)