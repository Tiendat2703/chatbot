from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from perfect import main
import os

from bson import ObjectId
import pymongo
from datetime import datetime

import numpy as np
import pandas as pd
import google.generativeai as genai
import time
import json

import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

from send_otp import send_otp  # Nhớ import hàm send_otp
from check_email import check_email_exists 
from datetime import datetime, timedelta

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

mongo_client = pymongo.MongoClient('mongodb+srv://admin:adminmirage@unix.xrw4tsm.mongodb.net')

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home page
@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

#log in 
@app.route('/login', methods=['GET', 'POST'])
def login():
    email_prefill = session.pop('temp_email', '')
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Email is not registered!', 'danger')  # 🛠 Thông báo lỗi email chưa đăng ký
            # 👇 Giữ lại email đã nhập
            return render_template('login.html', email=email)

        if not bcrypt.check_password_hash(user.password, password):
            flash('Incorrect password!', 'danger')  # 🛠 Thông báo lỗi password sai
            # 👇 Giữ lại email đã nhập
            return render_template('login.html', email=email)

        # Nếu đúng cả email và password
        login_user(user)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('home'))

    # Trường hợp GET ban đầu → dùng email_prefill nếu có
    return render_template('login.html', email=email_prefill)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check trùng email
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Try another one.', 'warning')
            return redirect(url_for('register'))
        
        # Check trùng username
        if User.query.filter_by(username=username).first():
            flash('username already exists. Try another one.', 'warning')
            return redirect(url_for('register'))
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Trước khi gửi OTP
        if not check_email_exists(email):
            flash('Email is invalid or does not exist.', 'danger')
            return redirect(url_for('register'))
        
        # Send OTP
        # Send OTP
        from send_otp import send_otp
        otp_code = send_otp(email)

        if otp_code is None:
            flash('Failed to send OTP. Please check your email address.', 'danger')
            return redirect(url_for('register'))
        session['email'] = email
        # Nếu gửi thành công thì lưu tạm
        session['temp_user'] = {
            'username': username,
            'email': email,
            'password': hashed_password
        }
        session['otp'] = otp_code

        flash('OTP has been sent to your email. Please check and enter it.', 'info')
        return redirect(url_for('verify_otp'))


    return render_template('register.html'
                           )
#verify otp
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        stored_otp = session.get('otp')
        temp_user = session.get('temp_user')

        # 🧪 Debug log (in ra terminal)
        print(">> User entered OTP:", user_otp)
        print(">> OTP stored in session:", stored_otp)
        print(">> Temp user data:", temp_user)

        if user_otp == stored_otp:
            if not temp_user:
                flash("Session expired. Please register again.", "warning")
                return redirect(url_for('register'))

            # ✅ Tạo user mới
            new_user = User(
                username=temp_user['username'],
                email=temp_user['email'],
                password=temp_user['password']
            )
            db.session.add(new_user)
            db.session.commit()
            session['temp_email'] = temp_user['email']
            flash("Account created successfully! You can now log in!", "success")

            # ✅ Xóa dữ liệu session tạm
            session.pop('temp_user', None)
            session.pop('otp', None)
            session.pop('email', None)

            return redirect(url_for('login'))

        else:
            flash("❌ The OTP you entered is incorrect. Please try again.", "danger")
            return redirect(url_for('verify_otp', purpose="register"))

    return render_template('verify_otp.html')
#resend otp

@app.route('/resend_otp', methods=['GET'])
def resend_otp():
    now = datetime.utcnow()
    last_sent = session.get('last_otp_time')

    if last_sent:
        last_time = datetime.strptime(last_sent, "%Y-%m-%d %H:%M:%S")
        if now - last_time < timedelta(seconds=60):
            remaining = 60 - int((now - last_time).total_seconds())
            flash(f'Please wait {remaining}s before requesting another OTP.', 'warning')
            return redirect(url_for('verify_otp'))

    email = session.get('email')
    if email:
        otp = send_otp(email)
        if otp:
            session['otp'] = otp
            session['last_otp_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
            flash('A new OTP has been sent to your email.', 'success')
        else:
            flash('Failed to resend OTP. Please try again.', 'danger')
    else:
        flash('Session expired. Please register again.', 'danger')
    return redirect(url_for('verify_otp'))

#forget_password
@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Email is not registered!', 'danger')
            return redirect(url_for('forget_password'))

        # ✅ Gửi OTP về email
        from send_otp import send_otp
        otp_code = send_otp(email)

        if not otp_code:
            flash('Failed to send OTP.', 'danger')
            return redirect(url_for('forget_password'))

        session['reset_email'] = email
        session['reset_otp'] = otp_code
        flash('OTP sent! Please check your email.', 'info')
        return redirect(url_for('verify_reset_otp'))

    return render_template('forget_password.html')

#verify_reset_otp
@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        otp = request.form['otp']
        if otp == session.get('reset_otp'):
            flash('OTP verified! Now reset your password.', 'success')
            
            return redirect(url_for('reset_password'))
        else:
            flash('Incorrect OTP!', 'danger')
    return render_template('verify_otp.html', purpose="reset")

#reset_passwpassw
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_pw = request.form['password']
        email = session.get('reset_email')
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
            db.session.commit()
            flash('Password has been reset. Please log in.', 'success')
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session['temp_email'] = email
            return redirect(url_for('login'))
    return render_template('reset_password.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Profile view
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Edit Profile
@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    new_username = request.form.get('username')
    if new_username:
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Username already taken. Try another one.', 'warning')
            return redirect(url_for('profile'))
        current_user.username = new_username
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

# Delete Account
@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash('Your account has been deleted.', 'warning')
    return redirect(url_for('register'))


# Chart chatbot
# Load data chart
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, 'transform_filled_chitieu.xlsx')
df1 = pd.read_excel(file_path)

# Clean data cơ bản
df1.dropna(subset=['Điểm Chuẩn', 'Phương Thức Xét Tuyển'], inplace=True)

for col in ['Tên trường', 'Tên Ngành', 'Phương Thức Xét Tuyển']:
    df1[col] = df1[col].str.strip()

df1['Năm'] = df1['Năm'].astype(int)
df1['Điểm Chuẩn'] = pd.to_numeric(df1['Điểm Chuẩn'], errors='coerce')

# Filter theo phương thức xét tuyển "THPT quốc gia"
df_thpt = df1[df1['Phương Thức Xét Tuyển'] == 'THPT Quốc gia']

# Route Trang Chart
@app.route('/chart')
@login_required
def chart():
    return render_template('chart.html', user=current_user)

# API Chart 1
@app.route('/api/chart1')
@login_required
def api_chart1():
    data = df_thpt.groupby(['Tên trường', 'Tên Ngành', 'Năm'])['Điểm Chuẩn'].mean().reset_index()
    return json.dumps(data.to_dict(orient='records'), ensure_ascii=False)

# API Chart 2
@app.route('/api/chart2')
@login_required
def api_chart2():
    data = df_thpt.groupby(['Năm', 'Tên Ngành', 'Tên trường'])['Điểm Chuẩn'].mean().reset_index()
    return json.dumps(data.to_dict(orient='records'), ensure_ascii=False)

# API Chart 3
@app.route('/api/chart3')
@login_required
def api_chart3():
    grouped = df_thpt.groupby('Năm').agg({
        'Điểm Chuẩn': 'mean',
        'Tên Ngành': 'nunique'
    }).reset_index()
    grouped.rename(columns={'Tên Ngành': 'Số lượng ngành'}, inplace=True)
    return json.dumps(grouped.to_dict(orient='records'), ensure_ascii=False)

# API Chart 4
@app.route('/api/chart4')
@login_required
def api_chart4():
    data = df_thpt.groupby(['Tên trường', 'Năm'])['Điểm Chuẩn'].mean().reset_index()
    return json.dumps(data.to_dict(orient='records'), ensure_ascii=False)

# Overview
# Load and clean data
# Load data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, 'transform_filled_chitieu.xlsx')
df = pd.read_excel(file_path)
df.dropna(subset=['Điểm Chuẩn', 'Phương Thức Xét Tuyển'], inplace=True)
df['Tên trường'] = df['Tên trường'].str.strip()
df['Tên Ngành'] = df['Tên Ngành'].str.strip()
df['Phương Thức Xét Tuyển'] = df['Phương Thức Xét Tuyển'].str.strip()
df['Năm'] = df['Năm'].astype(int)
df['Điểm Chuẩn'] = pd.to_numeric(df['Điểm Chuẩn'], errors='coerce')

@app.route('/overview')
def overview():
    return render_template('overview.html',
        years=sorted(df['Năm'].unique()),
        schools=sorted(df['Tên trường'].unique()),
        methods=sorted(df['Phương Thức Xét Tuyển'].unique()))

@app.route('/majors-by-schools', methods=['POST'])
def majors_by_schools():
    schools = request.json.get('schools', [])
    filtered = df.copy() if '__all__' in schools else df[df['Tên trường'].isin(schools)]
    majors = sorted(filtered['Tên Ngành'].unique())
    return jsonify({"majors": majors})

@app.route('/filter', methods=['POST'])
def filter_data():
    filters = request.json
    filtered_df = df.copy()

    if filters['year'] and filters['year'] != ['__all__']:
        filtered_df = filtered_df[filtered_df['Năm'].isin([int(y) for y in filters['year']])]
    if filters['school'] and filters['school'] != ['__all__']:
        filtered_df = filtered_df[filtered_df['Tên trường'].isin(filters['school'])]
    if filters['major'] and filters['major'] != ['__all__']:
        filtered_df = filtered_df[filtered_df['Tên Ngành'].isin(filters['major'])]


    if filters['method']:
        method_list = df['Phương Thức Xét Tuyển'].unique().tolist()
        if '__all__' not in filters['method'] and set(filters['method']) != set(method_list):
            filtered_df = filtered_df[filtered_df['Phương Thức Xét Tuyển'].isin(filters['method'])]


    if filtered_df.empty:
        return jsonify({'plot_html': '<p class="text-center text-danger">Không có dữ liệu phù hợp.</p>',
                        'metrics': {'total_records': 0, 'avg_score': 0, 'num_schools': 0, 'num_majors': 0}})

    chart_df = filtered_df.copy()

    # Nếu user chọn TẤT CẢ ngành → chỉ lấy top 10 ngành có ĐIỂM TRUNG BÌNH cao nhất
    if filters['major'] and '__all__' in filters['major']:
        top10_nganh = (
            chart_df
            .groupby('Tên Ngành')['Điểm Chuẩn']
            .mean()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        chart_df = chart_df[chart_df['Tên Ngành'].isin(top10_nganh)]

    avg_by_year = chart_df.groupby(['Năm', 'Tên trường'], as_index=False)['Điểm Chuẩn'].mean()

    chart_df["Năm"] = chart_df["Năm"].astype(str)
    
    avg_by_year["Năm"] = avg_by_year["Năm"].astype(str)

    # Rút gọn tên ngành
    # Rút gọn tên ngành
    # 🧠 Tạo cột hiển thị trên trục Ox: Ngành (Phương thức)
    chart_df = filtered_df.copy()

    # 🔥 CHỈ RIÊNG CHO CHART 1
    chart1_df = filtered_df.copy()

    # Lọc năm mới nhất
    # Nếu user không chọn năm ⇒ mặc định chọn năm mới nhất
    if not filters['year'] or '__all__' in filters['year']:
        max_year = chart1_df['Năm'].max()
        chart1_df = chart1_df[chart1_df['Năm'] == max_year]
    else:
        # Nếu user chọn nhiều năm → hiển thị đủ
        selected_years = [int(y) for y in filters['year']]
        chart1_df = chart1_df[chart1_df['Năm'].isin(selected_years)]


    # Nếu nhiều ngành quá thì chỉ lấy top 20 ngành điểm cao nhất
    top_majors = (
        chart1_df.groupby('Tên Ngành')['Điểm Chuẩn']
        .mean()
        .sort_values(ascending=False)
        .head(20)
        .index.tolist()
    )
    chart1_df = chart1_df[chart1_df['Tên Ngành'].isin(top_majors)]

    # 🧠 Tạo cột hiển thị
    chart1_df['Nhóm Ngành'] = chart1_df['Tên Ngành']
    chart1_df['Label_Tooltip'] = chart1_df['Nhóm Ngành']
    chart1_df['Năm'] = chart1_df['Năm'].astype(str)  # 🧠 Thêm dòng này

    # 📊 Vẽ Chart1
    filtered_methods = chart1_df['Phương Thức Xét Tuyển'].dropna().unique()
    is_multi_method = len(filtered_methods) > 1

    if is_multi_method and chart1_df['Phương Thức Xét Tuyển'].nunique() > 1:
        fig1 = px.bar(
        chart1_df,
        x="Điểm Chuẩn",
        y="Nhóm Ngành",
        color="Năm",
        barmode="group",
        facet_row="Phương Thức Xét Tuyển",
        title="📊 So sánh Điểm Chuẩn Theo Nhiều Phương Thức (Năm mới nhất)"
    )
        fig1.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig1.for_each_yaxis(lambda y: y.update(title='') if y.anchor != 'x' else None)
    else:
        fig1 = px.bar(
        chart1_df,
        x="Điểm Chuẩn",
        y="Nhóm Ngành",
        color="Năm",
        barmode="group",
        title="📊 So sánh Điểm Chuẩn Theo Ngành (Năm mới nhất)"
    )

        for trace in fig1.data:
            trace.customdata = np.stack([
            chart1_df['Tên trường'],
            chart1_df['Năm'],
            chart1_df['Phương Thức Xét Tuyển'],
            chart1_df['Điểm Chuẩn']
        ], axis=-1)

        trace.hovertemplate = (
            "<b>Trường:</b> %{customdata[0]}<br>" +
            "<b>Năm:</b> %{customdata[1]}<br>" +
            "<b>Phương thức:</b> %{customdata[2]}<br>" +
            "<b>Điểm:</b> %{customdata[3]:.2f}<extra></extra>"
        )

    fig1.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        hovermode="closest",
        bargap=0.19,
        bargroupgap=0.09,
        height=800,
        legend=dict(
            orientation="v",
            yanchor="middle", y=0.5,
            xanchor="left", x=1.02
        ),
        margin=dict(l=60, r=60, t=60, b=120),
        xaxis=dict(title="Điểm chuẩn", tickangle=-30),
        yaxis=dict(title="", gridcolor="#e0e0e0", zeroline=False)
    )
  
    fig2 = px.line(
    avg_by_year,
    x="Năm",
    y="Điểm Chuẩn",
    color="Tên trường",
    markers=True,
    title="📈 Xu Hướng Điểm Chuẩn Trung Bình Theo Trường"
)
    
    method_stats = chart_df.groupby('Phương Thức Xét Tuyển').agg(
    Điểm_TB=('Điểm Chuẩn', 'mean'),
    Số_ngành=('Tên Ngành', 'nunique')
    ).reset_index()
    method_stats["Điểm_TB"] = method_stats["Điểm_TB"].round(2)

    fig3 = px.bar(
    method_stats,
    x="Phương Thức Xét Tuyển",
    y="Điểm_TB",
    text="Điểm_TB",
    color="Phương Thức Xét Tuyển",
    title="📊 Điểm TB & Số Ngành Theo Phương Thức"
)
    fig3.update_traces(
    textposition="outside",
    hovertemplate="<b>Phương thức xét tuyển:</b> %{x}<br><b>Điểm TB:</b> %{y} điểm<extra></extra>",
)

    # Lọc các trường có Thành phố là Đà Nẵng
# Treemap logic: mặc định lọc Đà Nẵng, nếu user có chọn thì ưu tiên filter user

    if not filters['school'] or '__all__' in filters['school']:
        # Lấy trường Đà Nẵng và không có trong danh sách cấm
        default_schools = df[
            df['Thành phố'].str.contains("Đà Nẵng", case=False, na=False) &
            ~df['Tên trường'].str.contains("KHOA CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG|TRƯỜNG Y DƯỢC|KHOA GIÁO DỤC THỂ CHẤT|KHOA Y DƯỢC|PHÂN HIỆU ĐẠI HỌC ĐÀ NẴNG TẠI KON TUM", case=False, na=False)
        ]['Tên trường'].unique()

        treemap_df = chart_df[chart_df['Tên trường'].isin(default_schools)]
    else:
        # Nếu người dùng đã chọn trường ⇒ dùng nguyên dữ liệu chart_df, KHÔNG loại trừ gì cả
        treemap_df = chart_df.copy()

    # (1) Lấy năm mới nhất
    max_year = treemap_df['Năm'].max()
    latest_df = treemap_df[treemap_df['Năm'] == max_year]

    # (2) KHÔNG cần groupby trung bình
    # Giữ nguyên từng dòng Trường - Ngành - Phương thức với điểm chuẩn năm mới nhất

    # (3) Giới hạn chỉ lấy 5 trường có ngành cao nhất (để tránh tràn text)
    top_truong = (
        latest_df.groupby('Tên trường')['Điểm Chuẩn']
        .max()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    filtered_latest_df = latest_df[latest_df['Tên trường'].isin(top_truong)]

    # (3b) Lấy top 5 ngành của mỗi trong 5 trường
    top5_by_school = filtered_latest_df.groupby('Tên trường', group_keys=False).apply(
        lambda g: g.sort_values(by='Điểm Chuẩn', ascending=False).head(5)
    ).reset_index(drop=True)

    # (4) Rút gọn tên ngành: 2 từ/dòng, tối đa 5 từ
    def wrap_text(text, words_per_line=2, max_words=5):
        words = text.split()
        add_ellipsis = False
        if len(words) > max_words:
            words = words[:max_words]
            add_ellipsis = True
        wrapped_text = ''
        for i in range(0, len(words), words_per_line):
            wrapped_text += ' '.join(words[i:i+words_per_line]) + '<br>'
        wrapped_text = wrapped_text.rstrip('<br>')
        if add_ellipsis:
            wrapped_text += ' ...'
        return wrapped_text

    top5_by_school['Tên Ngành Rút gọn'] = top5_by_school['Tên Ngành'].apply(lambda x: wrap_text(x))

    # (5) Treemap
    fig4 = px.treemap(
    top5_by_school,
    path=[px.Constant("Tất cả"), 'Tên trường', 'Tên Ngành Rút gọn'],
    values='Điểm Chuẩn',
    color='Điểm Chuẩn',
    color_continuous_scale='Blues',
    custom_data=['Tên trường', 'Tên Ngành', 'Điểm Chuẩn', 'Phương Thức Xét Tuyển'],
    title=f"🗂️ Treemap: Trường → Ngành Top 5 (Năm {max_year})"
)

    # (6) Cập nhật hover
    fig4.update_traces(
    hovertemplate="<b>Trường:</b> %{customdata[0]}<br>" +
                  "<b>Ngành:</b> %{customdata[1]}<br>" +
                  "<b>Điểm:</b> %{customdata[2]:.1f} điểm<br>" +
                  "<b>Phương thức:</b> %{customdata[3]}<extra></extra>",
    root_color="white",
    texttemplate="<b>%{label}</b><br><i>%{customdata[2]:.1f} điểm</i>",
    textinfo="label+value",
    insidetextfont=dict(size=10),
    marker=dict(line=dict(width=0)),
    selector=dict(type='treemap')
)


    fig4.update_layout(
        height=900,
        margin=dict(l=40, r=40, t=60, b=80),
        uniformtext=dict(minsize=8, mode='show')
    )

    for fig in [fig1, fig2, fig3, fig4]:
        fig.update_layout(
            autosize=True,
            width=None,
            height=700,
            margin=dict(l=40, r=40, t=60, b=80)
        )

    full_html = f'<div id="fig1">{fig1.to_html(full_html=False, include_plotlyjs=False)}</div>' \
            f'<div id="fig2">{fig2.to_html(full_html=False, include_plotlyjs=False)}</div>' \
            f'<div id="fig3">{fig3.to_html(full_html=False, include_plotlyjs=False)}</div>' \
           f'<div id="fig4">{fig4.to_html(full_html=False, include_plotlyjs=False, config=dict(displayModeBar=True))}</div>'

    metrics = {
        'total_records': len(filtered_df),
        'avg_score': round(filtered_df['Điểm Chuẩn'].mean(), 2),
        'num_schools': filtered_df['Tên trường'].nunique(),
        'num_majors': filtered_df['Tên Ngành'].nunique()
    }

    fig1_html = fig1.to_html(full_html=False, include_plotlyjs=False)

    # Sau khi đã có fig1, fig2, fig3, fig4
    fig1_html = fig1.to_html(full_html=False, include_plotlyjs=False)
    fig2_html = fig2.to_html(full_html=False, include_plotlyjs=False)
    fig3_html = fig3.to_html(full_html=False, include_plotlyjs=False)
    fig4_html = fig4.to_html(full_html=False, include_plotlyjs=False)

    return jsonify({
        'plot_html': {
            'fig1': fig1_html,
            'fig2': fig2_html,
            'fig3': fig3_html,
            'fig4': fig4_html
        },
        'metrics': metrics
    })
  
@app.route('/suggest', methods=['POST'])
def suggest():
    data = request.get_json()
    methods = data.get('method', [])
    min_score = float(data.get('minScore', 0))
    max_score = float(data.get('maxScore', 1000))
    years = data.get('year', [])

    filtered = df[
        (df['Điểm Chuẩn'] >= min_score) &
        (df['Điểm Chuẩn'] <= max_score)
    ]
    if methods:
        filtered = filtered[filtered['Phương Thức Xét Tuyển'].isin(methods)]
    if years:
        filtered = filtered[filtered['Năm'].isin([int(y) for y in years if str(y).isdigit()])]

    results = filtered[['Tên trường', 'Tên Ngành', 'Phương Thức Xét Tuyển', 'Điểm Chuẩn', 'Năm']].drop_duplicates()
    results = results.sort_values(by='Điểm Chuẩn')
    return jsonify([
        {
            'school': row['Tên trường'],
            'major': row['Tên Ngành'],
            'method': row['Phương Thức Xét Tuyển'],
            'score': round(row['Điểm Chuẩn'], 2),
            'year': row['Năm']
        } for _, row in results.iterrows()
    ])


# Chatbot
genai.configure(api_key="AIzaSyBwLVH64NVzGZ6ISO_jqmsQGX2iXeEyByg")
@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot():
    db_user = mongo_client[f"db_user_{current_user.id}"]

    def generate_next_session_id(db_user):
        existing_sessions = [name for name in db_user.list_collection_names() if name.startswith("session_")]
        if not existing_sessions:
            return "session_00001"
        max_number = max([int(name.replace("session_", "")) for name in existing_sessions])
        return f"session_{max_number + 1:05d}"

    def get_latest_session_id(db_user):
        existing_sessions = [name for name in db_user.list_collection_names() if name.startswith("session_")]
        if not existing_sessions:
            return None
        max_number = max([int(name.replace("session_", "")) for name in existing_sessions])
        return f"session_{max_number:05d}"

    is_new_session = False

    # 👉 Nếu chưa có session_id thì lấy session mới nhất hoặc tạo mới
    if 'session_id' not in session:
        latest_session_id = get_latest_session_id(db_user)
        if latest_session_id:
            session['session_id'] = f"session_{latest_session_id}"
        else:
            session['session_id'] = "session_00001"
            is_new_session = True

    session_collection = db_user[session['session_id']]

    if request.method == 'GET':
        # Khi load giao diện, đọc messages từ Mongo
        session_doc = session_collection.find_one({}, {"_id": 0})
        messages = session_doc.get('messages', []) if session_doc else []
        return render_template('chat.html', messages=messages)

    # Nếu POST (user gửi tin nhắn)
    user_input = request.form.get('user_input')

    # Load tin nhắn hiện tại từ Mongo
    session_doc = session_collection.find_one({}, {"_id": 0})
    messages = session_doc.get('messages', []) if session_doc else []

    # Thêm user input vào messages
    messages.append({"role": "user", "content": user_input})

    # Gọi AI trả lời
    response, question_type = main(user_input)
    messages.append({"role": "assistant", "content": response})

    if question_type == "search":
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, 'static/media/data.xlsx')
        
        fig = None
        try:
            # Đọc file Excel
            df = pd.read_excel(file_path)

            # Kiểm tra dữ liệu đầu vào đủ điều kiện vẽ
            if df.shape[0] == 0 or "Điểm Chuẩn" not in df.columns:
                chart_html = None
            else:
                unique_majors = df["Tên Ngành"].nunique()
                unique_universities = df["Tên trường"].nunique()
                unique_years = df["Năm"].nunique()


                # Trường hợp 1: Nhiều năm, nhiều trường, chỉ 1 ngành → Line chart theo năm
                if unique_years >= 2 and unique_universities >= 2:
                    fig = px.line(
                        df,
                        x="Năm",
                        y="Điểm Chuẩn",
                        color="Tên trường",
                        markers=True,
                        title=f"Biểu đồ điểm chuẩn theo năm của ngành {df['Tên Ngành'].iloc[0]}"
                    )

                # Trường hợp 2: Nhiều trường, chỉ 1 ngành → Bar chart theo trường
                elif unique_universities >= 2 and unique_majors == 1:
                    latest_year = df["Năm"].max()
                    df_latest = df[df["Năm"] == latest_year]  # Chọn năm gần nhất
                    fig = px.bar(
                        df_latest,
                        x="Điểm Chuẩn",
                        y="Tên trường",
                        orientation="h",
                        title=f"Điểm chuẩn theo trường (năm {latest_year}) cho ngành {df_latest['Tên Ngành'].iloc[0]}"
                    )

                # Trường hợp 3: Nhiều ngành → Bar chart theo ngành
                elif unique_majors >= 2:
                    latest_year = df["Năm"].max()
                    df_latest = df[df["Năm"] == latest_year]
                    fig = px.bar(
                        df_latest,
                        x="Điểm Chuẩn",
                        y="Tên Ngành",
                        orientation="h",
                        title=f"Điểm chuẩn theo ngành (năm {latest_year})"
                    )

                # ✅ Trường hợp 4: Cùng 1 trường, cùng 1 ngành → Bar chart theo Năm
                elif unique_universities == 1 and unique_majors == 1 and unique_years >= 2:
                    fig = px.bar(
                        df.sort_values("Năm"),
                        x="Điểm Chuẩn",
                        y="Năm",
                        orientation="h",
                        title=f"Điểm chuẩn theo năm của ngành {df['Tên Ngành'].iloc[0]} tại {df['Tên trường'].iloc[0]}"
                    )

                # Tạo HTML nếu có biểu đồ
                if fig:
                    chart_html = fig.to_html(
                        full_html=False,
                        include_plotlyjs='cdn',
                        config={
                            "responsive": True,
                            "displaylogo": False,
                            "toImageButtonOptions": {
                                "format": "png",
                                "filename": "chatbot_chart",
                                "height": 400,
                                "width": 600,
                                "scale": 0.7
                            }
                        }
                    )
                    messages.append({
                        "role": "assistant",
                        "content": chart_html,
                        "type": "chart"
                    })
                    
                else:
                    chart_html = None
            

        except Exception as e:
            chart_html = None
            print("Lỗi khi xử lý Excel/chart:", e)

    # Cập nhật lại Mongo
    if is_new_session:
        session_doc = {
            "created_at": datetime.utcnow(),
            "session_title": user_input.capitalize(),
            "messages": messages
        }
        session_collection.insert_one(session_doc)
    else:
        update_data = {
            "updated_at": datetime.utcnow(),
            "messages": messages
        }
        session_collection.update_one({}, {"$set": update_data}, upsert=True)
    
    if question_type == "search" and fig:
        return jsonify({
            "messages": [{"role": "assistant", "content": response},
            {"role": "assistant", "content": chart_html, "type": "chart"}]
        })
    else:
        return jsonify({
            "messages": [{"role": "assistant", "content": response}]
        })
    
@app.route("/get_sessions")
def get_sessions():
    db_user = mongo_client[f"db_user_{current_user.id}"]
    sessions = [name for name in db_user.list_collection_names() if name.startswith("session_")]
    sessions_sorted = sorted(sessions, key=lambda x: int(x.replace("session_", "")))
    return jsonify({"sessions": sessions_sorted})

@app.route("/switch_session", methods=["POST"])
def switch_session():
    session_data = request.get_json()
    session_id = session_data.get("session_id")
    session["session_id"] = session_id

    db_user = mongo_client[f"db_user_{current_user.id}"]
    collection = db_user[session_id]

    # Luôn lấy document theo sort theo created_at mới nhất
    doc = collection.find_one({}, {"_id": 0, "messages": 1}, sort=[("created_at", -1)])

    if doc and "messages" in doc:
        session["messages"] = doc["messages"]
    else:
        session["messages"] = []

    return jsonify({"status": "ok"})


def generate_next_session_id(db_user):
    existing_sessions = [name for name in db_user.list_collection_names() if name.startswith("session_")]
    max_number = 0
    for name in existing_sessions:
        try:
            number = int(name.replace("session_", ""))
            max_number = max(max_number, number)
        except ValueError:
            continue
    return f"session_{max_number + 1:05d}"

@app.route("/create_new_session", methods=["POST"])
def create_new_session():
    db_user = mongo_client[f"db_user_{current_user.id}"]
    new_id = generate_next_session_id(db_user)
    session['session_id'] = new_id
    session['messages'] = []
    return jsonify({"status": "created"})

@app.route("/preview_session")
def preview_session():
    session_id = request.args.get("session_id")
    db_user = mongo_client[f"db_user_{current_user.id}"]
    collection = db_user[session_id]
    doc = collection.find_one({}, {"_id": 0, "messages": 1})

    if doc:
        return jsonify({"messages": doc.get("messages", [])})
    else:
        return jsonify({"messages": []})
               

@app.route('/mbti-intro')
def mbti_intro():
    with open(os.path.join(BASE_DIR, 'data', 'mbti_open.json'), 'r', encoding='utf-8') as f:
        mbti_open_profiles = json.load(f)
    return render_template('mbti_home.html', mbti_profiles=mbti_open_profiles)


@app.route('/mbti', methods=['GET', 'POST'])
def mbti_test():
    with open(os.path.join(BASE_DIR, 'data', 'mbti_50_questions.json'), 'r', encoding='utf-8') as f:
        all_questions = json.load(f)

    questions_per_page = 1
    page = int(request.args.get('page', 1))
    total_pages = len(all_questions)

    if request.method == 'POST':
        answer = request.form.to_dict()
        session.setdefault('mbti_answers', {}).update(answer)
        session.modified = True

        if page < total_pages:
            return redirect(url_for('mbti_test', page=page + 1))
        else:
            final_answers = session.pop('mbti_answers', {})
            result = calculate_mbti(final_answers, all_questions)

            with open(os.path.join(BASE_DIR, 'data', 'mbti_profiles.json'), 'r', encoding='utf-8') as f:
                mbti_profiles = json.load(f)

            with open(os.path.join(BASE_DIR, 'data', 'mbti_majors.json'), 'r', encoding='utf-8') as f:
                mbti_majors = json.load(f)

            profile = mbti_profiles.get(result, {})
            majors = mbti_majors.get(result, [])

            return render_template('mbti_result.html', result=result, profile=profile, majors=majors)

    start = (page - 1) * questions_per_page
    questions = all_questions[start:start + questions_per_page]
    return render_template('mbti_test.html', questions=questions, page=page, total_pages=total_pages)


def calculate_mbti(answers, questions):
    traits = {'E': 0, 'I': 0, 'S': 0, 'N': 0, 'T': 0, 'F': 0, 'J': 0, 'P': 0}

    for q in questions:
        qid = q['id']
        choice = answers.get(qid)
        if choice == 'a':
            traits[q['a_trait']] += 1
        elif choice == 'b':
            traits[q['b_trait']] += 1

    mbti = ''.join([
        'E' if traits['E'] >= traits['I'] else 'I',
        'S' if traits['S'] >= traits['N'] else 'N',
        'T' if traits['T'] >= traits['F'] else 'F',
        'J' if traits['J'] >= traits['P'] else 'P'
    ])
    return mbti

def suggest_majors(mbti_type):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(BASE_DIR, 'data', 'mbti_majors.json'), 'r', encoding='utf-8') as f:
        all_majors = json.load(f)
    return all_majors.get(mbti_type, [])

# Run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
