#app.py
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Poll, Option, VoteRecord
from api import api_bp  # 確保 api.py 定義了 api_bp
import os

app = Flask(__name__, instance_relative_config=True)

# 設置應用的 Secret Key，用於會話加密。這裡可以從 config.py 加載或直接設置
app.config['SECRET_KEY'] = 'your_secret_key_here'  # 請設置為安全的隨機字符串

# 設置資料庫配置
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, "polls.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 SQLAlchemy 和 Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 註冊 API 藍圖
app.register_blueprint(api_bp, url_prefix='/api')

# 用於加載已登入的用戶
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 主頁路由，顯示所有投票
@app.route('/')
@login_required
def index():
    polls = Poll.query.all()
    return render_template('index.html', polls=polls)

# 投票頁面路由
@app.route('/vote/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def vote(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    existing_votes = VoteRecord.query.filter_by(user_id=current_user.id, poll_id=poll_id).all()
    
    # 提取用戶已投票的選項 ID
    voted_option_ids = [vote.option_id for vote in existing_votes]

    if request.method == 'POST':
        if existing_votes:
            # 清除舊的投票記錄
            for record in existing_votes:
                record.option.votes -= 1
                db.session.delete(record)

        if poll.is_multiple_choice:
            # 處理多選題的投票
            option_ids = request.form.getlist('options')
            for option_id in option_ids:
                option = Option.query.get(option_id)
                if option:
                    option.votes += 1
                    new_vote = VoteRecord(user_id=current_user.id, poll_id=poll_id, option_id=option_id)
                    db.session.add(new_vote)
        else:
            # 處理單選題的投票
            option_id = request.form.get('option')
            option = Option.query.get(option_id)
            if option:
                option.votes += 1
                new_vote = VoteRecord(user_id=current_user.id, poll_id=poll_id, option_id=option_id)
                db.session.add(new_vote)

        db.session.commit()
        return redirect(url_for('result', poll_id=poll_id))
    
    return render_template('vote.html', poll=poll, voted_option_ids=voted_option_ids)

# 新增投票問題路由
@app.route('/add_poll', methods=['GET', 'POST'])
@login_required
def add_poll():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        options = request.form.getlist('options')
        is_multiple_choice = request.form.get('is_multiple_choice', 'off') == 'on'
        
        # 創建新的投票，並將當前使用者 ID 設為 creator_id
        new_poll = Poll(
            title=title, 
            content=content, 
            is_multiple_choice=is_multiple_choice, 
            creator_id=current_user.id
        )
        db.session.add(new_poll)
        db.session.flush()  # 獲取 new_poll 的 id
        
        # 添加選項
        for option_text in options:
            option = Option(option_text=option_text, poll_id=new_poll.id)
            db.session.add(option)
        
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('add_poll.html')

# 詳細頁面 (投票結果)
@app.route('/result/<int:poll_id>')
@login_required
def result(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    return render_template('result.html', poll=poll)

# 註冊路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 檢查使用者名稱是否已存在
        if User.query.filter_by(username=username).first():
            flash('使用者名稱已存在，請選擇另一個名稱')
            return redirect(url_for('register'))
        
        # 創建新使用者
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功，請登入')
        return redirect(url_for('login'))
    return render_template('register.html')

# 登入路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 查找用戶
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            #flash('登入成功')  # 僅在用戶成功登入時顯示提示
            return redirect(url_for('index'))
        else:
            flash('使用者名稱或密碼錯誤')  # 顯示錯誤訊息
            return redirect(url_for('login'))
    return render_template('login.html')

# 登出路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)  # 清除所有 flash 訊息
    flash('您已登出')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)