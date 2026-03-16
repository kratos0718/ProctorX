# -*- coding: utf-8 -*-
import os, cv2, base64, time
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, jsonify, send_file)
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np

from config import Config
from models import db, User, ExamSession, Violation, Question, ExamAnswer
from proctoring.face_detection import FaceDetector
from proctoring.eye_tracker import EyeTracker
from proctoring.head_pose import HeadPoseEstimator
from proctoring.lip_movement import LipMovementDetector
from proctoring.object_detection import ObjectDetector
from proctoring.audio_monitor import AudioMonitor
from proctoring.risk_scorer import RiskScorer
from proctoring.report_generator import ReportGenerator

# â”€â”€ App Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = Flask(__name__)
app.config.from_object(Config)
os.makedirs('static/screenshots', exist_ok=True)
os.makedirs('database', exist_ok=True)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
login_manager = LoginManager(app)
login_manager.login_view = 'login'

proctoring_sessions = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# â”€â”€ Auth Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))

            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
        if User.query.filter_by(username=username).first():
            return render_template('login.html', reg_error='Username already exists', show_reg=True)
        user = User(
            username=username, email=email,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('login.html', show_reg=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# â”€â”€ Student Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/student')
@app.route('/dashboard')
@login_required
def dashboard():
    exams = db.session.query(Question.exam_name).distinct().all()
    exams = [e[0] for e in exams]
    sessions = ExamSession.query.filter_by(user_id=current_user.id)\
                                .order_by(ExamSession.start_time.desc()).all()
    
    meta = {
        'Data Structures & Algorithms': {'icon':'🌲','sub':'sub-dsa','diff':'Hard','instructor':'Prof. Sharma','desc':'Arrays, trees, graphs, sorting algorithms','dur':45,'qcount':10},
        'Database Management Systems':  {'icon':'🗄️','sub':'sub-dbms','diff':'Medium','instructor':'Prof. Mehta','desc':'SQL, normalization, transaction mgmt','dur':40,'qcount':10},
        'Operating Systems':            {'icon':'⚙️','sub':'sub-os','diff':'Hard','instructor':'Prof. Turing','desc':'Processes, deadlocks, memory mgmt','dur':50,'qcount':10},
        'Java Programming':             {'icon':'☕','sub':'sub-java','diff':'Medium','instructor':'Prof. Gupta','desc':'OOP concepts, collections, threads','dur':45,'qcount':10},
        'Design & Analysis of Algorithms':{'icon':'🔍','sub':'sub-daa','diff':'Hard','instructor':'Prof. Cormen','desc':'Dynamic programming, greedy, P/NP','dur':60,'qcount':10},
        'Python Programming':           {'icon':'🐍','sub':'sub-python','diff':'Easy','instructor':'Prof. Rossum','desc':'Basics, data structures, decorators','dur':30,'qcount':10},
        'Machine Learning':             {'icon':'🤖','sub':'sub-ml','diff':'Hard','instructor':'Prof. Ng','desc':'Regression, classifications, NNs','dur':60,'qcount':10},
        'Artificial Intelligence':      {'icon':'🧠','sub':'sub-ml','diff':'Medium','instructor':'Prof. Russell','desc':'Search, logic, logic programming','dur':45,'qcount':10},
        'Computer Networks':            {'icon':'🌐','sub':'sub-python','diff':'Medium','instructor':'Prof. Kurose','desc':'OSI model, TCP/IP, routing','dur':40,'qcount':10},
        'Software Engineering':         {'icon':'📐','sub':'sub-java','diff':'Easy','instructor':'Prof. Pressman','desc':'SDLC, Agile, testing, design patterns','dur':30,'qcount':10},
        'Default':                      {'icon':'🎓','sub':'sub-default','diff':'Medium','instructor':'Staff','desc':'General assessment','dur':45,'qcount':10}
    }
    
    return render_template('proctorx_dashboard.html', exams=exams, meta=meta, sessions=sessions)

@app.route('/exams')
@login_required
def exams_page():
    available_exams = db.session.query(Question.exam_name).distinct().all()
    available_exams = [e[0] for e in available_exams]
    meta = {
        'Data Structures & Algorithms': {'icon':'🌲','sub':'sub-dsa','diff':'Hard','instructor':'Prof. Sharma','desc':'Arrays, trees, graphs, sorting algorithms','dur':45,'qcount':10},
        'Database Management Systems':  {'icon':'🗄️','sub':'sub-dbms','diff':'Medium','instructor':'Prof. Mehta','desc':'SQL, normalization, transaction mgmt','dur':40,'qcount':10},
        'Operating Systems':            {'icon':'⚙️','sub':'sub-os','diff':'Hard','instructor':'Prof. Turing','desc':'Processes, deadlocks, memory mgmt','dur':50,'qcount':10},
        'Java Programming':             {'icon':'☕','sub':'sub-java','diff':'Medium','instructor':'Prof. Gupta','desc':'OOP concepts, collections, threads','dur':45,'qcount':10},
        'Design & Analysis of Algorithms':{'icon':'🔍','sub':'sub-daa','diff':'Hard','instructor':'Prof. Cormen','desc':'Dynamic programming, greedy, P/NP','dur':60,'qcount':10},
        'Python Programming':           {'icon':'🐍','sub':'sub-python','diff':'Easy','instructor':'Prof. Rossum','desc':'Basics, data structures, decorators','dur':30,'qcount':10},
        'Machine Learning':             {'icon':'🤖','sub':'sub-ml','diff':'Hard','instructor':'Prof. Ng','desc':'Regression, classifications, NNs','dur':60,'qcount':10},
        'Artificial Intelligence':      {'icon':'🧠','sub':'sub-ml','diff':'Medium','instructor':'Prof. Russell','desc':'Search, logic, logic programming','dur':45,'qcount':10},
        'Computer Networks':            {'icon':'🌐','sub':'sub-python','diff':'Medium','instructor':'Prof. Kurose','desc':'OSI model, TCP/IP, routing','dur':40,'qcount':10},
        'Software Engineering':         {'icon':'📐','sub':'sub-java','diff':'Easy','instructor':'Prof. Pressman','desc':'SDLC, Agile, testing, design patterns','dur':30,'qcount':10},
        'Default':                      {'icon':'🎓','sub':'sub-default','diff':'Medium','instructor':'Staff','desc':'General assessment','dur':45,'qcount':10}
    }
    return render_template('exams.html', available_exams=available_exams, meta=meta)

@app.route('/history')
@login_required
def history_page():
    sessions = ExamSession.query.filter_by(user_id=current_user.id)\
                                .order_by(ExamSession.start_time.desc()).all()
    return render_template('history.html', sessions=sessions)

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')

@app.route('/profile/data')
@login_required
def profile_data():
    sessions = ExamSession.query.filter_by(user_id=current_user.id)\
                                .order_by(ExamSession.start_time.asc()).all()
    completed = [s for s in sessions if s.status == 'completed']
    scored    = [s for s in completed if s.total_questions]
    avg_score_pct = round(
        sum(s.score / s.total_questions * 100 for s in scored) / len(scored), 1
    ) if scored else 0.0
    avg_risk = round(
        sum(s.final_risk_score or 0 for s in completed) / len(completed), 1
    ) if completed else 0.0
    total_viols = db.session.query(db.func.count(Violation.id)).join(
        ExamSession, Violation.session_id == ExamSession.id
    ).filter(ExamSession.user_id == current_user.id).scalar() or 0
    integrity = max(0, min(100, round(100 - avg_risk)))
    # Per-exam score history for chart
    history = [
        {'exam': s.exam_name[:22],
         'score_pct': round(s.score / s.total_questions * 100, 1) if s.total_questions else 0,
         'risk': round(s.final_risk_score or 0, 1),
         'date': s.start_time.strftime('%b %d')}
        for s in completed[-10:]
    ]
    return jsonify({
        'username': current_user.username,
        'email': current_user.email,
        'joined': current_user.created_at.strftime('%b %Y'),
        'total_exams': len(sessions),
        'completed_exams': len(completed),
        'avg_score_pct': avg_score_pct,
        'avg_risk': avg_risk,
        'integrity': integrity,
        'total_violations': total_viols,
        'history': history,
    })

@app.route('/exam/start/<exam_name>')
@login_required
def start_exam(exam_name):
    exam_session = ExamSession(user_id=current_user.id, exam_name=exam_name)
    db.session.add(exam_session)
    db.session.commit()
    proctoring_sessions[exam_session.id] = {
        'face': FaceDetector(),
        'eye': EyeTracker(),
        'head': HeadPoseEstimator(),
        'lip': LipMovementDetector(),
        'audio': AudioMonitor(),
        'risk': RiskScorer(),
        'object': ObjectDetector(),
        'last_screenshot': 0,
        'frame_count': 0,
    }
    proctoring_sessions[exam_session.id]['audio'].start()
    return redirect(url_for('exam_page', session_id=exam_session.id))

_EXAM_META = {
    'Data Structures & Algorithms':    {'dur': 45, 'diff': 'Hard'},
    'Database Management Systems':     {'dur': 40, 'diff': 'Medium'},
    'Operating Systems':               {'dur': 50, 'diff': 'Hard'},
    'Java Programming':                {'dur': 45, 'diff': 'Medium'},
    'Design & Analysis of Algorithms': {'dur': 60, 'diff': 'Hard'},
    'Python Programming':              {'dur': 30, 'diff': 'Easy'},
    'Machine Learning':                {'dur': 60, 'diff': 'Hard'},
    'Artificial Intelligence':         {'dur': 45, 'diff': 'Medium'},
    'Computer Networks':               {'dur': 40, 'diff': 'Medium'},
    'Software Engineering':            {'dur': 30, 'diff': 'Easy'},
}

@app.route('/exam/<int:session_id>')
@login_required
def exam_page(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    if exam_session.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    questions = Question.query.filter_by(exam_name=exam_session.exam_name).all()
    meta = _EXAM_META.get(exam_session.exam_name, {'dur': 45, 'diff': 'Medium'})
    return render_template('exam.html', session=exam_session,
                           questions=questions, duration=meta['dur'],
                           difficulty=meta['diff'])

@app.route('/exam/<int:session_id>/submit', methods=['POST'])
@login_required
def submit_exam(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    answers = request.json.get('answers', {})
    score = 0
    for qid_str, ans in answers.items():
        q = Question.query.get(int(qid_str))
        if q:
            is_correct = (ans == q.correct_answer)
            if is_correct:
                score += 1
            ea = ExamAnswer(session_id=session_id, question_id=q.id,
                            selected_answer=ans, is_correct=is_correct)
            db.session.add(ea)
    ps = proctoring_sessions.get(session_id, {})
    risk = ps.get('risk', RiskScorer())
    summary = risk.get_summary()
    exam_session.end_time = datetime.utcnow()
    exam_session.status = 'completed'
    exam_session.final_risk_score = summary['score']
    exam_session.total_violations = summary['total_violations']
    exam_session.score = score
    exam_session.total_questions = len(answers)
    exam_session.exam_type = 'mcq'
    db.session.commit()
    if 'audio' in ps:
        ps['audio'].stop()
    return jsonify({'success': True, 'score': score,
                    'redirect': url_for('exam_result', session_id=session_id)})

@app.route('/exam/<int:session_id>/result')
@login_required
def exam_result(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    violations = Violation.query.filter_by(session_id=session_id).all()
    answers = ExamAnswer.query.filter_by(session_id=session_id).all()
    correct = sum(1 for a in answers if a.is_correct)
    return render_template('result.html', session=exam_session,
                           violations=violations, score=correct, total=len(answers))

# â”€â”€ Proctoring API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/proctor/frame/<int:session_id>', methods=['POST'])
@login_required
def process_frame(session_id):
    ps = proctoring_sessions.get(session_id)
    if not ps:
        return jsonify({'error': 'Session not found'}), 404

    data = request.json
    img_data = data.get('frame', '')
    tab_switch = data.get('tab_switch', False)
    all_alerts = []
    face_count = 0

    try:
        header, encoded = img_data.split(',', 1)
        frame_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        frame = cv2.resize(frame, (640, 360))
    except Exception:
        return jsonify({'error': 'Frame decode failed'}), 400

    ps['frame_count'] += 1

    # Keep track of last alerts to prevent flickering
    if 'last_alerts' not in ps:
        ps['last_alerts'] = []
    
    # Run all detections every 2 frames for near real-time response (<1s)
    if True:
        face_count, landmarks, frame, face_alerts = ps['face'].detect(frame)
        all_alerts.extend(face_alerts)

        if landmarks is not None:
            eye_result = ps['eye'].analyze(frame, landmarks)
            all_alerts.extend(eye_result['alerts'])

            head_result = ps['head'].estimate(frame, landmarks)
            all_alerts.extend(head_result['alerts'])

            lip_result = ps['lip'].analyze(frame, landmarks)
            all_alerts.extend(lip_result['alerts'])
            
            ps['last_stats'] = {
                'face_count': face_count,
                'gaze': eye_result['gaze'],
                'head': head_result['pose'],
                'blinks': getattr(ps['eye'], 'total_blinks', 0),
                'talking': lip_result['talking']
            }
        else:
            ps['last_stats'] = {
                'face_count': face_count,
                'gaze': None,
                'head': None,
                'blinks': getattr(ps['eye'], 'total_blinks', 0),
                'talking': False
            }

        # Object detection every 2 frames — fast enough for sub-1 second response
        frame, _, obj_alerts = ps['object'].detect(frame)
        all_alerts.extend(obj_alerts)
        ps['last_obj_alerts'] = obj_alerts

        ps['last_alerts'] = all_alerts
    else:
        # On skipped frames, reuse previous alerts (only 1 frame old)
        all_alerts.extend(ps.get('last_alerts', []))

    audio_status = ps['audio'].get_status()
    all_alerts.extend(audio_status['alerts'])

    if tab_switch:
        all_alerts.append(('tab_switch', 'Tab switch detected!', 'high'))

    risk_score = ps['risk'].update(all_alerts)
    risk_summary = ps['risk'].get_summary()

    now = time.time()
    saved_violations = []
    for vtype, msg, severity in all_alerts:
        v = Violation(session_id=session_id, violation_type=vtype,
                      severity=severity, details=msg, timestamp=datetime.utcnow())
        if severity == 'high' and (now - ps['last_screenshot']) > 5:
            try:
                ss_path = f"static/screenshots/{session_id}_{int(now)}.jpg"
                cv2.imwrite(ss_path, frame)
                v.screenshot_path = ss_path
                ps['last_screenshot'] = now
            except Exception:
                pass
        db.session.add(v)
        saved_violations.append({'type': vtype, 'msg': msg, 'severity': severity})

    if all_alerts:
        db.session.commit()

    last = ps.get('last_stats', {})
    
    socketio.emit('proctor_update', {
        'session_id': session_id,
        'student': current_user.username,
        'risk_score': risk_score,
        'risk_level': risk_summary['level'],
        'alerts': saved_violations,
        'face_count': last.get('face_count', face_count),
        'gaze': last.get('gaze'),
        'head_dir': last.get('head'),
        'talking': last.get('talking'),
        'audio_level': audio_status['level'],
    }, room='admin')

    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    frame_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buffer).decode()

    return jsonify({
        'risk_score': risk_score,
        'risk_level': risk_summary['level'],
        'risk_color': risk_summary['color'],
        'alerts': saved_violations,
        'annotated_frame': frame_b64,
        'stats': {
            'face_count': last.get('face_count', face_count),
            'gaze': last.get('gaze', 'unknown'),
            'blinks': last.get('blinks', 0),
            'head': last.get('head', 'forward'),
            'talking': last.get('talking', False),
            'audio': audio_status['level'],
        }
    })


# ── Coding Exam ───────────────────────────────────────────────────────────────────────
@app.route('/code')
@login_required
def code_lab():
    """Single-route coding exam — creates session and renders page directly."""
    exam_session = ExamSession(user_id=current_user.id, exam_name='Coding Assessment')
    db.session.add(exam_session)
    db.session.commit()
    try:
        proctoring_sessions[exam_session.id] = {
            'face': FaceDetector(), 'eye': EyeTracker(),
            'head': HeadPoseEstimator(), 'lip': LipMovementDetector(),
            'audio': AudioMonitor(), 'risk': RiskScorer(),
            'object': ObjectDetector(), 'last_screenshot': 0, 'frame_count': 0,
        }
        proctoring_sessions[exam_session.id]['audio'].start()
    except Exception:
        proctoring_sessions[exam_session.id] = {
            'risk': RiskScorer(), 'last_screenshot': 0, 'frame_count': 0
        }
    return render_template('coding_exam.html', session=exam_session,
                           questions=CODING_QUESTIONS)

@app.route('/code/run', methods=['POST'])
@login_required
def code_run():
    import requests as _req
    data = request.get_json(silent=True) or {}
    try:
        resp = _req.post('https://emkc.org/api/v2/piston/execute',
                         json=data, timeout=15,
                         headers={'Content-Type': 'application/json'})
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({'run': {'output': f'Execution error: {e}', 'stderr': ''}}), 200

@app.route('/code/<int:session_id>/submit', methods=['POST'])
@login_required
def code_submit(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    data    = request.get_json(silent=True) or {}
    results = data.get('results', {})
    passed  = sum(1 for v in results.values() if v == 'pass')
    ps      = proctoring_sessions.get(session_id, {})
    risk    = ps.get('risk', RiskScorer())
    summary = risk.get_summary()
    exam_session.end_time         = datetime.utcnow()
    exam_session.status           = 'completed'
    exam_session.final_risk_score = summary['score']
    exam_session.total_violations = summary['total_violations']
    exam_session.score            = passed
    exam_session.total_questions  = len(CODING_QUESTIONS)
    exam_session.exam_type        = 'coding'
    db.session.commit()
    if 'audio' in ps:
        try: ps['audio'].stop()
        except: pass
    return jsonify({'success': True, 'score': passed, 'total': len(CODING_QUESTIONS),
                    'redirect': url_for('exam_result', session_id=session_id)})

CODING_QUESTIONS = [
    {
        'id': 1, 'title': 'Hello World', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>hello_world()</code> that returns the string <strong>"Hello, World!"</strong>.',
        'starter': 'def hello_world():\n    # Return the string "Hello, World!"\n    pass',
        'test_code': '\n_r=hello_world()\nassert _r=="Hello, World!",f"Expected \'Hello, World!\' got \'{_r}\'"\nprint("ALL_PASS")',
        'examples': [{'call': 'hello_world()', 'output': '"Hello, World!"'}],
    },
    {
        'id': 2, 'title': 'Sum of Two Numbers', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>add(a, b)</code> that returns the sum of two numbers.',
        'starter': 'def add(a, b):\n    # Return the sum of a and b\n    pass',
        'test_code': '\nassert add(1,2)==3\nassert add(-1,1)==0\nassert add(100,200)==300\nprint("ALL_PASS")',
        'examples': [{'call': 'add(3, 5)', 'output': '8'}],
    },
    {
        'id': 3, 'title': 'Reverse a String', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>reverse_string(s)</code> that returns the reversed version of the input string.',
        'starter': 'def reverse_string(s):\n    # Return the reversed string\n    pass',
        'test_code': '\nassert reverse_string("hello")=="olleh"\nassert reverse_string("Python")=="nohtyP"\nassert reverse_string("")==""\nprint("ALL_PASS")',
        'examples': [{'call': 'reverse_string("hello")', 'output': '"olleh"'}],
    },
    {
        'id': 4, 'title': 'Count Vowels', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>count_vowels(s)</code> that counts and returns the number of vowels (a, e, i, o, u) in a string. The check should be case-insensitive.',
        'starter': 'def count_vowels(s):\n    # Count vowels a, e, i, o, u (case-insensitive)\n    pass',
        'test_code': '\nassert count_vowels("hello")==2\nassert count_vowels("Python")==1\nassert count_vowels("AEIOU")==5\nassert count_vowels("xyz")==0\nprint("ALL_PASS")',
        'examples': [{'call': 'count_vowels("hello")', 'output': '2'}],
    },
    {
        'id': 5, 'title': 'FizzBuzz', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>fizzbuzz(n)</code> that returns a list of strings for numbers 1 to n: <strong>"FizzBuzz"</strong> if divisible by both 3 and 5, <strong>"Fizz"</strong> if by 3, <strong>"Buzz"</strong> if by 5, otherwise the number as a string.',
        'starter': 'def fizzbuzz(n):\n    result = []\n    for i in range(1, n+1):\n        # Append the correct value to result\n        pass\n    return result',
        'test_code': '\nr=fizzbuzz(15)\nassert r[2]=="Fizz",f"Got {r[2]}"\nassert r[4]=="Buzz",f"Got {r[4]}"\nassert r[14]=="FizzBuzz",f"Got {r[14]}"\nassert r[0]=="1",f"Got {r[0]}"\nprint("ALL_PASS")',
        'examples': [{'call': 'fizzbuzz(5)', 'output': '["1","2","Fizz","4","Buzz"]'}],
    },
    {
        'id': 6, 'title': 'Fibonacci Number', 'difficulty': 'Medium', 'points': 15,
        'description': 'Write a function <code>fibonacci(n)</code> that returns the nth Fibonacci number (0-indexed). <br>fibonacci(0)=0, fibonacci(1)=1, fibonacci(2)=1, fibonacci(6)=8.',
        'starter': 'def fibonacci(n):\n    # Return the nth Fibonacci number\n    pass',
        'test_code': '\nassert fibonacci(0)==0\nassert fibonacci(1)==1\nassert fibonacci(5)==5\nassert fibonacci(10)==55\nprint("ALL_PASS")',
        'examples': [{'call': 'fibonacci(6)', 'output': '8'}],
    },
    {
        'id': 7, 'title': 'Palindrome Check', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>is_palindrome(s)</code> that returns <strong>True</strong> if the string is a palindrome (reads the same forwards and backwards), and <strong>False</strong> otherwise. Ignore case.',
        'starter': 'def is_palindrome(s):\n    # Return True if s is a palindrome (case-insensitive)\n    pass',
        'test_code': '\nassert is_palindrome("racecar")==True\nassert is_palindrome("hello")==False\nassert is_palindrome("Level")==True\nassert is_palindrome("Madam")==True\nprint("ALL_PASS")',
        'examples': [{'call': 'is_palindrome("racecar")', 'output': 'True'}],
    },
    {
        'id': 8, 'title': 'Find Maximum', 'difficulty': 'Easy', 'points': 10,
        'description': 'Write a function <code>find_max(lst)</code> that returns the maximum element in a list. <strong>Do not use Python\'s built-in max() function.</strong>',
        'starter': 'def find_max(lst):\n    # Return maximum element without using max()\n    pass',
        'test_code': '\nassert find_max([1,5,3,9,2])==9\nassert find_max([-1,-5,-3])==-1\nassert find_max([42])==42\nprint("ALL_PASS")',
        'examples': [{'call': 'find_max([3, 1, 7, 2])', 'output': '7'}],
    },
    {
        'id': 9, 'title': 'Prime Number Check', 'difficulty': 'Medium', 'points': 15,
        'description': 'Write a function <code>is_prime(n)</code> that returns <strong>True</strong> if n is a prime number, and <strong>False</strong> otherwise. A prime number is greater than 1 with no divisors other than 1 and itself.',
        'starter': 'def is_prime(n):\n    # Return True if n is prime\n    pass',
        'test_code': '\nassert is_prime(2)==True\nassert is_prime(17)==True\nassert is_prime(1)==False\nassert is_prime(4)==False\nassert is_prime(97)==True\nprint("ALL_PASS")',
        'examples': [{'call': 'is_prime(7)', 'output': 'True'}],
    },
    {
        'id': 10, 'title': 'Two Sum', 'difficulty': 'Medium', 'points': 15,
        'description': 'Write a function <code>two_sum(nums, target)</code> that, given a list of integers and a target integer, returns the <strong>indices</strong> of the two numbers that add up to target as a list <code>[i, j]</code> where i &lt; j. Assume exactly one solution exists.',
        'starter': 'def two_sum(nums, target):\n    # Return [i, j] where nums[i] + nums[j] == target\n    pass',
        'test_code': '\nr=two_sum([2,7,11,15],9)\nassert sorted(r)==[0,1],f"Got {r}"\nr2=two_sum([3,2,4],6)\nassert sorted(r2)==[1,2],f"Got {r2}"\nprint("ALL_PASS")',
        'examples': [{'call': 'two_sum([2,7,11,15], 9)', 'output': '[0, 1]'}],
    },
]



# ── Browser Violation API ──────────────────────────────────────────────────────────────
_BROWSER_VTYPES = frozenset([
    'clipboard_access', 'window_focus_lost',
    'rapid_tab_switch', 'multiple_monitor_suspected',
    'fullscreen_exit',
])

@app.route('/browser/violation/<int:session_id>', methods=['POST'])
@login_required
def browser_violation(session_id):
    session_obj = ExamSession.query.get_or_404(session_id)
    if session_obj.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data    = request.get_json(silent=True) or {}
    vtype   = data.get('violation_type', '')
    details = str(data.get('details', ''))[:500]

    if vtype not in _BROWSER_VTYPES:
        return jsonify({'error': 'Unknown violation type'}), 400

    weight   = Config.VIOLATION_WEIGHTS.get(vtype, 10)
    severity = 'high' if weight >= 20 else 'medium' if weight >= 10 else 'low'

    v = Violation(
        session_id=session_id, violation_type=vtype,
        severity=severity, details=details, timestamp=datetime.utcnow()
    )
    db.session.add(v)
    session_obj.total_violations = (session_obj.total_violations or 0) + 1
    db.session.commit()

    ps = proctoring_sessions.get(session_id)
    if ps:
        ps['risk'].update([(vtype, details, severity)])

    socketio.emit('proctor_update', {
        'session_id': session_id,
        'student': current_user.username,
        'risk_score': ps['risk'].get_summary()['score'] if ps else None,
        'alerts': [{'type': vtype, 'msg': details, 'severity': severity}],
    }, room='admin')

    return jsonify({'status': 'ok', 'severity': severity})


# ── Student Analytics API ──────────────────────────────────────────────────────────────
@app.route('/student/analytics_data')
@login_required
def student_analytics_data():
    sessions = ExamSession.query.filter_by(user_id=current_user.id).all()
    if not sessions:
        return jsonify({
            'integrity_score': 100,
            'most_common_violation': None,
            'violation_counts': {},
            'risk_history': [],
            'total_exams': 0,
            'total_violations': 0,
        })

    session_ids     = [s.id for s in sessions]
    violations      = Violation.query.filter(Violation.session_id.in_(session_ids)).all()

    violation_counts = {}
    for v in violations:
        violation_counts[v.violation_type] = violation_counts.get(v.violation_type, 0) + 1

    most_common     = max(violation_counts, key=violation_counts.get) if violation_counts else None
    sorted_sess     = sorted(sessions, key=lambda s: s.start_time)
    risk_history    = [
        {'exam': s.exam_name[:20], 'risk': round(s.final_risk_score or 0, 1),
         'date': s.start_time.strftime('%b %d')}
        for s in sorted_sess[-10:]
    ]
    avg_risk        = sum(s.final_risk_score or 0 for s in sessions) / len(sessions)
    integrity_score = max(0, min(100, round(100 - avg_risk)))

    return jsonify({
        'integrity_score': integrity_score,
        'most_common_violation': most_common,
        'violation_counts': violation_counts,
        'risk_history': risk_history,
        'total_exams': len(sessions),
        'total_violations': len(violations),
    })


# â”€â”€ Report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/report/<int:session_id>')
@login_required
def generate_report(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    violations = Violation.query.filter_by(session_id=session_id).all()
    ps = proctoring_sessions.get(session_id, {})
    risk = ps.get('risk', RiskScorer())
    summary = risk.get_summary()
    if exam_session.final_risk_score:
        summary['score'] = exam_session.final_risk_score
    summary['total_violations'] = exam_session.total_violations or len(violations)
    gen = ReportGenerator()
    path = f"static/screenshots/report_{session_id}.pdf"
    gen.generate(exam_session, violations, summary, path)
    return send_file(path, as_attachment=True,
                     download_name=f"report_{exam_session.student.username}.pdf")

# â”€â”€ Admin Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    active_sessions = ExamSession.query.filter_by(status='active').all()
    completed_sessions = ExamSession.query.filter(
        ExamSession.status.in_(['completed', 'terminated'])
    ).order_by(ExamSession.start_time.desc()).limit(50).all()
    all_sessions = ExamSession.query.order_by(ExamSession.start_time.desc()).limit(50).all()
    students = User.query.filter_by(role='student').all()
    total_violations = db.session.query(db.func.count(Violation.id)).scalar() or 0
    return render_template('admin_dashboard.html',
                           active_sessions=active_sessions,
                           completed_sessions=completed_sessions,
                           all_sessions=all_sessions,
                           students=students,
                           total_students=len(students),
                           total_sessions=len(all_sessions),
                           total_violations=total_violations)

@app.route('/admin/violations/<int:session_id>')
@login_required
def get_violations(session_id):
    violations = Violation.query.filter_by(session_id=session_id)\
                                .order_by(Violation.timestamp.desc()).limit(50).all()
    return jsonify([{
        'type': v.violation_type,
        'severity': v.severity,
        'timestamp': str(v.timestamp)[:19],
        'details': v.details,
        'screenshot': v.screenshot_path
    } for v in violations])

@app.route('/admin/terminate/<int:session_id>', methods=['POST'])
@login_required
def terminate_session(session_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    exam_session = ExamSession.query.get_or_404(session_id)
    exam_session.status = 'terminated'
    exam_session.end_time = datetime.utcnow()
    db.session.commit()
    socketio.emit('session_terminated', {'session_id': session_id}, room='admin')
    return jsonify({'success': True})

@app.route('/admin/add_question', methods=['POST'])
@login_required
def add_question():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    q = Question(
        exam_name=data.get('exam_name', data.get('subject', 'Default')),
        question_text=data.get('question_text', data.get('question', '')),
        option_a=data.get('option_a', data.get('a', '')),
        option_b=data.get('option_b', data.get('b', '')),
        option_c=data.get('option_c', data.get('c', '')),
        option_d=data.get('option_d', data.get('d', '')),
        correct_answer=data.get('correct_answer', data.get('correct', 'A'))
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({'success': True, 'id': q.id})

@app.route('/admin/delete_question/<int:qid>', methods=['DELETE'])
@login_required
def delete_question(qid):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/questions/<path:exam_name>')
@login_required
def list_questions(exam_name):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    qs = Question.query.filter_by(exam_name=exam_name).all()
    return jsonify([{
        'id': q.id, 'question_text': q.question_text,
        'option_a': q.option_a, 'option_b': q.option_b,
        'option_c': q.option_c, 'option_d': q.option_d,
        'correct_answer': q.correct_answer
    } for q in qs])

@app.route('/admin/student_stats')
@login_required
def student_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    students = User.query.filter_by(role='student').all()
    result = []
    for s in students:
        sessions = ExamSession.query.filter_by(user_id=s.id).all()
        completed = [x for x in sessions if x.status == 'completed']
        avg_score_pct = 0.0
        if completed:
            scored = [x for x in completed if x.total_questions]
            if scored:
                avg_score_pct = round(
                    sum(x.score / x.total_questions * 100 for x in scored) / len(scored), 1
                )
        avg_risk = round(
            sum(x.final_risk_score or 0 for x in completed) / len(completed), 1
        ) if completed else 0.0
        total_viols = db.session.query(db.func.count(Violation.id)).join(
            ExamSession, Violation.session_id == ExamSession.id
        ).filter(ExamSession.user_id == s.id).scalar() or 0
        result.append({
            'id': s.id, 'username': s.username, 'email': s.email,
            'total_exams': len(sessions),
            'completed_exams': len(completed),
            'avg_score_pct': avg_score_pct,
            'avg_risk': avg_risk,
            'total_violations': total_viols,
            'joined': s.created_at.strftime('%Y-%m-%d'),
        })
    return jsonify(result)

@app.route('/admin/session_detail/<int:session_id>')
@login_required
def session_detail(session_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    s = ExamSession.query.get_or_404(session_id)
    viols = Violation.query.filter_by(session_id=session_id)\
                           .order_by(Violation.timestamp.desc()).all()
    return jsonify({
        'id': s.id, 'exam_name': s.exam_name, 'student': s.student.username,
        'status': s.status, 'exam_type': s.exam_type or 'mcq',
        'score': s.score or 0, 'total_questions': s.total_questions or 0,
        'final_risk_score': round(s.final_risk_score or 0, 1),
        'total_violations': s.total_violations or 0,
        'start_time': str(s.start_time)[:19],
        'end_time': str(s.end_time)[:19] if s.end_time else None,
        'violations': [{
            'type': v.violation_type, 'severity': v.severity,
            'timestamp': str(v.timestamp)[:19], 'details': v.details,
        } for v in viols[:100]]
    })

# â”€â”€ SocketIO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@socketio.on('join_admin')
def on_join_admin():
    join_room('admin')
    emit('joined', {'room': 'admin'})

# â”€â”€ Seed Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def seed_data():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@exam.com',
                     password=generate_password_hash('admin123'), role='admin')
        db.session.add(admin)

    if not User.query.filter_by(username='student1').first():
        student = User(username='student1', email='student@exam.com',
                       password=generate_password_hash('student123'), role='student')
        db.session.add(student)

    if not Question.query.first():
        sample_qs = [
            # ── Data Structures & Algorithms ──────────────────────────────
            ('Data Structures & Algorithms','What is the time complexity of binary search?','O(n)','O(log n)','O(n log n)','O(1)','B'),
            ('Data Structures & Algorithms','Which data structure uses LIFO order?','Queue','Heap','Stack','Deque','C'),
            ('Data Structures & Algorithms','What is the worst-case time complexity of QuickSort?','O(n log n)','O(n)','O(n²)','O(log n)','C'),
            ('Data Structures & Algorithms','In a min-heap, where is the smallest element?','Last leaf','Root','Any leaf','Middle','B'),
            ('Data Structures & Algorithms','Which traversal visits root AFTER children?','Pre-order','In-order','Post-order','Level-order','C'),
            ('Data Structures & Algorithms','What is the space complexity of Merge Sort?','O(1)','O(log n)','O(n)','O(n²)','C'),
            ('Data Structures & Algorithms','Which graph algorithm finds shortest path with non-negative weights?','BFS','DFS','Dijkstra','Bellman-Ford','C'),
            ('Data Structures & Algorithms','What is a degenerate BST equivalent to?','Heap','Linked list','Hash table','Stack','B'),
            ('Data Structures & Algorithms','AVL tree maintains balance using what factor?','Height difference ≤ 1','Degree ≤ 2','Color property','Parent pointer','A'),
            ('Data Structures & Algorithms','What does a hash table use to resolve collisions?','Sorting','Chaining or probing','Balancing','Recursion','B'),
            # ── Database Management Systems ───────────────────────────────
            ('Database Management Systems','Which SQL keyword removes duplicate rows from result?','UNIQUE','DISTINCT','FILTER','NODUPE','B'),
            ('Database Management Systems','What does ACID stand for in DBMS?','Atomicity Consistency Isolation Durability','Abstraction Concurrency Integrity Data','Access Control Index Durability','Aggregation Consistency Index Design','A'),
            ('Database Management Systems','Which normal form eliminates transitive dependencies?','1NF','2NF','3NF','BCNF','C'),
            ('Database Management Systems','A foreign key references which key in another table?','Foreign key','Composite key','Primary key','Candidate key','C'),
            ('Database Management Systems','Which JOIN returns all rows from both tables?','INNER JOIN','LEFT JOIN','RIGHT JOIN','FULL OUTER JOIN','D'),
            ('Database Management Systems','What is a deadlock in DBMS?','Slow query','Two transactions waiting on each other','Missing index','Corrupt data','B'),
            ('Database Management Systems','Which command permanently saves a transaction?','ROLLBACK','SAVEPOINT','COMMIT','END','C'),
            ('Database Management Systems','What does ER stand for in ER diagram?','Entity Relationship','Element Record','Execution Routine','Entry Row','A'),
            ('Database Management Systems','Which index type is best for range queries?','Hash index','B-tree index','Bitmap index','Full-text index','B'),
            ('Database Management Systems','What is a view in SQL?','Stored procedure','Virtual table from a SELECT','Trigger','Index','B'),
            # ── Operating Systems ─────────────────────────────────────────
            ('Operating Systems','Which scheduling algorithm gives minimum average waiting time for known burst times?','FCFS','Round Robin','SJF','Priority','C'),
            ('Operating Systems','What is thrashing in OS?','High CPU usage','Excessive paging causing low CPU utilization','Memory leak','Stack overflow','B'),
            ('Operating Systems','Which of the following is NOT a condition for deadlock?','Mutual exclusion','Hold and wait','Preemption','Circular wait','C'),
            ('Operating Systems','What does a semaphore value of 0 indicate?','Resource available','Resource unavailable or all copies in use','Error state','Process terminated','B'),
            ('Operating Systems','Which memory allocation strategy never has external fragmentation?','First fit','Best fit','Paging','Segmentation','C'),
            ('Operating Systems','What is the purpose of a TLB?','Translate logical to physical addresses quickly','Store page tables','Handle page faults','Manage disk I/O','A'),
            ('Operating Systems','Which process state means the process is waiting for I/O?','Ready','Running','Blocked','Terminated','C'),
            ('Operating Systems','What is the critical section problem?','Race condition in shared memory access','Scheduling priority conflict','Memory overflow','Disk failure','A'),
            ('Operating Systems','UNIX uses which system call to create a new process?','create()','spawn()','fork()','exec()','C'),
            ('Operating Systems','Which page replacement algorithm suffers from Belady\'s anomaly?','LRU','Optimal','FIFO','Clock','C'),
            # ── Java Programming ──────────────────────────────────────────
            ('Java Programming','Which keyword prevents a method from being overridden in Java?','static','abstract','final','private','C'),
            ('Java Programming','What is the default value of an int array element in Java?','null','1','-1','0','D'),
            ('Java Programming','Which interface must be implemented to sort objects with Collections.sort()?','Serializable','Runnable','Comparable','Iterable','C'),
            ('Java Programming','What does JVM stand for?','Java Variable Management','Java Virtual Machine','Java Verified Module','Just-in-time Virtual Manager','B'),
            ('Java Programming','Which Java keyword is used for exception handling?','error','handle','try','catch-all','C'),
            ('Java Programming','What is autoboxing in Java?','Converting String to int','Automatic conversion between primitive and wrapper types','Casting objects','Memory boxing','B'),
            ('Java Programming','Which collection class is synchronized in Java?','ArrayList','HashMap','Vector','LinkedList','C'),
            ('Java Programming','What is the output of: System.out.println(10/3) in Java?','3.33','3','4','Error','B'),
            ('Java Programming','Which access modifier makes a member accessible only within the class?','protected','public','default','private','D'),
            ('Java Programming','What does the "super" keyword refer to?','Current class','Parent class','Static method','Interface','B'),
            # ── Design & Analysis of Algorithms ──────────────────────────
            ('Design & Analysis of Algorithms','What technique does dynamic programming use to avoid recomputation?','Recursion','Memoization','Greedy choice','Divide and conquer','B'),
            ('Design & Analysis of Algorithms','Which algorithm solves the 0/1 knapsack problem optimally?','Greedy','Dynamic programming','BFS','Divide and conquer','B'),
            ('Design & Analysis of Algorithms','What is the recurrence relation for Merge Sort?','T(n)=T(n-1)+O(1)','T(n)=2T(n/2)+O(n)','T(n)=T(n/2)+O(1)','T(n)=n·T(1)','B'),
            ('Design & Analysis of Algorithms','Which problem class contains problems solvable in polynomial time?','NP','NP-Hard','P','NP-Complete','C'),
            ('Design & Analysis of Algorithms','Prim\'s and Kruskal\'s algorithms solve which problem?','Shortest path','Minimum spanning tree','Maximum flow','Topological sort','B'),
            ('Design & Analysis of Algorithms','What is the greedy choice property?','Local optimum leads to global optimum','All subproblems are solved','Problems have overlapping subproblems','Divide into equal halves','A'),
            ('Design & Analysis of Algorithms','What does Big-O notation describe?','Best case','Exact running time','Upper bound on growth rate','Lower bound','C'),
            ('Design & Analysis of Algorithms','Which algorithm uses backtracking to solve N-Queens?','Greedy','Dynamic programming','Branch and bound','Backtracking','D'),
            ('Design & Analysis of Algorithms','Strassen\'s algorithm improves which operation?','Sorting','Matrix multiplication','Graph traversal','String matching','B'),
            ('Design & Analysis of Algorithms','A problem is NP-Complete if it is in NP and is:','In P','NP-Hard','Decidable','Polynomial','B'),
            # ── Python Programming ────────────────────────────────────────
            ('Python Programming','What is the output of print(type([]))?','<class list>','<class tuple>','<type list>','list','A'),
            ('Python Programming','Which Python data type is immutable?','list','dict','set','tuple','D'),
            ('Python Programming','What does the "self" parameter refer to in a class method?','The class itself','The parent class','The current instance','A static reference','C'),
            ('Python Programming','What is a lambda function in Python?','A named function','An anonymous inline function','A recursive function','A generator','B'),
            ('Python Programming','What does list comprehension [x**2 for x in range(3)] produce?','[1,4,9]','[0,1,4]','[0,1,2]','[1,2,3]','B'),
            ('Python Programming','Which module is used for regular expressions in Python?','regex','re','regexp','string','B'),
            ('Python Programming','What does the "yield" keyword create?','A list','A generator','A coroutine','A thread','B'),
            ('Python Programming','How do you open a file for reading in Python?','open(f,"w")','open(f)','open(f,"r")','Both B and C','D'),
            ('Python Programming','What is the output of bool("") in Python?','True','None','Error','False','D'),
            ('Python Programming','Which decorator makes a method a class method?','@staticmethod','@classmethod','@property','@method','B'),
            # ── Machine Learning ──────────────────────────────────────────
            ('Machine Learning','Which algorithm minimizes cost function using gradient steps?','Random Forest','Gradient Descent','K-Means','SVM','B'),
            ('Machine Learning','What does overfitting mean?','Model too simple','Model performs well on train but poorly on test','Low training error and low test error','Model fails to converge','B'),
            ('Machine Learning','Which metric is best for imbalanced classification?','Accuracy','MSE','F1-Score','R-Squared','C'),
            ('Machine Learning','What does the kernel trick do in SVM?','Reduces dimensions','Maps data to higher dimension implicitly','Prunes decision tree','Normalizes data','B'),
            ('Machine Learning','What is the role of the activation function in a neural network?','Initialize weights','Introduce non-linearity','Normalize inputs','Compute loss','B'),
            ('Machine Learning','Which technique reduces overfitting by randomly dropping neurons?','Batch normalization','Dropout','Data augmentation','Early stopping','B'),
            ('Machine Learning','In k-fold cross-validation, the dataset is split into how many folds?','2','n (samples)','k','k+1','C'),
            ('Machine Learning','Principal Component Analysis (PCA) is used for?','Classification','Clustering','Dimensionality reduction','Regression','C'),
            ('Machine Learning','Which loss function is used for binary classification?','MSE','Cross-entropy','Hinge loss','MAE','B'),
            ('Machine Learning','What does a confusion matrix show?','Feature importance','Predicted vs actual class counts','Loss curve','Learning rate','B'),
            # ── Artificial Intelligence ───────────────────────────────────
            ('Artificial Intelligence','Which search algorithm uses a heuristic to guide exploration?','BFS','DFS','A*','Uniform Cost Search','C'),
            ('Artificial Intelligence','What is the Turing Test designed to measure?','Processing speed','Machine intelligence via conversation','Memory capacity','Algorithm efficiency','B'),
            ('Artificial Intelligence','Which logic type handles uncertain knowledge?','Propositional logic','First-order logic','Fuzzy logic','Temporal logic','C'),
            ('Artificial Intelligence','What is a knowledge base in an expert system?','Database of rules and facts','Training dataset','Neural network','Decision tree','A'),
            ('Artificial Intelligence','Which technique is used in game-playing AI like chess?','A* Search','Minimax with Alpha-Beta pruning','Genetic algorithm','Hidden Markov model','B'),
            ('Artificial Intelligence','What does NLP stand for?','Neural Learning Process','Natural Language Processing','Network Layer Protocol','Non-Linear Programming','B'),
            ('Artificial Intelligence','A Bayesian network represents what?','Decision tree','Probabilistic dependencies between variables','Recurrent neural layers','Rule-based system','B'),
            ('Artificial Intelligence','Which algorithm is used for constraint satisfaction problems?','Backtracking search','Minimax','Gradient descent','Value iteration','A'),
            ('Artificial Intelligence','What is reinforcement learning\'s reward signal used for?','Labeling data','Guiding agent behavior toward goal','Initializing weights','Pruning search tree','B'),
            ('Artificial Intelligence','STRIPS is a language for?','Natural language parsing','Automated planning','Image recognition','Cryptography','B'),
            # ── Computer Networks ─────────────────────────────────────────
            ('Computer Networks','How many layers does the OSI model have?','4','5','7','8','C'),
            ('Computer Networks','Which protocol assigns IP addresses automatically?','DNS','FTP','DHCP','ARP','C'),
            ('Computer Networks','What does TCP guarantee that UDP does not?','Speed','Reliability and ordering','Encryption','Low latency','B'),
            ('Computer Networks','Which layer is responsible for routing packets?','Data Link','Transport','Network','Session','C'),
            ('Computer Networks','What is the purpose of ARP?','Resolve domain name to IP','Resolve IP address to MAC address','Encrypt packets','Assign ports','B'),
            ('Computer Networks','Which device operates at Layer 2 of the OSI model?','Router','Switch','Hub','Gateway','B'),
            ('Computer Networks','What is the subnet mask for a /24 network?','255.255.0.0','255.0.0.0','255.255.255.0','255.255.255.128','C'),
            ('Computer Networks','Which port does HTTPS use by default?','80','21','443','8080','C'),
            ('Computer Networks','What is the three-way handshake in TCP?','SYN → SYN-ACK → ACK','ACK → SYN → FIN','SYN → ACK → FIN','HELLO → READY → GO','A'),
            ('Computer Networks','Which protocol is used for sending email?','IMAP','POP3','SMTP','FTP','C'),
            # ── Software Engineering ──────────────────────────────────────
            ('Software Engineering','Which SDLC model is iterative and incremental?','Waterfall','V-Model','Agile','Big Bang','C'),
            ('Software Engineering','What does SOLID stand for in OOP design?','5 design principles for maintainable code','Structured Object Layered Interface Design','Server Object Linked Integration Design','Scalable Open Linked Interface Domain','A'),
            ('Software Engineering','Which testing technique tests without knowledge of internal code?','White-box','Grey-box','Black-box','Structural','C'),
            ('Software Engineering','What is the purpose of a design pattern?','Writing fastest code','Reusable solution to common design problem','Defining database schema','Testing methodology','B'),
            ('Software Engineering','Which version control system is distributed?','SVN','CVS','Git','Perforce','C'),
            ('Software Engineering','What does CI/CD stand for?','Code Integration / Code Deployment','Continuous Integration / Continuous Deployment','Component Interface / Component Design','Compiled Input / Computed Data','B'),
            ('Software Engineering','Which Agile ceremony estimates story points?','Daily standup','Sprint review','Planning poker','Retrospective','C'),
            ('Software Engineering','A use case diagram belongs to which modeling language?','BPMN','ER notation','UML','Flowchart','C'),
            ('Software Engineering','What is the purpose of code refactoring?','Add new features','Fix critical bugs','Improve code structure without changing behavior','Increase performance only','C'),
            ('Software Engineering','Which metric measures the number of independent paths through code?','LOC','Cyclomatic complexity','Coupling','Cohesion','B'),
        ]
        for qdata in sample_qs:
            q = Question(exam_name=qdata[0], question_text=qdata[1],
                         option_a=qdata[2], option_b=qdata[3],
                         option_c=qdata[4], option_d=qdata[5],
                         correct_answer=qdata[6])
            db.session.add(q)

    db.session.commit()

# â”€â”€ Run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def migrate_db():
    """Add any missing columns to existing tables (safe to run every startup)."""
    with db.engine.connect() as conn:
        # exam_sessions new columns
        for col, typedef in [
            ('score',           'INTEGER DEFAULT 0'),
            ('total_questions', 'INTEGER DEFAULT 0'),
            ('exam_type',       "VARCHAR(20) DEFAULT 'mcq'"),
        ]:
            try:
                conn.execute(db.text(f'ALTER TABLE exam_sessions ADD COLUMN {col} {typedef}'))
                conn.commit()
            except Exception:
                pass  # column already exists

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_db()
        seed_data()
    socketio.run(
        app,
        host="0.0.0.0",
        port=5050,
        debug=True,
        allow_unsafe_werkzeug=True,
        use_reloader=False
    )
@app.route('/test')
def test():
    return "<h1 style='color:red'>TEST PAGE</h1>"