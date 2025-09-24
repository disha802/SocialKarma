from flask import Flask, render_template, request, redirect, url_for, flash, session
import csv
import random 
import os
from datetime import datetime
from confession import run_confession_bot, score_deed_with_sentiment

DEEDS_FILE = 'data/deeds.csv'
MOOD_FILE = 'moods.csv'


app = Flask(__name__)
app.secret_key = 'super_secret_karma_key'  # for sessions + flash

# Dummy user
dummy_user = {
    'email': 'test@karma.com',
    'password': '1234',
    'name': 'User'
}

def get_random_quote():
    with open('data/quotes.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        quotes = [row['quote'] for row in reader if row['quote'].strip()]
    return random.choice(quotes)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == dummy_user['email'] and password == dummy_user['password']:
            session['user_name'] = dummy_user['name']
            flash('Login successful 🎉', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials 💀', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        flash('Please login first 🙃', 'error')
        return redirect(url_for('login'))
    quote = get_random_quote()
    return render_template('index.html', user_name=session['user_name'], quote=quote)

@app.route('/logout')
def logout():
    session.clear()
    flash('You’ve been logged out 👋', 'info')
    return redirect(url_for('login'))

@app.route("/confession", methods=["GET", "POST"])
def run_bot_confession():
    print("⚡ [DEBUG] Confession route triggered!")  
    if 'user_name' not in session:
        flash('Please login first 🙃', 'error')
        return redirect(url_for('login'))
    
    if request.method == "POST":
        user_msg = request.form.get("message", "")
        tone = request.form.get("tone", "Empathetic")
        # print(f"➡️ [DEBUG] Sending message to bot: {user_msg}")
        run_confession_bot(user_msg, tone)
        # print("↩️ [DEBUG] Bot finished processing, redirecting...")
        return redirect(url_for("run_bot_confession"))

    return render_template("confessions.html")


@app.route("/confession/reset")
def reset_confession():
    session.pop("history", None)  # ✅ Remove chat memory
    flash("Conversation cleared 🧹", "info")
    return redirect(url_for("run_bot_confession"))


@app.route('/mood', methods=['GET', 'POST'])
def mood_logger():
    if 'user_name' not in session:
        flash('Please login first 🙃', 'error')
        return redirect(url_for('login'))
    
    
    mood_file = 'moods.csv'

    # Ensure the CSV file exists with headers
    if not os.path.exists(mood_file):
        with open(mood_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['emoji', 'note', 'timestamp'])

    if request.method == 'POST':
        emoji = request.form.get('emoji')
        note = request.form.get('note', '').strip()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if emoji:
            with open(mood_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([emoji, note, timestamp])
        return redirect('/mood')

    moods = []
    with open(mood_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reversed(list(reader)):
            moods.append({
                'emoji': row['emoji'],
                'note': row['note'],
                'timestamp': row['timestamp']
            })

    return render_template('mood.html', moods=moods)

@app.route('/delete_mood', methods=['POST'])
def delete_mood():
    timestamp_to_delete = request.form.get('timestamp')
    mood_file = 'moods.csv'
    updated_moods = []

    with open(mood_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['timestamp'] != timestamp_to_delete:
                updated_moods.append(row)

    with open(mood_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['emoji', 'note', 'timestamp'])
        writer.writeheader()
        writer.writerows(updated_moods)

    return redirect('/mood')


@app.route('/motivation')
def motivation():
    return "<h2>Motivational Quote of the Day page</h2>"

@app.route('/zen')
def zen_zone():
    if 'user_name' not in session:
        flash('Please login first 🙃', 'error')
        return redirect(url_for('login'))
    return render_template('zen.html')


@app.route('/karma', methods=['GET', 'POST'])
def karma():
    if 'user_name' not in session:
        flash('Please login first 🙃', 'error')
        return redirect(url_for('login'))

    os.makedirs('data', exist_ok=True)

    # Handle form submission
    if request.method == 'POST':
        new_deed = request.form.get('deed')
        if new_deed and new_deed.strip():
            points, reason = score_deed_with_sentiment(new_deed)
            print(f"📝 [DEBUG] Deed: {new_deed}, Points: {points}, Reason: {reason}")
            with open(DEEDS_FILE, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([new_deed.strip(), points, reason])
        return redirect(url_for('karma'))

    # Load deeds from CSV
    deeds = []
    total_points = 0
    if os.path.exists(DEEDS_FILE):
        with open(DEEDS_FILE, encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 3:
                    deed, points, reason = row
                    points = int(points)
                elif len(row) == 2:
                    deed, points = row
                    points, reason = int(points), ""
                else:
                    deed, points, reason = row[0], 1, ""
                deeds.append({"text": deed, "points": points, "reason": reason})
                total_points += points

    progress_percent = min(max(total_points, 0) * 10, 100)

    return render_template(
        'karma.html',
        deeds=deeds,
        total_points=total_points,
        progress_percent=progress_percent
    )

@app.route('/delete-deed/<int:deed_id>', methods=['POST'])
def delete_deed(deed_id):
    if os.path.exists(DEEDS_FILE):
        with open(DEEDS_FILE, encoding='utf-8') as f:
            deeds = [row for row in csv.reader(f)]

        if 0 <= deed_id < len(deeds):
            deeds.pop(deed_id)

        with open(DEEDS_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(deeds)

    return redirect(url_for('karma'))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
