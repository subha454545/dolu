import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)

# Use eventlet for better WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Game state
waiting_player = None
games = {}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('connect')
def handle_connect():
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_player
    print(f'❌ Client disconnected: {request.sid}')
    
    if waiting_player == request.sid:
        waiting_player = None
    
    for game_id, game in list(games.items()):
        if game['p1'] == request.sid or game['p2'] == request.sid:
            other = game['p1'] if game['p2'] == request.sid else game['p2']
            if other:
                socketio.emit('opponent_disconnected', room=other)
            del games[game_id]
            break

@socketio.on('find_match')
def handle_find_match():
    global waiting_player
    print(f'🔍 Find match from: {request.sid}')
    
    if waiting_player is None:
        waiting_player = request.sid
        emit('waiting')
        print(f'Player {request.sid} is waiting')
    else:
        if waiting_player != request.sid:
            game_id = str(hash(waiting_player + request.sid))
            
            games[game_id] = {
                'p1': waiting_player,
                'p2': request.sid,
                'c1': None,
                'c2': None
            }
            
            print(f'🎮 Game created: {game_id}')
            
            socketio.emit('match_found', {
                'room_id': game_id,
                'player': 1
            }, room=waiting_player)
            
            socketio.emit('match_found', {
                'room_id': game_id,
                'player': 2
            }, room=request.sid)
            
            waiting_player = None

@socketio.on('make_move')
def handle_make_move(data):
    game_id = data.get('room_id')
    choice = data.get('choice')
    player = data.get('player')
    
    print(f'🎯 Move: game={game_id}, player={player}, choice={choice}')
    
    if game_id not in games:
        print(f'Game not found: {game_id}')
        return
    
    game = games[game_id]
    
    if player == 1:
        game['c1'] = choice
    else:
        game['c2'] = choice
    
    print(f'Choices: P1={game["c1"]}, P2={game["c2"]}')
    
    if game['c1'] is not None and game['c2'] is not None:
        winner = get_winner(game['c1'], game['c2'])
        
        result = {
            'player1_choice': game['c1'],
            'player2_choice': game['c2'],
            'winner': winner
        }
        
        print(f'🏆 Winner: {winner}')
        
        socketio.emit('game_result', result, room=game_id)
        del games[game_id]

def get_winner(c1, c2):
    if c1 == c2:
        return 'tie'
    if (c1 == 'rock' and c2 == 'scissors') or \
       (c1 == 'scissors' and c2 == 'paper') or \
       (c1 == 'paper' and c2 == 'rock'):
        return 'player1'
    return 'player2'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f'Starting server on port {port}')
    socketio.run(app, host='0.0.0.0', port=port)