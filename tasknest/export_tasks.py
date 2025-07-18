import csv
import json
from app import app, db, Task

with app.app_context():
    tasks = Task.query.all()

    # Export to CSV
    with open('tasks_export.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Task', 'Completed', 'Created At'])  # header
        for task in tasks:
            writer.writerow([task.id, task.task, task.completed, task.created_at])

    print("✅ Exported to tasks_export.csv")

    # Export to JSON
    json_data = [
        {
            'id': task.id,
            'task': task.task,
            'completed': task.completed,
            'created_at': str(task.created_at)
        }
        for task in tasks
    ]

    with open('tasks_export.json', 'w', encoding='utf-8') as jsonfile:
        json.dump(json_data, jsonfile, indent=4)

    print("✅ Exported to tasks_export.json")
