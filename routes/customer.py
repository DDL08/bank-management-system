from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from db import get_db
from datetime import datetime
import csv
from flask import Response

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')
auth_bp = Blueprint('auth', __name__)


# 登录检查装饰器
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'cardID' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# 首页 / 仪表盘
@customer_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('customer/dashboard.html', cardID=session['cardID'])

# 1. 余额查询
@customer_bp.route('/balance')
@login_required
def check_balance():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM cardInfo WHERE cardID = %s", (session['cardID'],))
    balance = cursor.fetchone()
    return render_template('customer/balance.html', balance=balance)
4

# 2. 交易查询
@customer_bp.route('/trades')
@login_required
def view_trades():
    conn = get_db()
    cursor = conn.cursor()

    # 获取所有交易记录
    cursor.execute("""
        SELECT * FROM tradeinfo 
        WHERE cardID = %s ORDER BY tradeDate DESC
    """, (session['cardID'],))
    trades = cursor.fetchall()

    # 总交易额（全部）
    cursor.execute("""
        SELECT SUM(tradeMoney) AS total_amount
        FROM tradeinfo
        WHERE cardID = %s
    """, (session['cardID'],))
    total_result = cursor.fetchone()
    total_amount = total_result['total_amount'] if total_result['total_amount'] else 0.00

    # 本月月末汇总（当月交易总额 + 交易次数）
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute("""
        SELECT 
            SUM(tradeMoney) AS month_total,
            COUNT(*) AS month_count
        FROM tradeinfo
        WHERE cardID = %s AND DATE_FORMAT(tradeDate, '%%Y-%%m') = %s
    """, (session['cardID'], current_month))
    month_summary = cursor.fetchone()
    month_total = month_summary['month_total'] if month_summary['month_total'] else 0.00
    month_count = month_summary['month_count']

    return render_template(
        'customer/trades.html',
        trades=trades,
        total_amount=total_amount,
        month_total=month_total,
        month_count=month_count
    )
# 2.2 交易导出
@customer_bp.route('/trades/export')
@login_required
def export_trades():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tradeID, cardID, tradeType, tradeMoney, tradeDate
        FROM tradeinfo
        WHERE cardID = %s
        ORDER BY tradeDate DESC
    """, (session['cardID'],))
    trades = cursor.fetchall()

    # 生成 CSV 数据
    def generate():
        yield '交易ID,卡号,交易类型,金额,交易日期\n'
        for row in trades:
            yield f'{row["tradeID"]},{"'" + str(row['cardID'])},{row["tradeType"]},{row["tradeMoney"]},{row["tradeDate"]}\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=trades.csv"})

# 3. 存款
@customer_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT pass FROM cardInfo WHERE cardID = %s", (session['cardID'],))
        correct_pass = cursor.fetchone()

        if correct_pass and password == correct_pass['pass']:
            cursor.execute("""
                UPDATE cardInfo SET balance = balance + %s WHERE cardID = %s
            """, (amount, session['cardID']))
            cursor.execute("""
                INSERT INTO tradeinfo (tradeType, tradeMoney, cardID, remark, tradeDate)
                VALUES ('存入', %s, %s, '客户存款', NOW())
            """, (amount, session['cardID']))
            conn.commit()
            flash("存款成功")
        else:
            flash("密码错误")

    return render_template('customer/deposit.html')

# 4. 取款
@customer_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT balance, pass FROM cardInfo WHERE cardID = %s", (session['cardID'],))
        row = cursor.fetchone()

        if row and password == row['pass']:
            if row['balance'] >= amount and amount >= 1:
                cursor.execute("""
                    UPDATE cardInfo SET balance = balance - %s WHERE cardID = %s
                """, (amount, session['cardID']))
                cursor.execute("""
                    INSERT INTO tradeinfo (tradeType, tradeMoney, cardID, remark, tradeDate)
                    VALUES ('支取', %s, %s, '客户取款', NOW())
                """, (amount, session['cardID']))
                conn.commit()
                flash("取款成功")
            else:
                flash("余额不足或金额小于1元")
        else:
            flash("密码错误")

    return render_template('customer/withdraw.html')

# 5. 挂失
@customer_bp.route('/report_loss', methods=['POST'])
@login_required
def report_loss():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE cardInfo SET IsReportLoss = TRUE WHERE cardID = %s", (session['cardID'],))
    conn.commit()
    flash("挂失成功")
    return redirect(url_for('customer.dashboard'))

# 6. 修改密码
@customer_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT pass FROM cardInfo WHERE cardID = %s", (session['cardID'],))
        current = cursor.fetchone()

        if current and current['pass'] == old:
            cursor.execute("UPDATE cardInfo SET pass = %s WHERE cardID = %s", (new, session['cardID']))
            conn.commit()
            flash("密码修改成功")
        else:
            flash("原密码错误")

    return render_template('customer/change_password.html')

# 客户转账
@customer_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        to_card = request.form['to_card']
        amount = float(request.form['amount'])
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        # 校验转出卡信息
        cursor.execute("SELECT balance, pass FROM cardInfo WHERE cardID = %s", (session['cardID'],))
        from_card = cursor.fetchone()

        # 校验收款卡是否存在
        cursor.execute("SELECT * FROM cardInfo WHERE cardID = %s", (to_card,))
        to_card_info = cursor.fetchone()

        if not to_card_info:
            flash("收款卡号不存在")
        elif from_card['pass'] != password:
            flash("密码错误")
        elif from_card['balance'] < amount:
            flash("余额不足")
        elif session['cardID'] == to_card:
            flash("不能给自己转账")
        else:
            # 扣钱
            cursor.execute("UPDATE cardInfo SET balance = balance - %s WHERE cardID = %s", (amount, session['cardID']))
            # 收钱
            cursor.execute("UPDATE cardInfo SET balance = balance + %s WHERE cardID = %s", (amount, to_card))

            # 记录交易
            cursor.execute("""
                INSERT INTO tradeinfo (tradeType, tradeMoney, cardID, remark, tradeDate)
                VALUES ('支取', %s, %s, %s, NOW())
            """, (amount, session['cardID'], f"转给卡号 {to_card}"))

            cursor.execute("""
                INSERT INTO tradeinfo (tradeType, tradeMoney, cardID, remark, tradeDate)
                VALUES ('存入', %s, %s, %s, NOW())
            """, (amount, to_card, f"来自卡号 {session['cardID']}"))

            conn.commit()
            flash("转账成功")

    return render_template('customer/transfer.html')
