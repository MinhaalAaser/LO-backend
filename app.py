from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
#import os
from datetime import timedelta

app = Flask(__name__)
CORS(app)

#basedir = os.path.abspath(os.path.dirname(__file__))
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.sqlite")
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://zpuvvpblcwxkvo:125df0b48d393c41e8d10dfd2b9f7175834252a9c83230486cf3ea6a5d760838@ec2-52-72-109-141.compute-1.amazonaws.com:5432/d97ifkb6hr97r0"
app.config['SECRET_KEY'] = '0845ed3c395a22e08afb995a5d2514338729d6aefbfa28f076988bccf52e35ed'

db = SQLAlchemy(app)
ma = Marshmallow(app)
bc = Bcrypt(app)
migrate = Migrate(app, db)

# Classes for database tables:

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    pwd = db.Column(db.Text, nullable=False)
    firstname = db.Column(db.Text, nullable=False)
    lastname = db.Column(db.Text, nullable=False)
    tasks = db.relationship('Tasklist', backref='users', cascade='all,delete,delete-orphan', lazy=True)
    
    def __init__(self, email, pwd, firstname, lastname):      
        self.email = email
        self.pwd = pwd
        self.firstname = firstname
        self.lastname = lastname

    def get_id(self):
        return self.id

class Tasklist(db.Model):
    __tablename__ = "tasks"
    task_id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task = db.Column(db.Text, nullable=False)
    category = db.Column(db.Text, nullable=False)

    def __init__(self, user_id, task, category):
        self.user_id = user_id
        self.task = task
        self.category = category
    
    def serialize(self):
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'task': self.task,
            'category': self.category
        }

class TasklistSchema(ma.Schema):
    class Meta:
        fields = ('task_id', 'user_id', 'task', 'category')

tasks_schema = TasklistSchema()
multi_tasks_schema = TasklistSchema(many=True)

class UserSchema(ma.Schema):
    tasks = ma.Nested(multi_tasks_schema)
    class Meta:
        fields = ('id', 'email', 'pwd', 'firstname', 'lastname', 'tasks' )

users_schema = UserSchema()
multi_users_schema = UserSchema(many=True)
login_response_schema = UserSchema(exclude=('id', 'pwd'))

# initializing LoginManager

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(id):
    user_data = User.query.filter_by(id=id).first()
    if user_data:
        return user_data
    else:
        return None

#Auth related routes:

@app.route("/register", methods=["POST"])
def register():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be sent as JSON')

    post_data = request.get_json()
    email = post_data.get("email")
    pwd = post_data.get("pwd")
    firstname = post_data.get("firstname")
    lastname = post_data.get("lastname")

    pwd_hash = bc.generate_password_hash(pwd, 15).decode('utf-8')
    

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'The email address is already registered'}), 409


    new_user = User(email, pwd_hash, firstname, lastname)
    db.session.add(new_user)
    db.session.commit()
    login_user(user=new_user, remember=True)
    user_tasks = new_user.tasks
    tasks_json = [task.serialize() for task in user_tasks]

    return jsonify({
            'id' : new_user.id,
            'email': new_user.email,
            'firstname': new_user.firstname,
            'lastname': new_user.lastname,
            'tasks': tasks_json}), 200

# @app.route('/user/edit', methods=['PATCH'])
# def edit_user():
#     if request.content_type != 'application/json':
#         return jsonify('Error: Data must be sent as JSON')

#     post_data = request.get_json()
#     user_id = current_user.id
#     new_email = post_data.get("email")
#     new_firstname = post_data.get("firstname")
#     new_lastname = post_data.get("lastname")

#     user = User.query.get(int(user_id))

#     if user:
        
#         user.email = new_email
#         user.firstname = new_firstname
#         user.lastname = new_lastname

#         db.session.commit()

#         return jsonify({
#             'message': f'User {user.firstname} {user.lastname} updated successfully'
#         }), 20
#     else:
#         return jsonify({'message': 'User not found'}), 404

# @app.route('/user/get/<id>', methods=['GET'])
# def get_user(id):
    
#     user = db.session.query(User).filter(User.id == id).first()

#     return jsonify(users_schema.dump(user)), 200
    

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be sent as JSON')
    
    post_data = request.get_json()
    email = post_data.get("email")
    pwd = post_data.get("pwd")

    user = User.query.filter_by(email=email).first()

    if user:
        if bc.check_password_hash(user.pwd, pwd):
            login_user(user, remember=True, duration=timedelta(days=7))
            user_tasks = user.tasks
            tasks_json = [task.serialize() for task in user_tasks] 
        return jsonify({
            'id' : user.id,
            'email': user.email,
            'firstname': user.firstname,
            'lastname': user.lastname,
            'tasks': tasks_json}), 200
        
    return jsonify("Invalid email or password"), 401

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()

    return jsonify({"message": "User logged out successfully"}), 200

# Task related routes

@app.route('/tasks/add', methods=['POST'])

def add_task():
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be sent as JSON')
    
    post_data = request.get_json()
    user_id = post_data.get('user_id')
    task = post_data.get("task")
    category = post_data.get('category')
    
    if category is None:
        category = 'Master'

    new_task = Tasklist(user_id, task, category)
    db.session.add(new_task)
    db.session.commit()

    return jsonify({
        "task_id" : new_task.task_id,
        "user_id" : new_task.user_id,
        "task" : new_task.task,
        "category" : new_task.category
         
    }), 200

@app.route('/tasks/get', methods=['GET'])

def get_tasks():
    user_id = int(request.args.get('user_id'))
    user = User.query.filter_by(id=user_id).first()
    if user:
        user_tasks = user.tasks
        tasks_json = [task.serialize() for task in user_tasks] 
        return jsonify(tasks_json)
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/tasks/edit/<int:task_id>', methods=['PUT'])
def edit_task(task_id):
    if request.content_type != 'application/json':
        return jsonify('Error: Data must be sent as JSON')

    post_data = request.get_json()
    task = Tasklist.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify('Task not found'), 404

    task.task = post_data.get('task', task.task)
    task.category = post_data.get('category', task.category)

    db.session.commit()

    return jsonify({
        'message': 'Task updated successfully',
        'task': task.serialize()
    }), 200

@app.route('/tasks/delete/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Tasklist.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify('Task not found'), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify('Task deleted successfully')

if __name__ == '__main__':
    app.run(debug=True)