from app import app, db, Task

with app.app_context():
    tasks = Task.query.all()
    if not tasks:
        print("No tasks found in the database.")
    for task in tasks:
        print(f"{task.id}: {task.task} - {'✅ Done' if task.completed else '🕒 Pending'}")
