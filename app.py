import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
    print(f'✅ Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_player
    print(f'❌ Client disconnected: {request.sid}')
    
    # If waiting player disconnects, clear waiting
    if waiting_player == request.sid:
        waiting_player = None
        print('Waiting player cleared')
    
    # If player in a room disconnects, notify opponent
    for room_id, room in list(rooms.items()):
        if room['player1'] == request.sid or room['player2'] == request.sid:
            print(f'Player from room {room_id} disconnected')
            other = room['player1'] if room['player2'] == request.sid else room['player2']
            if other:
                socketio.emit('opponent_disconnected', room=other)
            del rooms[room_id]
            break

@socketio.on('find_match')
def handle_find_match():
    global waiting_player, room_counter
    print(f'🔍 Find match from: {request.sid}')
    
    if waiting_player is None:
        # No one waiting, add this player to waiting
        waiting_player = request.sid
        print(f'Player {request.sid} is now waiting')
        emit('waiting')
    else:
        # Someone is waiting, create a room
        if waiting_player == request.sid:
            # Same player clicked twice - ignore
            print('Same player clicked again - ignoring')
            return
        
        room_id = f"room_{room_counter}"
        room_counter += 1
        
        rooms[room_id] = {
            'player1': waiting_player,
            'player2': request.sid,
            'choice1': None,
            'choice2': None
        }
        
        print(f'🎮 Created room {room_id} with {waiting_player} and {request.sid}')
        
        # Notify both players
        socketio.emit('match_found', {'room_id': room_id, 'player': 1}, room=waiting_player)
        socketio.emit('match_found', {'room_id': room_id, 'player': 2}, room=request.sid)
        
        # Clear waiting player
        waiting_player = None
        print('Waiting player cleared')

@socketio.on('make_move')
def handle_make_move(data):
    room_id = data.get('room_id')
    choice = data.get('choice')
    player = data.get('player')
    
    print(f'🎯 Move from player {player} in room {room_id}: {choice}')
    
    if room_id not in rooms:
        print(f'Room {room_id} not found')
        emit('error', {'message': 'Room not found'})
        return
    
    room = rooms[room_id]
    
    if player == 1:
        room['choice1'] = choice
    else:
        room['choice2'] = choice
    
    print(f'Room choices: P1={room["choice1"]}, P2={room["choice2"]}')
    
    # Check if both players have made their moves
    if room['choice1'] is not None and room['choice2'] is not None:
        winner = determine_winner(room['choice1'], room['choice2'])
        
        result = {
            'player1_choice': room['choice1'],
            'player2_choice': room['choice2'],
            'winner': winner
        }
        
        print(f'🏆 Game result: {winner}')
        
        # Send result to both players
        socketio.emit('game_result', result, room=room_id)
        
        # Clean up room
        del rooms[room_id]
        print(f'Room {room_id} removed')

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