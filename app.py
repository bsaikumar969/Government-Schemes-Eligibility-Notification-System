# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
from translate import Translator
import smtplib
from email.mime.text import MIMEText
from functools import wraps
import re  # For email validation
import time
import threading

# Flask app initialization
app = Flask(__name__)
app.secret_key = 'your_secret_key'
translator = Translator(to_lang="")

# Email validation function
def is_valid_email(email):
    """Validate the email address format."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

# Your other code...




# MySQL Database connection
def get_db_connection():
    return pymysql.connect(host='localhost',user='root',passwd='sai12345',database="schemes_db")

# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(50) UNIQUE,
        password VARCHAR(50),
        language VARCHAR(10),
        income INT DEFAULT NULL,
        gender VARCHAR(10) DEFAULT NULL,
        age INT DEFAULT NULL,
        state VARCHAR(10) DEFAULT NULL,
        area VARCHAR(10) DEFAULT NULL,
        caste VARCHAR(10) DEFAULT NULL,
        occupation VARCHAR(50) DEFAULT NULL,
        units INT DEFAULT NULL
    )''')


    cursor.execute('''CREATE TABLE IF NOT EXISTS schemes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        criteria TEXT,
        description TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        scheme_id INT,
        sent BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (scheme_id) REFERENCES schemes(id)
    )''')

    # Table to track new schemes added
     # Table to track new schemes added
    cursor.execute('''CREATE TABLE IF NOT EXISTS new_schemes_notifier (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scheme_id INT,
        processed BOOLEAN DEFAULT FALSE
        #FOREIGN KEY (scheme_id) REFERENCES schemes(id)
    )''')

    conn.commit()
    conn.close()
    

# Add sample data to database
'''def add_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO schemes (id, name, criteria, description) VALUES (1, 'Scholarship Scheme', 'income<=30000;caste:student', 'Financial aid for students')")
    cursor.execute("INSERT IGNORE INTO schemes (id, name, criteria, description) VALUES (2, 'Farmer Support', 'certificates:farmer', 'Subsidies for farmers')")
    conn.commit()'''
def is_user_eligible(user, criteria):
    """Check if a user matches scheme criteria."""
    criteria_list = criteria.split(';')

    for criterion in criteria_list:
        if '<=' in criterion:
            key, value = criterion.split('<=')
            if key in user and int(user[key]) > int(value):
                return False
        elif ':' in criterion:
            key, value = criterion.split(':')
            if key in user and user[key] != value:
                return False

    return True

    

'''def process_new_schemes():
    """ Continuously check for new schemes and notify users. """
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch unprocessed new schemes
        cursor.execute("SELECT scheme_id FROM new_schemes_notifier WHERE processed = FALSE")
        new_schemes = cursor.fetchall()

        for scheme in new_schemes:
            scheme_id = scheme[0]

            # Fetch scheme details
            cursor.execute("SELECT * FROM schemes WHERE id = %s", (scheme_id,))
            scheme_data = cursor.fetchone()

            if scheme_data:
                name, criteria, description = scheme_data[1], scheme_data[2], scheme_data[3]

                # Fetch all users
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()

                for user in users:
                    user_details = {
                        'income': user[3],
                        'gender': user[4],
                        'age': user[5],
                        'state': user[6],
                        'area': user[7],
                        'caste': user[8],
                        'occupation': user[9],
                        'units': user[10]
                    }

                    # Check if user is eligible
                    if is_user_eligible(user_details, criteria):
                        email = user[1]
                        language = user[2]

                        # Translate description
                        translator = Translator(to_lang=language)
                        translated_desc = translator.translate(description)

                        body = f"Hello,\n\nYou are eligible for the new scheme: {name}\n\nDetails: {translated_desc}\n\nBest regards,\nGovernment Schemes Portal"
                        send_email(email, "New Government Scheme Available", body)

                        # Store notification in database
                        cursor.execute("INSERT INTO notifications (user_id, scheme_id, sent) VALUES (%s, %s, %s)",
                                       (user[0], scheme_id, True))

            # Mark scheme as processed
            cursor.execute("UPDATE new_schemes_notifier SET processed = TRUE WHERE scheme_id = %s", (scheme_id,))
            conn.commit()

        conn.close()
        time.sleep(10)'''
def process_new_schemes():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch new unprocessed schemes
    cursor.execute("SELECT scheme_id FROM new_schemes_notifier WHERE processed = FALSE")
    new_schemes = cursor.fetchall()

    if not new_schemes:
        return
    
    for (scheme_id,) in new_schemes:
        # Fetch scheme details
        cursor.execute("SELECT * FROM schemes WHERE id = %s", (scheme_id,))
        scheme = cursor.fetchone()
        
        if not scheme:
            continue

        # Extract the scheme details
        name = scheme[1]
        criteria = scheme[2]  # Assuming `criteria` is the second field
        description = scheme[3]

        # Fetch all users
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        for user in users:
            user_details = {
                'income': user[4],
                'gender': user[5],
                'age': user[6],
                'state': user[7],
                'area': user[8],
                'caste': user[9],
                'occupation': user[10],
                'units': user[11]
            }
            
            if is_user_eligible(user_details, criteria):  # Check if user is eligible
                send_email(user[1], "New Scheme Available", f"You are eligible for {name}: {description}")

        # Mark as processed
        cursor.execute("UPDATE new_schemes_notifier SET processed = TRUE WHERE scheme_id = %s", (scheme_id,))
        conn.commit()

    conn.close()


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Match user to eligible schemes
def match_schemes(user):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schemes")
    schemes = cursor.fetchall()
    eligible_schemes = []

    for scheme in schemes:
        criteria = scheme[2].split(';')  # Accessing the 'criteria' field by index (2)
        is_eligible = True
        for criterion in criteria:
            if '<=' in criterion:
                key, value = criterion.split('<=')
                if key == 'income' and user['income'] > int(value):
                    is_eligible = False
                if key == 'age' and user['age'] > int(value):
                    is_eligible = False
                if key == 'units' and user['units'] > int(value):
                    is_eligible = False
            elif ':' in criterion:
                key, value = criterion.split(':')
                if key == 'gender' and value not in user['gender']:
                    is_eligible = False
                if key == 'state' and value != user['state']:
                    is_eligible = False
                if key == 'area' and value not in user['area']:
                    is_eligible = False
                if key == 'caste' and value not in user['caste']:
                    is_eligible = False
                if key == 'occupation' and value not in user['occupation']:
                    is_eligible = False
        if is_eligible:
            eligible_schemes.append(scheme)

    conn.close()
    return eligible_schemes


# Send email notification
'''def send_email(to_email, subject, body):
    from_email = "bsaikumar969@gmail.com"
    password = "tfai cjvr oawz jmfd"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print("Failed to send email:", e)'''
def send_email(to_email, subject, body):
    if not is_valid_email(to_email):
        print(f"Invalid email address: {to_email}")
        return

    from_email = "bsaikumar969@gmail.com"
    password = "tfai cjvr oawz jmfd"  # Replace with a valid app password

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        #print("Email sent successfully!")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"Failed to send email. Invalid recipient: {to_email}. Error: {e}")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        language = request.form.get('language', '').strip()

        if not email or not password or not language:
            return "All fields are required!", 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password, language) VALUES (%s, %s, %s)", (email, password, language))
            conn.commit()
        except pymysql.connect.Error as err:
            return f"Database error: {err}", 500
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            return "Both email and password are required!", 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')



@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email,language,income,gender,age,state,area, caste, occupation,units,email,language  FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

     # Fetch dropdown data
    genders = ['Male', 'Female']
    states = [
    'Andhra Pradesh', 
    'Arunachal Pradesh', 
    'Assam', 
    'Bihar', 
    'Chhattisgarh', 
    'Goa', 
    'Gujarat', 
    'Haryana', 
    'Himachal Pradesh', 
    'Jharkhand', 
    'Karnataka', 
    'Kerala', 
    'Madhya Pradesh', 
    'Maharashtra', 
    'Manipur', 
    'Meghalaya', 
    'Mizoram', 
    'Nagaland', 
    'Odisha', 
    'Punjab', 
    'Rajasthan', 
    'Sikkim', 
    'Tamil Nadu', 
    'Telangana', 
    'Tripura', 
    'Uttar Pradesh', 
    'Uttarakhand', 
    'West Bengal',
    'Andaman and Nicobar Islands', 
    'Chandigarh', 
    'Dadra and Nagar Haveli and Daman and Diu', 
    'Delhi', 
    'Jammu and Kashmir', 
    'Ladakh', 
    'Lakshadweep', 
    'Puducherry'
]
    areas = ['Rural', 'Urban']
    castes = ['General', 'OBC','SC/ST']  # Adjust according to your application

    if request.method == 'POST':
        # Fetch form data
        income = request.form.get('income', '').strip()
        gender = request.form.get('gender', '').strip()
        age = request.form.get('age', '').strip()
        state = request.form.get('state', '').strip()
        area = request.form.get('area', '').strip()
        caste = request.form.get('caste', '').strip()
        occupation = request.form.get('occupation', '').strip()
        occupation = occupation.lower()
        units = request.form.get('units', '').strip()
        # Update user details in the database
        cursor.execute(
            "UPDATE users SET income = %s, gender = %s, age = %s, state = %s, area = %s, caste = %s, occupation = %s, units = %s WHERE id = %s",(income, gender, age, state, area, caste, occupation, units, session['user_id'])
        )
        conn.commit()

        # Prepare user details for scheme matching
        user_details = {
            'income': int(income),
            'gender': gender,
            'age': int(age),
            'state': state,
            'area': area,
            'caste': caste,
            'occupation': occupation,
            'units': int(units)
        }

        eligible_schemes = match_schemes(user_details)
        translated_schemes = []

        # Send eligible schemes via email
        if eligible_schemes:
            language = user[1]  # Fetch preferred language
            email = user[0]  # Fetch user email
            body = "Hello,\n\nYou are eligible for the following schemes:\n"

            for scheme in eligible_schemes:
                translator = Translator(to_lang=language)
                translated_desc = translator.translate(scheme[3])  # Translate scheme description
                body += f"- {scheme[1]}: {translated_desc}\n"
                translated_schemes.append({'name': scheme[1], 'description': scheme[3],'translated_desc':translated_desc})

            body += "\nBest regards,\nGovernment Schemes Portal"
            send_email(user[0], "Your Eligible Government Schemes", body)


            return render_template('schemes.html', schemes=translated_schemes)
        else:
            return "No eligible schemes found."

    # Render dashboard with user data
    return render_template(
        'dashboard.html',
        income=user[2] if user else '',
        gender=user[3] if user else '',
        age=user[4] if user else '',
        state=user[5] if user else '',
        area=user[6] if user else '',
        caste=user[7] if user else '',
        occupation=user[8] if user else '',
        units=user[9] if user else '',
        genders=genders,
        states=states,
        areas=areas,
        castes=castes
    )

if __name__ == '__main__':
    init_db()
    #add_sample_data()
    background_thread = threading.Thread(target=process_new_schemes, daemon=True)
    background_thread.start()
    app.run(debug=True)