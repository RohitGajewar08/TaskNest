from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date, timedelta
import joblib
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# === Load ML Models ===
ML_DIR = os.path.join(os.path.dirname(__file__), 'ml')
vectorizer_prio = joblib.load(os.path.join(ML_DIR, 'vectorizer_priority.pkl'))
model_priority = joblib.load(os.path.join(ML_DIR, 'model_priority.pkl'))
model_deadline = joblib.load(os.path.join(ML_DIR, 'model_deadline.pkl'))
model_overdue = joblib.load(os.path.join(ML_DIR, 'model_overdue.pkl'))
model_category = joblib.load(os.path.join(ML_DIR, 'model_category.pkl'))
label_encoder_cat = joblib.load(os.path.join(ML_DIR, 'label_encoder_cat.pkl'))

# === Database Models ===
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    tasks = db.relationship('Task', back_populates='category', lazy=True, cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(10), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', back_populates='tasks')

# === ML Predictions ===
def ml_predict(text):
    X = vectorizer_prio.transform([text])

    priority = model_priority.predict(X)[0]
    deadline_days = int(round(model_deadline.predict(X)[0]))
    category_encoded = model_category.predict(X)[0]
    category = label_encoder_cat.inverse_transform([category_encoded])[0]
    overdue_prob = model_overdue.predict_proba(X)[0][1]

    predicted_due_date = date.today() + timedelta(days=deadline_days)
    return priority, predicted_due_date, category, overdue_prob

    if ml_predicted:
    task.priority += " (Predicted)"

# === Routes ===
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task_text = request.form.get('task', '').strip()
        category_name = request.form.get('category', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', '').strip()

        if not task_text:
            flash("⚠️ Task cannot be empty!", "error")
            return redirect(url_for('index'))

        # If fields are missing, use ML
        predicted_priority, predicted_due, predicted_category, overdue_prob = ml_predict(task_text)

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("⚠️ Invalid due date format.", "error")
                return redirect(url_for('index'))
        else:
            due_date = predicted_due

        if not priority or priority not in ['Low', 'Medium', 'High']:
            priority = predicted_priority

        if not category_name:
            category_name = predicted_category

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.commit()

        new_task = Task(task=task_text, due_date=due_date, priority=priority, category=category)
        db.session.add(new_task)
        db.session.commit()

        msg = f"✅ Task added with ML: Priority={priority}, Due={due_date}, Category={category.name}"
        if overdue_prob > 0.7:
            msg += f" ⚠️ May be overdue! ({overdue_prob:.2%})"
        flash(msg, "success")

        return redirect(url_for('index'))

    status = request.args.get('status')
    priority = request.args.get('priority')
    category_id = request.args.get('category_id')
    sort = request.args.get('sort')

    tasks_query = Task.query

    if status == 'completed':
        tasks_query = tasks_query.filter_by(completed=True)
    elif status == 'pending':
        tasks_query = tasks_query.filter_by(completed=False)

    if priority:
        tasks_query = tasks_query.filter_by(priority=priority)

    if category_id:
        tasks_query = tasks_query.filter_by(category_id=category_id)

    if sort == 'due_date':
        tasks_query = tasks_query.order_by(Task.due_date.asc().nullslast())
    elif sort == 'priority':
        tasks_query = tasks_query.order_by(Task.priority.asc())
    else:
        tasks_query = tasks_query.order_by(Task.created_at.desc())

    tasks = tasks_query.all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('index.html', tasks=tasks, categories=categories, current_date=date.today())

@app.route('/toggle/<int:task_id>')
def toggle(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = not task.completed
    db.session.commit()
    flash(f"🔁 Task marked as {'complete' if task.completed else 'incomplete'}.", "info")
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>')
def delete(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("🗑️ Task deleted.", "info")
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit(task_id):
    task = Task.query.get_or_404(task_id)
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        task_text = request.form.get('task', '').strip()
        category_name = request.form.get('category', '').strip()
        due_date_str = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', '').strip()

        if not task_text:
            flash("⚠️ Task cannot be empty!", "error")
            return redirect(url_for('edit', task_id=task.id))

        task.task = task_text
        task.priority = priority if priority in ['Low', 'Medium', 'High'] else None

        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("⚠️ Invalid due date", "error")
        else:
            task.due_date = None

        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.commit()
            task.category = category
        else:
            task.category = None

        db.session.commit()
        flash("✏️ Task updated!", "success")
        return redirect(url_for('index'))

    return render_template('edit.html', task=task, categories=categories)

if __name__ == '__main__':
    app.run(debug=True)
