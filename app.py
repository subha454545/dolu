import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
waiting = None
games = {}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('connect')
def connect():
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def disconnect():
    global waiting
    print(f'❌ Client disconnected: {request.sid}')
    if waiting == request.sid:
        waiting = None
    for gid, game in list(games.items()):
        if game['p1'] == request.sid or game['p2'] == request.sid:
            del games[gid]

@socketio.on('profile')
def profile(data):
    room = data['room']
    avatar = data['avatar']
    username = data['username']
    print(f'📝 Profile for room {room}: {username} ({avatar})')
    emit('opponent_profile', {'avatar': avatar, 'username': username}, room=room)

@socketio.on('find_match')
def find_match():
    global waiting
    print(f'🔍 Find match from: {request.sid}')
    
    if waiting is None:
        waiting = request.sid
        emit('waiting')
        print(f'   Player {request.sid} is now waiting')
    else:
        if waiting != request.sid:
            gid = f"game_{waiting[:6]}_{request.sid[:6]}"
            games[gid] = {
                'p1': waiting,
                'p2': request.sid,
                'c1': None,
                'c2': None
            }
            print(f'🎮 Created game: {gid}')
            
            emit('match_found', {'room': gid, 'player': 1}, room=waiting)
            emit('match_found', {'room': gid, 'player': 2}, room=request.sid)
            
            waiting = None

@socketio.on('make_move')
def make_move(data):
    gid = data['room']
    choice = data['choice']
    player = data['player']
    
    print(f'🎯 Move: game={gid}, player={player}, choice={choice}')
    
    if gid not in games:
        print(f'   Game {gid} not found!')
        return
    
    game = games[gid]
    if player == 1:
        game['c1'] = choice
    else:
        game['c2'] = choice
    
    if game['c1'] and game['c2']:
        winner = 'tie'
        if game['c1'] != game['c2']:
            if (game['c1'] == 'rock' and game['c2'] == 'scissors') or \
               (game['c1'] == 'scissors' and game['c2'] == 'paper') or \
               (game['c1'] == 'paper' and game['c2'] == 'rock'):
                winner = 'player1'
            else:
                winner = 'player2'
        
        print(f'🏆 Winner: {winner}')
        
        result = {
            'p1_choice': game['c1'],
            'p2_choice': game['c2'],
            'winner': winner
        }
        
        emit('game_result', result, room=gid)
        del games[gid]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f'🚀 Starting server on port {port}')
    socketio.run(app, host='0.0.0.0', port=port)