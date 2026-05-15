import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
waiting_player = None
active_games = {}

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
    
    for game_id, game in list(active_games.items()):
        if game['player1'] == request.sid or game['player2'] == request.sid:
            other = game['player1'] if game['player2'] == request.sid else game['player2']
            if other:
                socketio.emit('opponent_disconnected', room=other)
            del active_games[game_id]
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
            game_id = f"game_{waiting_player[:8]}_{request.sid[:8]}"
            
            active_games[game_id] = {
                'player1': waiting_player,
                'player2': request.sid,
                'choice1': None,
                'choice2': None
            }
            
            print(f'🎮 Created game {game_id}')
            print(f'   Player1: {waiting_player}')
            print(f'   Player2: {request.sid}')
            
            socketio.emit('match_found', {
                'room_id': game_id,
                'player': 1
            }, room=waiting_player)
            
            socketio.emit('match_found', {
                'room_id': game_id,
                'player': 2
            }, room=request.sid)
            
            waiting_player = None
            print('Waiting player cleared')

@socketio.on('make_move')
def handle_make_move(data):
    game_id = data.get('room_id')
    choice = data.get('choice')
    player = data.get('player')
    
    print(f'🎯 Move received: game={game_id}, player={player}, choice={choice}')
    
    if game_id not in active_games:
        print(f'❌ Game {game_id} not found')
        emit('error', {'message': 'Game not found'})
        return
    
    game = active_games[game_id]
    
    if player == 1:
        game['choice1'] = choice
        print(f'   Player1 chose {choice}')
    else:
        game['choice2'] = choice
        print(f'   Player2 chose {choice}')
    
    print(f'   Current: P1={game["choice1"]}, P2={game["choice2"]}')
    
    if game['choice1'] is not None and game['choice2'] is not None:
        winner = determine_winner(game['choice1'], game['choice2'])
        
        result = {
            'player1_choice': game['choice1'],
            'player2_choice': game['choice2'],
            'winner': winner
        }
        
        print(f'🏆 Winner: {winner}')
        print(f'   Sending result to room {game_id}')
        
        socketio.emit('game_result', result, room=game_id)
        
        del active_games[game_id]
        print(f'   Game {game_id} removed')

def determine_winner(choice1, choice2):
    if choice1 == choice2:
        return 'tie'
    
    wins = {
        ('rock', 'scissors'): 'player1',
        ('scissors', 'paper'): 'player1',
        ('paper', 'rock'): 'player1',
        ('scissors', 'rock'): 'player2',
        ('paper', 'scissors'): 'player2',
        ('rock', 'paper'): 'player2'
    }
    
    return wins.get((choice1, choice2), 'player2')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'Starting server on port {port}')
    socketio.run(app, host='0.0.0.0', port=port, debug=True)