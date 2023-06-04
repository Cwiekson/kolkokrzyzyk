import datetime
import random

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import extract

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/kolkokrzyzyk'  #local
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@172.17.0.1:5432/kolkokrzyzyk'   #docker

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credits = db.Column(db.Integer, nullable=False, default=0)
    matches = db.relationship('Game', backref='user')

    def __repr__(self):
        return f'<User {self.id}>'


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_choice = db.Column(db.String(1))
    result = db.Column(db.String(50))
    date_start = db.Column(db.DateTime, default=datetime.datetime.now())
    time = db.Column(db.Time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Game {self.id}>'


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        new_user = User()
        try:
            db.session.add(new_user)
            db.session.commit()
            return render_template('index.html', user=new_user)
        except:
            return 'There was an issue add'

    return render_template('index.html')


@app.route('/update/<int:id>', methods=['POST', 'GET'])
def update_credits(id):
    user = User.query.get_or_404(id)
    if user.credits == 0:
        user.credits = 10
        db.session.commit()
    return render_template('index.html', user=user)


@app.route('/statitics/<int:user_id>', methods=['GET'])
def get_matches(user_id):
    user = User.query.get_or_404(user_id)
    matches = user.matches
    return render_template('statistics.html', user_id=user_id, matches=matches)


@app.route('/statitics/<int:user_id>/<string:day>', methods=['GET'])
def selected_matches(user_id, day):
    matches = Game.query.filter(extract('day', Game.date_start) == day[-2:], Game.user_id == user_id, Game.result =='win').all()
    count_result = {
        'win': len(Game.query.filter(extract('day', Game.date_start) == day[-2:], Game.user_id == user_id, Game.result == 'win').all()),
        'lose':len(Game.query.filter(extract('day', Game.date_start) == day[-2:], Game.user_id == user_id, Game.result == 'lose').all()),
        'draft':len(Game.query.filter(extract('day', Game.date_start) == day[-2:], Game.user_id == user_id, Game.result == 'draft').all())
    }
    return render_template('statistics.html', count_result=count_result,day=day)


@app.route('/game/<int:id>', methods=['POST', 'GET'])
def game(id):
    user = User.query.get_or_404(id)
    if user.credits >= 3:
        user.credits -= 3
        db.session.commit()
        games = Game(user_id=user.id)
        db.session.add(games)
        db.session.commit()
        return render_template('game.html', games_id=games.id)
    return 'You dont have enough credits to play'


@app.route('/play', methods=['POST'])
def play():
    game_id = int(request.form['game_id'])
    board = request.form['board']
    enemy_positions = eval(request.form['enemy_positions'])
    board_place = set_place_on_board(enemy_positions, 2)
    winner = is_winner(board_place)
    if winner:
        game = Game.query.get_or_404(game_id)
        game.time = datetime.datetime.now() - game.date_start
        game.result = winner
        user = User.query.get_or_404(game.user_id)

        if winner == 'win':
            user.credits += 4
        db.session.commit()
        response = {'winner': winner, 'board': board, 'user_id': user.id}
        return jsonify(response)
    our_positions = eval(request.form['our_positions'])
    board_place = set_place_on_board(our_positions, 1)

    available_positions = [i for i in range(9)]

    available_positions = update_avaiable_position(available_positions, our_positions)
    if enemy_positions:
        available_positions = update_avaiable_position(available_positions, enemy_positions)
        board_place = set_place_on_board(enemy_positions, 2, board_place)
    winner = is_winner(board_place)

    if winner:
        game = Game.query.get_or_404(game_id)
        game.time = datetime.datetime.now() - game.date_start
        game.result = winner
        user = User.query.get_or_404(game.user_id)

        if winner == 'win':
            user.credits += 4
        db.session.commit()

        response = {'winner': winner, 'board': board, 'user_id': user.id}
        return jsonify(response)
    if not available_positions:
        game = Game.query.get_or_404(game_id)
        game.time = datetime.datetime.now() - game.date_start
        game.result = 'draft'
        user = User.query.get_or_404(game.user_id)

        db.session.commit()
        response = {'winner': 'Draft', 'board': board, 'user_id': user.id}
        return jsonify(response)
    random_available_index = random.randint(0, len(available_positions) - 1)
    enemy_position = available_positions[random_available_index]

    response = {'winner': None, 'board': board, 'enemy_position': enemy_position}
    return jsonify(response)


def is_winner(board_place):
    winning_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for com in winning_combinations:
        if board_place[com[0]] == board_place[com[1]] == board_place[com[2]]:
            if board_place[com[0]] == 2:
                return 'lose'
            elif board_place[com[0]] == 1:
                return 'win'


def set_place_on_board(positions, value, board_place=None):
    if not board_place:
        board_place = [0] * 9
    for position in positions:
        board_place[position] = value
    return board_place


def update_avaiable_position(available_positions, positions):
    for element in positions:
        if element in available_positions:
            available_positions.remove(element)
    return available_positions


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
