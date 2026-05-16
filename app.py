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
def handle_connect():
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    global waiting
    print(f'❌ Client disconnected: {request.sid}')
    
    if waiting == request.sid:
        waiting = None
        print('Waiting player cleared')
    
    # Clean up games
    for gid, game in list(games.items()):
        if game['p1'] == request.sid or game['p2'] == request.sid:
            print(f'Removing game {gid} due to disconnect')
            del games[gid]
            break

@socketio.on('find_match')
def handle_find_match():
    global waiting
    print(f'🔍 Find match from: {request.sid}')
    
    if waiting is None:
        waiting = request.sid
        emit('waiting')
        print(f'Player {request.sid} is now waiting')
    else:
        if waiting != request.sid:
            gid = f"game_{waiting[:6]}_{request.sid[:6]}"
            games[gid] = {
                'p1': waiting,
                'p2': request.sid,
                'c1': None,
                'c2': None
            }
            
            # Join both players to the room
            join_room(gid, sid=waiting)
            join_room(gid, sid=request.sid)
            
            print(f'🎮 Created game: {gid}')
            print(f'   Player1: {waiting}')
            print(f'   Player2: {request.sid}')
            
            # Notify both players
            emit('match_found', {'room': gid, 'player': 1}, room=waiting)
            emit('match_found', {'room': gid, 'player': 2}, room=request.sid)
            
            waiting = None
            print('Waiting player cleared')
        else:
            print('Same player clicked again - ignoring')

@socketio.on('player_ready')
def handle_player_ready(data):
    room = data['room']
    print(f'Player ready in room: {room}')
    emit('opponent_move_made', room=room)

@socketio.on('make_move')
def handle_make_move(data):
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
        print(f'   Player1 chose {choice}')
    else:
        game['c2'] = choice
        print(f'   Player2 chose {choice}')
    
    print(f'   Choices: P1={game["c1"]}, P2={game["c2"]}')
    
    # Check if both players have made their moves
    if game['c1'] is not None and game['c2'] is not None:
        winner = determine_winner(game['c1'], game['c2'])
        
        result = {
            'p1_choice': game['c1'],
            'p2_choice': game['c2'],
            'winner': winner
        }
        
        print(f'🏆 Winner: {winner}')
        print(f'   Sending result to room {gid}')
        
        # Send result to both players in the room
        emit('game_result', result, room=gid)
        
        # Reset choices for next round
        game['c1'] = None
        game['c2'] = None
        print('   Reset choices for next round')

def determine_winner(c1, c2):
    if c1 == c2:
        return 'tie'
    if (c1 == 'rock' and c2 == 'scissors') or \
       (c1 == 'scissors' and c2 == 'paper') or \
       (c1 == 'paper' and c2 == 'rock'):
        return 'player1'
    return 'player2'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print('=' * 50)
    print('🚀 Stone Paper Scissors Server Starting...')
    print(f'📡 Port: {port}')
    print(f'🌐 WebSocket: ws://0.0.0.0:{port}')
    print('=' * 50)
    socketio.run(app, host='0.0.0.0', port=port, debug=False)