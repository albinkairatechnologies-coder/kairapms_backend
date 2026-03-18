from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.task import Task
from app.models.other import Comment, Notification
from app.models.user import User

task_bp = Blueprint('task', __name__)

LEAD_ROLES = ['admin', 'team_lead', 'marketing_head', 'crm']

@task_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    data = request.json
    claims = get_jwt()
    assigned_by = int(get_jwt_identity())

    # Only admin and team leads can create/assign tasks
    if claims['role'] not in LEAD_ROLES:
        return jsonify({"error": "Only admins and team leads can create tasks"}), 403

    try:
        assigned_to = int(data['assigned_to']) if data.get('assigned_to') else None
        task_id = Task.create(
            title=data['title'],
            description=data.get('description'),
            assigned_by=assigned_by,
            assigned_to=assigned_to,
            team_id=int(data['team_id']) if data.get('team_id') else None,
            department_id=int(data['department_id']) if data.get('department_id') else None,
            client_id=int(data['client_id']) if data.get('client_id') else None,
            department=data.get('department', 'general'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            due_date=data.get('due_date') or None
        )

        if assigned_to:
            assignee = User.get_by_id(assigned_to)
            assigner = User.get_by_id(assigned_by)
            Notification.create(
                assigned_to,
                "New Task Assigned",
                f"{assigner['name']} assigned you: {data['title']}",
                "task"
            )

        return jsonify({"message": "Task created", "task_id": task_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@task_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    user_id = int(get_jwt_identity())
    claims = get_jwt()

    team_id = request.args.get('team_id')
    department_id = request.args.get('department_id')
    status = request.args.get('status')
    client_id = request.args.get('client_id')

    if client_id:
        tasks = Task.get_by_client(int(client_id))
    elif claims['role'] == 'admin':
        tasks = Task.get_all(
            team_id=int(team_id) if team_id else None,
            department_id=int(department_id) if department_id else None,
            status=status
        )
    elif claims['role'] in LEAD_ROLES:
        tasks = Task.get_for_team_lead(user_id)
    else:
        tasks = Task.get_by_user(user_id)

    return jsonify(tasks), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    task['comments'] = Comment.get_by_task(task_id)
    task['activity'] = Task.get_activity(task_id)
    return jsonify(task), 200


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    data = request.json
    user_id = int(get_jwt_identity())
    claims = get_jwt()

    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    # Employees can only update status/progress on their own tasks
    if claims['role'] == 'employee':
        if task['assigned_to'] != user_id:
            return jsonify({"error": "Unauthorized"}), 403
        allowed = {'status', 'time_spent'}
        data = {k: v for k, v in data.items() if k in allowed}

    try:
        allowed_fields = {'title', 'description', 'assigned_to', 'team_id', 'department_id',
                          'status', 'priority', 'due_date', 'time_spent', 'department'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

        if 'assigned_to' in update_data:
            update_data['assigned_to'] = int(update_data['assigned_to']) if update_data['assigned_to'] else None

        Task.update(task_id, updated_by=user_id, **update_data)

        # Notify on status change
        if data.get('status') == 'completed' and task.get('assigned_by'):
            Notification.create(
                task['assigned_by'],
                "Task Completed",
                f"Task '{task['title']}' has been completed",
                "completion"
            )
        elif data.get('status') == 'review' and task.get('assigned_by'):
            Notification.create(
                task['assigned_by'],
                "Task Ready for Review",
                f"Task '{task['title']}' is ready for your review",
                "review"
            )

        # Notify new assignee if reassigned
        if data.get('assigned_to') and data['assigned_to'] != task.get('assigned_to'):
            assigner = User.get_by_id(user_id)
            Notification.create(
                int(data['assigned_to']),
                "Task Reassigned to You",
                f"{assigner['name']} assigned you: {task['title']}",
                "task"
            )

        return jsonify({"message": "Task updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    claims = get_jwt()
    if claims['role'] != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    conn = __import__('app.utils.database', fromlist=['get_db_connection']).get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Task deleted"}), 200


@task_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(task_id):
    data = request.json
    user_id = int(get_jwt_identity())
    try:
        Comment.create(task_id, user_id, data['comment'])
        # Log activity
        from app.utils.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO task_activity (task_id, user_id, action) VALUES (%s, %s, 'commented')", (task_id, user_id))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({"message": "Comment added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@task_bp.route('/clients/<int:client_id>/stats', methods=['GET'])
@jwt_required()
def get_client_stats(client_id):
    stats = Task.get_stats_by_client(client_id)
    total = sum(s['total'] for s in stats)
    completed = sum(s['completed'] for s in stats)
    percentage = (completed / total * 100) if total > 0 else 0
    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "percentage": round(percentage, 2),
        "by_department": stats
    }), 200
