from flask import Blueprint, render_template, redirect, url_for, session, flash, request, send_file
from db import get_db
import csv
import io
admin_bp = Blueprint('admin', __name__)

# 管理员主页（仪表盘）
@admin_bp.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', username=session.get('username'))
#11111---------------------------------------------------------------------客户管理**********
# 客户管理：列出所有客户
@admin_bp.route('/customers')
def list_customers():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM userInfo")
    customers = cursor.fetchall()
    return render_template('admin/customers.html', customers=customers)
# 添加客户
@admin_bp.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        name = request.form['name']
        pid = request.form['pid']
        phone = request.form['phone']
        address = request.form['address']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO userInfo (customerName, PID, telephone, address) VALUES (%s, %s, %s, %s)",
                       (name, pid, phone, address))
        conn.commit()
        flash("客户添加成功")
        return redirect(url_for('admin.list_customers'))
    return render_template('admin/add_customer.html')
# 删除客户
@admin_bp.route('/customers/delete/<int:customerID>')
def delete_customer(customerID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM userInfo WHERE customerID = %s", (customerID,))
    conn.commit()
    flash("客户已删除")
    return redirect(url_for('admin.list_customers'))
# 修改客户
@admin_bp.route('/customers/edit/<int:customerID>', methods=['GET', 'POST'])
def edit_customer(customerID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        pid = request.form['pid']
        phone = request.form['phone']
        address = request.form['address']
        cursor.execute("""
            UPDATE userInfo
            SET customerName=%s, PID=%s, telephone=%s, address=%s
            WHERE customerID=%s
        """, (name, pid, phone, address, customerID))
        conn.commit()
        flash("客户信息已更新")
        return redirect(url_for('admin.list_customers'))
    else:
        cursor.execute("SELECT * FROM userInfo WHERE customerID = %s", (customerID,))
        customer = cursor.fetchone()
        return render_template('admin/edit_customer.html', customer=customer)
# 客户模糊查询
@admin_bp.route('/customers/search', methods=['GET'])
def search_customers():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    keyword = request.args.get('q', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    if keyword:
        cursor.execute("""
            SELECT * FROM userInfo 
            WHERE customerName LIKE %s OR PID LIKE %s
        """, (f"%{keyword}%", f"%{keyword}%"))
    else:
        # 默认显示所有
        cursor.execute("SELECT * FROM userInfo")

    results = cursor.fetchall()
    return render_template('admin/customers.html', customers=results, keyword=keyword)

#22222---------------------------------------------------------------------银行卡管理**********
# 银行卡管理：列出所有银行卡
@admin_bp.route('/cards')
def list_cards():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    keyword = request.args.get('q', '')
    conn = get_db()
    cursor = conn.cursor()

    if keyword:
        sql = """
        SELECT c.*, u.customerName
        FROM cardInfo c
        JOIN userInfo u ON c.customerID = u.customerID
        WHERE c.cardID LIKE %s OR u.customerName LIKE %s
        """
        cursor.execute(sql, ('%' + keyword + '%', '%' + keyword + '%'))
    else:
        sql = """
        SELECT c.*, u.customerName
        FROM cardInfo c
        JOIN userInfo u ON c.customerID = u.customerID
        """
        cursor.execute(sql)

    cards = cursor.fetchall()
    return render_template('admin/cards.html', cards=cards, keyword=keyword)

# 添加银行卡（手动添加）
@admin_bp.route('/cards/add', methods=['GET', 'POST'])
def add_card():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        cardID = request.form['cardID']
        customerID = request.form['customerID']
        savingID = request.form['savingID']
        openMoney = float(request.form['openMoney'])
        password = request.form['password']

        cursor.execute("""
            INSERT INTO cardInfo (cardID, curID, openDate, openMoney, balance, pass, IsReportLoss, customerID, savingID)
            VALUES (%s, 'RMB', NOW(), %s, %s, %s, FALSE, %s, %s)
        """, (cardID, openMoney, openMoney, password, customerID, savingID))

        conn.commit()
        flash("银行卡添加成功")
        return redirect(url_for('admin.list_cards'))

    cursor.execute("SELECT customerID, customerName FROM userInfo")
    customers = cursor.fetchall()

    cursor.execute("SELECT savingID, savingName FROM deposit")
    saving_types = cursor.fetchall()

    return render_template('admin/card_add.html', customers=customers, saving_types=saving_types)

# 修改银行卡信息
@admin_bp.route('/cards/edit/<cardID>', methods=['GET', 'POST'])
def edit_card(cardID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        balance = float(request.form['balance'])
        password = request.form['password']
        report_loss = request.form.get('IsReportLoss') == 'on'

        cursor.execute("""
            UPDATE cardInfo
            SET balance=%s, pass=%s, IsReportLoss=%s
            WHERE cardID=%s
        """, (balance, password, report_loss, cardID))
        conn.commit()
        flash("银行卡信息更新成功")
        return redirect(url_for('admin.list_cards'))

    cursor.execute("""
        SELECT * FROM cardInfo WHERE cardID = %s
    """, (cardID,))
    card = cursor.fetchone()
    return render_template('admin/card_edit.html', card=card)

# 删除银行卡
@admin_bp.route('/cards/delete/<cardID>', methods=['POST'])
def delete_card(cardID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cardInfo WHERE cardID=%s", (cardID,))
    conn.commit()
    flash("银行卡删除成功")
    return redirect(url_for('admin.list_cards'))


#33333---------------------------------------------------------------------存款业务管理**********
@admin_bp.route('/savings')
def list_savings():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposit")
    savings = cursor.fetchall()

    return render_template('admin/savings.html', savings=savings)
#添加存款业务
@admin_bp.route('/savings/add', methods=['GET', 'POST'])
def add_saving():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        savingName = request.form['savingName']
        descrip = request.form['descrip']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deposit (savingName, descrip)
            VALUES (%s, %s)
        """, (savingName, descrip))
        conn.commit()
        flash("新增存款业务成功")
        return redirect(url_for('admin.list_savings'))

    return render_template('admin/saving_add.html')
#编辑指定存款业务
@admin_bp.route('/savings/edit/<int:savingID>', methods=['GET', 'POST'])
def edit_saving(savingID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        savingName = request.form['savingName']
        descrip = request.form['descrip']

        cursor.execute("""
            UPDATE deposit
            SET savingName = %s, descrip = %s
            WHERE savingID = %s
        """, (savingName, descrip, savingID))
        conn.commit()
        flash("更新成功")
        return redirect(url_for('admin.list_savings'))

    cursor.execute("SELECT * FROM deposit WHERE savingID = %s", (savingID,))
    saving = cursor.fetchone()
    return render_template('admin/saving_edit.html', saving=saving)
#删除指定存款业务
@admin_bp.route('/savings/delete/<int:savingID>', methods=['POST'])
def delete_saving(savingID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deposit WHERE savingID = %s", (savingID,))
    conn.commit()
    flash("删除成功")
    return redirect(url_for('admin.list_savings'))
#导出csv表
@admin_bp.route('/savings/export')
def export_savings():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT savingID, savingName, descrip FROM deposit")
    rows = cursor.fetchall()

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['业务编号', '业务名称', '描述'])  # 表头
    for row in rows:
        writer.writerow([row.savingID, row.savingName, row.descrip])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv',
                     download_name='存款业务报表.csv',
                     as_attachment=True)




#44444---------------------------------------------------------------------交易管理**********


# 1. 查询并列出所有交易信息
@admin_bp.route('/trades')
def list_trades():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    keyword = request.args.get('q', '').strip()  # 获取搜索关键字

    conn = get_db()
    cursor = conn.cursor()

    if keyword:
        like_keyword = f"%{keyword}%"
        cursor.execute("""
            SELECT t.*, u.customerName
            FROM tradeInfo t
            LEFT JOIN cardInfo c ON t.cardID = c.cardID
            LEFT JOIN userInfo u ON c.customerID = u.customerID
            WHERE t.cardID LIKE %s OR t.tradeType LIKE %s OR t.remark LIKE %s
            ORDER BY t.tradeDate DESC
        """, (like_keyword, like_keyword, like_keyword))
    else:
        cursor.execute("""
            SELECT t.*, u.customerName
            FROM tradeInfo t
            LEFT JOIN cardInfo c ON t.cardID = c.cardID
            LEFT JOIN userInfo u ON c.customerID = u.customerID
            ORDER BY t.tradeDate DESC
        """)

    trades = cursor.fetchall()
    return render_template('admin/trades.html', trades=trades, keyword=keyword)


# 2. 删除指定交易数据
@admin_bp.route('/trades/delete/<int:tradeID>', methods=['POST'])
def delete_trade(tradeID):
    if 'admin' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tradeInfo WHERE tradeID = %s", (tradeID,))
    conn.commit()
    flash("交易记录删除成功")
    return redirect(url_for('admin.list_trades'))

# 3. 导出交易数据到 CSV 报表
@admin_bp.route('/trades/export')
def export_trades():
    if 'admin' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.tradeID, t.tradeDate, t.tradeType, t.tradeMoney, t.cardID, u.customerName, t.remark
        FROM tradeInfo t
        LEFT JOIN cardInfo c ON t.cardID = c.cardID
        LEFT JOIN userInfo u ON c.customerID = u.customerID
        ORDER BY t.tradeDate DESC
    """)
    trades = cursor.fetchall()

    # 创建CSV内存文件
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['交易ID', '交易时间', '交易类型', '交易金额', '卡号', '客户姓名', '备注'])
    for row in trades:
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='trade_report.csv'
    )






# 注销登录
@admin_bp.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('username', None)
    flash("已退出登录")
    return redirect(url_for('auth.login'))
