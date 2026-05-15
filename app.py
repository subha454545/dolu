import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

waiting = None
rooms = {}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('find_match')
def find_match():
    global waiting
    if waiting is None:
        waiting = request.sid
        emit('waiting')
    else:
        if waiting != request.sid:
            room = f"room_{id(waiting)}_{id(request.sid)}"
            rooms[room] = {
                'p1': waiting,
                'p2': request.sid,
                'c1': None,
                'c2': None
            }
            emit('match_found', {'room_id': room, 'player': 1}, room=waiting)
            emit('match_found', {'room_id': room, 'player': 2}, room=request.sid)
            waiting = None

@socketio.on('make_move')
def make_move(data):
    room = data['room_id']
    player = data['player']
    choice = data['choice']
    
    if room not in rooms:
        return
    
    if player == 1:
        rooms[room]['c1'] = choice
    else:
        rooms[room]['c2'] = choice
    
    c1 = rooms[room]['c1']
    c2 = rooms[room]['c2']
    
    if c1 and c2:
        winner = get_winner(c1, c2)
        result = {
            'player1_choice': c1,
            'player2_choice': c2,
            'winner': winner
        }
        emit('game_result', result, room=room)
        del rooms[room]

def get_winner(c1, c2):
    if c1 == c2:
        return 'tie'
    if (c1 == 'rock' and c2 == 'scissors') or \
       (c1 == 'scissors' and c2 == 'paper') or \
       (c1 == 'paper' and c2 == 'rock'):
        return 'player1'
    return 'player2'

if __name__ == '__main__':
    from flask import request
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)