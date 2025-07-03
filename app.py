from flask import Flask
from config import SECRET_KEY
from routes.auth import auth_bp
# from routes.admin import admin_bp
# from routes.customer import customer_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 注册蓝图
app.register_blueprint(auth_bp)

from routes.admin import admin_bp
app.register_blueprint(admin_bp)

# 如果还有客户模块
from routes.customer import customer_bp
app.register_blueprint(customer_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
