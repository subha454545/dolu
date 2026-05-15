import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
rooms = {}
waiting_player = None
room_counter = 1

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/healthz')
def health():
    return "OK", 200

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_player
    if waiting_player == request.sid:
        waiting_player = None

@socketio.on('find_match')
def handle_find_match():
    global waiting_player, room_counter
    
    if waiting_player is None:
        waiting_player = request.sid
        emit('waiting')
    else:
        room_id = f"room_{room_counter}"
        room_counter += 1
        
        rooms[room_id] = {
            'player1': waiting_player,
            'player2': request.sid,
            'choice1': None,
            'choice2': None
        }
        
        socketio.emit('match_found', {'room_id': room_id, 'player': 1}, room=waiting_player)
        socketio.emit('match_found', {'room_id': room_id, 'player': 2}, room=request.sid)
        waiting_player = None

@socketio.on('make_move')
def handle_make_move(data):
    room_id = data['room_id']
    choice = data['choice']
    player = data['player']
    
    if room_id in rooms:
        room = rooms[room_id]
        if player == 1:
            room['choice1'] = choice
        else:
            room['choice2'] = choice
        
        if room['choice1'] and room['choice2']:
            winner = determine_winner(room['choice1'], room['choice2'])
            
            result = {
                'action': 'game_result',
                'player1_choice': room['choice1'],
                'player2_choice': room['choice2'],
                'winner': winner
            }
            
            socketio.emit('game_result', result, room=room_id)
            del rooms[room_id]

def determine_winner(choice1, choice2):
    if choice1 == choice2:
        return 'tie'
    wins = {
        ('rock', 'scissors'): 'player1',
        ('scissors', 'paper'): 'player1',
        ('paper', 'rock'): 'player1',
        ('scissors', 'rock'): 'player2',
        ('paper', 'scissors'): 'player2',
        ('rock', 'paper'): 'player2',
    }
    return wins.get((choice1, choice2), 'player2')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)