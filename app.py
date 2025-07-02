from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import zipfile
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'smarthire123'

# ──────────────────────────────────────────────
# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Manisha@2204'
app.config['MYSQL_DB'] = 'smarthire'

mysql = MySQL(app)

# ──────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

# ──────────────────────────────────────────────
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM recruiters WHERE email = %s AND password = %s", (email, password))
        recruiter = cur.fetchone()
        cur.close()

        if recruiter:
            session['recruiter_id'] = recruiter[0]
            session['recruiter_name'] = recruiter[1]
            flash('Signed in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('signin'))

    return render_template('Signin.html')

# ──────────────────────────────────────────────
@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_recruiter():
    full_name = request.form['full_name']
    email = request.form['email']
    password = request.form['password']
    phone = request.form['phone']

    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO recruiters (full_name, email, password, phone) VALUES (%s, %s, %s, %s)",
                    (full_name, email, password, phone))
        mysql.connection.commit()
        cur.close()
        flash("Registration successful! Please sign in.", "success")
        return redirect(url_for('signin'))
    except Exception as e:
        flash("Email already registered or error occurred.", "error")
        return redirect(url_for('register'))

# ──────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'recruiter_id' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cur.execute("SELECT COUNT(*) AS total FROM candidates")
        total_applications = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) AS selected FROM candidates WHERE status='Shortlisted'")
        selected_count = cur.fetchone()['selected']

        cur.execute("SELECT COUNT(*) AS pending FROM candidates WHERE status='Pending'")
        pending_count = cur.fetchone()['pending']

        cur.execute("SELECT COUNT(*) AS rejected FROM candidates WHERE status='Rejected'")
        rejected_count = cur.fetchone()['rejected']

        cur.execute("SELECT * FROM candidates ORDER BY id DESC LIMIT 5")
        recent_candidates = cur.fetchall()
        cur.close()

        return render_template(
            "dashboard.html",
            name=session['recruiter_name'],
            total_applications=total_applications,
            selected_count=selected_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            candidates=recent_candidates
        )
    else:
        flash("Please sign in to access dashboard.", "error")
        return redirect(url_for('signin'))


# ──────────────────────────────────────────────
@app.route('/applications')
def applications():
    if 'recruiter_id' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM candidates")
        all_candidates = cur.fetchall()
        cur.close()
        return render_template("applications.html", candidates=all_candidates, name=session['recruiter_name'])
    else:
        return redirect(url_for('signin'))

# ──────────────────────────────────────────────
@app.route('/export_resumes')
def export_resumes():
    resume_folder = os.path.join('static', 'resumes')
    zip_io = BytesIO()

    with zipfile.ZipFile(zip_io, 'w') as zipf:
        for filename in os.listdir(resume_folder):
            file_path = os.path.join(resume_folder, filename)
            zipf.write(file_path, arcname=filename)

    zip_io.seek(0)
    return send_file(zip_io, mimetype='application/zip', as_attachment=True, download_name='resumes.zip')

# ──────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('signin'))

# ──────────────────────────────────────────────
@app.route('/candidate')
def candidate():
    return render_template('candidate.html')

# ──────────────────────────────────────────────
@app.route('/submit', methods=['POST'])
def submit_candidate():
    data = request.form
    file = request.files['resume']

    filename = secure_filename(file.filename)
    filepath = os.path.join('static/resumes', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO candidates (
                title, first_name, last_name, email, phone,
                graduation_year, gender, experience, current_employer,
                current_ctc, expected_ctc, notice_period, skills, source,
                current_location, preferred_location, resume_filename, candidate_type, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """, (
            data['title'], data['first_name'], data['last_name'], data['email'], data['phone'],
            data['graduation_year'], data['gender'], data.get('experience') or '',
            data.get('current_employer') or '', data.get('current_ctc') or '',
            data.get('expected_ctc') or '', data.get('notice_period') or '',
            data['skills'], data['source'], data['current_location'],
            data['preferred_location'], filename, data['candidate_type']
        ))
        mysql.connection.commit()
        cur.close()
        flash("Application submitted successfully!", "success")
        return redirect(url_for('home'))
    except Exception as e:
        print("Error submitting candidate:", e)
        flash("Error submitting application.", "error")
        return redirect(url_for('home'))

# ──────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
