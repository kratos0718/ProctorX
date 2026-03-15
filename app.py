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

@app.route('/exam/<int:session_id>')
@login_required
def exam_page(session_id):
    exam_session = ExamSession.query.get_or_404(session_id)
    if exam_session.user_id != current_user.id:
        return redirect(url_for('student_home'))
    questions = Question.query.filter_by(exam_name=exam_session.exam_name).all()
    return render_template('exam.html', session=exam_session, questions=questions)

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
            ('Python Basics', 'What is the output of print(2 ** 3)?',
             '6', '8', '9', '12', 'B'),
            ('Python Basics', 'Which keyword defines a function in Python?',
             'func', 'def', 'function', 'define', 'B'),
            ('Python Basics', 'What does len([1,2,3]) return?',
             '2', '4', '3', '1', 'C'),
            ('Python Basics', 'Which data type is mutable?',
             'tuple', 'string', 'list', 'int', 'C'),
            ('Python Basics', 'What does // operator do?',
             'Division', 'Modulo', 'Floor division', 'Power', 'C'),
        ]
        for qdata in sample_qs:
            q = Question(exam_name=qdata[0], question_text=qdata[1],
                         option_a=qdata[2], option_b=qdata[3],
                         option_c=qdata[4], option_d=qdata[5],
                         correct_answer=qdata[6])
            db.session.add(q)

    db.session.commit()

# â”€â”€ Run â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
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