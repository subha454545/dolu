import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Simple game state
waiting_player = None
games = {}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('find_match')
def handle_find_match():
    global waiting_player
    print(f'Find match from: {request.sid}')
    
    if waiting_player is None:
        waiting_player = request.sid
        emit('waiting')
        print('Player added to waiting')
    else:
        if waiting_player != request.sid:
            room = waiting_player + '_' + request.sid
            games[room] = {
                'p1': waiting_player,
                'p2': request.sid,
                'p1_choice': None,
                'p2_choice': None
            }
            
            join_room(room, sid=waiting_player)
            join_room(room, sid=request.sid)
            
            emit('match_found', {'player': 1, 'room': room}, room=waiting_player)
            emit('match_found', {'player': 2, 'room': room}, room=request.sid)
            
            waiting_player = None
            print(f'Match created: {room}')

@socketio.on('make_move')
def handle_make_move(data):
    room = data['room']
    player = data['player']
    choice = data['choice']
    
    print(f'Move: room={room}, player={player}, choice={choice}')
    
    if room not in games:
        print(f'Game {room} not found')
        return
    
    if player == 1:
        games[room]['p1_choice'] = choice
    else:
        games[room]['p2_choice'] = choice
    
    p1_choice = games[room]['p1_choice']
    p2_choice = games[room]['p2_choice']
    
    if p1_choice and p2_choice:
        winner = get_winner(p1_choice, p2_choice)
        result = {
            'p1_choice': p1_choice,
            'p2_choice': p2_choice,
            'winner': winner
        }
        emit('game_result', result, room=room)
        del games[room]

def get_winner(c1, c2):
    if c1 == c2:
        return 'tie'
    if (c1 == 'rock' and c2 == 'scissors') or \
       (c1 == 'scissors' and c2 == 'paper') or \
       (c1 == 'paper' and c2 == 'rock'):
        return 'player1'
    return 'player2'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)