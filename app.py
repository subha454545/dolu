import asyncio
import json
import os
import sys
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
        self.waiting_players: set = set()
        self.next_room_id = 1

    def determine_winner(self, choice1: str, choice2: str) -> str:
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
        try:
            async for message in websocket:
                data = json.loads(message)
                action = data.get('action')

                if action == 'find_match':
                    if self.waiting_players:
                        opponent = self.waiting_players.pop()
                        room_id = str(self.next_room_id)
                        self.next_room_id += 1
                        room = GameRoom(player1=opponent, player2=websocket)
                        self.rooms[room_id] = room
                        await opponent.send(json.dumps({'action': 'match_found', 'room_id': room_id, 'player': 1}))
                        await websocket.send(json.dumps({'action': 'match_found', 'room_id': room_id, 'player': 2}))
                    else:
                        self.waiting_players.add(websocket)
                        await websocket.send(json.dumps({'action': 'waiting'}))

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
                            del self.rooms[room_id]
        except:
            pass
        finally:
            self.waiting_players.discard(websocket)

async def main():
    port = int(os.environ.get("PORT", 8080))
    game_server = GameServer()
    async with serve(game_server.handle_message, "0.0.0.0", port) as server:
        print(f"Game server running on port {port}")
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())