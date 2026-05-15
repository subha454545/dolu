# app.py - Stone Paper Scissors Multiplayer Game Server
import asyncio
import json
import os
import signal
import http
from websockets.asyncio.server import serve
from dataclasses import dataclass
from typing import Dict, Set

@dataclass
class GameRoom:
    player1: any = None
    player2: any = None
    choice1: str = None
    choice2: str = None

class GameServer:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.waiting_players: Set = set()
        self.next_room_id = 1

    def determine_winner(self, choice1: str, choice2: str) -> str:
        """Return 'player1', 'player2', or 'tie'"""
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

    async def handle_message(self, websocket):
        """Handle incoming WebSocket messages"""
        try:
            async for message in websocket:
                data = json.loads(message)
                action = data.get('action')

                if action == 'find_match':
                    # Check if someone is waiting
                    if self.waiting_players:
                        opponent = self.waiting_players.pop()
                        room_id = str(self.next_room_id)
                        self.next_room_id += 1
                        
                        room = GameRoom(player1=opponent, player2=websocket)
                        self.rooms[room_id] = room
                        
                        # Tell both players they found a match
                        await opponent.send(json.dumps({
                            'action': 'match_found',
                            'room_id': room_id,
                            'player': 1
                        }))
                        await websocket.send(json.dumps({
                            'action': 'match_found',
                            'room_id': room_id,
                            'player': 2
                        }))
                    else:
                        # Add to waiting queue
                        self.waiting_players.add(websocket)
                        await websocket.send(json.dumps({
                            'action': 'waiting'
                        }))

                elif action == 'make_move':
                    room_id = data['room_id']
                    choice = data['choice']
                    player = data['player']
                    room = self.rooms.get(room_id)
                    
                    if room:
                        if player == 1:
                            room.choice1 = choice
                        else:
                            room.choice2 = choice
                        
                        # If both players have chosen, determine winner
                        if room.choice1 and room.choice2:
                            winner = self.determine_winner(room.choice1, room.choice2)
                            
                            result_msg = json.dumps({
                                'action': 'game_result',
                                'player1_choice': room.choice1,
                                'player2_choice': room.choice2,
                                'winner': winner
                            })
                            
                            await room.player1.send(result_msg)
                            await room.player2.send(result_msg)
                            
                            # Clean up the room
                            del self.rooms[room_id]

        except:
            # Player disconnected
            pass
        finally:
            self.waiting_players.discard(websocket)

async def health_check(connection, request):
    """Respond to Koyeb health checks"""
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, "OK\n")

async def main():
    # Get port from environment (Koyeb sets this automatically)
    port = int(os.environ.get("PORT", "8080"))
    
    # Create game server
    game_server = GameServer()
    
    # Start WebSocket server
    async with serve(
        game_server.handle_message,
        "",
        port,
        process_request=health_check
    ) as server:
        print(f"🎮 Game server running on port {port}")
        print(f"🔄 WebSocket endpoint: ws://localhost:{port}")
        
        # Handle graceful shutdown
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, server.close)
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())