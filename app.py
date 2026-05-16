import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
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
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def disconnect():
    global waiting
    print(f'Client disconnected: {request.sid}')
    if waiting == request.sid:
        waiting = None
    for gid, game in list(games.items()):
        if game['p1'] == request.sid or game['p2'] == request.sid:
            del games[gid]

@socketio.on('find')
def find():
    global waiting
    print(f'Find match from: {request.sid}')
    if waiting is None:
        waiting = request.sid
        emit('wait')
        print(f'Player {request.sid} is waiting')
    else:
        if waiting != request.sid:
            gid = str(hash(waiting + request.sid))
            games[gid] = {
                'p1': waiting,
                'p2': request.sid,
                'c1': None,
                'c2': None
            }
            print(f'Game created: {gid}')
            emit('start', {'gid': gid, 'p': 1}, room=waiting)
            emit('start', {'gid': gid, 'p': 2}, room=request.sid)
            waiting = None

@socketio.on('move')
def move(data):
    gid = data['gid']
    choice = data['choice']
    player = data['player']
    
    print(f'Move: game={gid}, player={player}, choice={choice}')
    
    if gid not in games:
        print(f'Game {gid} not found')
        return
    
    game = games[gid]
    if player == 1:
        game['c1'] = choice
    else:
        game['c2'] = choice
    
    print(f'Choices: P1={game["c1"]}, P2={game["c2"]}')
    
    if game['c1'] and game['c2']:
        winner = 'tie'
        if game['c1'] != game['c2']:
            if (game['c1'] == 'rock' and game['c2'] == 'scissors') or \
               (game['c1'] == 'scissors' and game['c2'] == 'paper') or \
               (game['c1'] == 'paper' and game['c2'] == 'rock'):
                winner = 'p1'
            else:
                winner = 'p2'
        
        print(f'Winner: {winner}')
        
        emit('result', {
            'c1': game['c1'],
            'c2': game['c2'],
            'winner': winner
        }, room=gid)
        del games[gid]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f'Starting server on port {port}')
    socketio.run(app, host='0.0.0.0', port=port)