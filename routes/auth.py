from flask import render_template, request, redirect, session, flash
from routes import auth_bp
from db import get_db
import hashlib

def md5_encrypt(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()

@auth_bp.route('/', methods=['GET', 'POST'])
def ret():
        return redirect('/login')
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_md5 = md5_encrypt(request.form['password'])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_user WHERE username=%s AND password_md5=%s", (username, password_md5))
        user = cursor.fetchone()
        if user:
            session['admin'] = True
            session['username'] = username
            return redirect('/dashboard')
        else:
            flash("用户名或密码错误")
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        invite = request.form['invite']
        if password != confirm:
            flash("密码不一致")
        elif invite != "114514":
            flash("邀请码错误")
        else:
            password_md5 = md5_encrypt(password)
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO admin_user (username, password_md5) VALUES (%s, %s)", (username, password_md5))
                conn.commit()
                flash("注册成功")
                return redirect('/login')
            except:
                flash("注册失败，用户名可能已存在")
    return render_template('register.html')

@auth_bp.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        cardID = request.form.get('cardID')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT pass FROM cardInfo WHERE cardID = %s", (cardID,))
        user = cursor.fetchone()

        if user and user['pass'] == password:
            session.clear()
            session['cardID'] = cardID  # 记录客户登录状态
            flash('登录成功')
            return redirect('/user_dashboard')
        else:
            flash('卡号或密码错误')

    return render_template('auth/user_login.html')