from app import app
from extensions import db, login_manager
from models import User, SearchHistory, Subscription

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import subprocess
import os


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        existing = User.query.filter_by(username=username).first()

        if existing:
            flash('Username already exists')
            return redirect(url_for('register'))

        user = User(username=username, password=password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful')

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for('dashboard'))

        flash('Invalid login credentials')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():

    searches = SearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SearchHistory.created_at.desc()
    ).all()

    return render_template(
        'dashboard.html',
        username=current_user.username,
        searches=searches
    )


@app.route('/search', methods=['POST'])
@login_required
def search():

    username = request.form['username']

    command = [
        'python',
        os.path.expanduser('~/sherlock/sherlock_project/sherlock.py'),
        username,
        '--print-found'
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = result.stdout

    report_path = f'reports/{username}.txt'

    with open(report_path, 'w') as file:
        file.write(output)

    history = SearchHistory(
        searched_username=username,
        result_file=report_path,
        user_id=current_user.id
    )

    db.session.add(history)
    db.session.commit()

    return render_template(
        'result.html',
        username=username,
        output=output
    )


@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('home'))
