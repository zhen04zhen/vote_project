#api.py
from flask import Blueprint, jsonify, request, redirect, url_for, render_template, flash
from models import db, Poll, Option
from flask_login import current_user, login_required

api_bp = Blueprint('api', __name__)

# 創建投票
@api_bp.route('/polls', methods=['POST'])
@login_required
def create_poll():
    data = request.json
    title = data.get('title')
    content = data.get('content')
    is_multiple_choice = data.get('is_multiple_choice', False)
    options = data.get('options', [])
    
    # 驗證必要資料
    if not title or not content or not options:
        return jsonify({'error': 'Title, content, and options are required'}), 400

    # 建立投票
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
    return jsonify({'message': 'Poll created successfully', 'poll_id': new_poll.id}), 201

# 刪除投票
@api_bp.route('/polls/<int:poll_id>', methods=['DELETE'])
@login_required
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    # 檢查當前使用者是否為創建者
    if poll.creator_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(poll)
    db.session.commit()
    return jsonify({'message': 'Poll deleted successfully'}), 200

# 獲取所有投票
@api_bp.route('/polls', methods=['GET'])
@login_required
def get_polls():
    polls = Poll.query.all()
    polls_data = [{
        'id': poll.id,
        'title': poll.title,
        'content': poll.content,
        'is_multiple_choice': poll.is_multiple_choice,
        'options': [{'id': option.id, 'text': option.option_text, 'votes': option.votes} for option in poll.options]
    } for poll in polls]
    return jsonify(polls_data), 200

# 編輯投票
@api_bp.route('/edit_poll/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def edit_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)

    # 檢查當前使用者是否為投票的創建者
    if poll.creator_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'POST':
        data = request.form
        poll.title = data.get('title', poll.title)
        poll.content = data.get('content', poll.content)
        poll.is_multiple_choice = data.get('is_multiple_choice', 'off') == 'on'  # 轉換為布林值

        # 清空原有選項並重新添加
        db.session.query(Option).filter_by(poll_id=poll_id).delete()
        options = request.form.getlist('options')
        for option_text in options:
            new_option = Option(option_text=option_text, poll_id=poll_id)
            db.session.add(new_option)

        db.session.commit()
        flash('投票已更新')
        return redirect(url_for('index'))

    # GET 請求，渲染編輯表單
    return render_template('edit_poll.html', poll=poll)


# 獲取特定投票詳細資料
@api_bp.route('/polls/<int:poll_id>', methods=['GET'])
@login_required
def get_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    return jsonify({
        'id': poll.id,
        'title': poll.title,
        'content': poll.content,
        'is_multiple_choice': poll.is_multiple_choice,
        'options': [{'id': opt.id, 'text': opt.option_text, 'votes': opt.votes} for opt in poll.options]
    }), 200
