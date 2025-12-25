import asyncio
import websockets
import requests
import json
import time

import logging

logger = logging.getLogger(__name__)


class LoginError(Exception):
    pass


class SaveReplayError(Exception):
    pass


class PSWebsocketClient:
    websocket = None
    address = None
    login_uri = None
    username = None
    password = None
    last_message = None
    last_challenge_time = 0

    @classmethod
    async def create(cls, username, password, address):
        self = PSWebsocketClient()
        self.username = username
        self.password = password
        self.address = address
        self.websocket = await websockets.connect(self.address)
        self.login_uri = "https://play.pokemonshowdown.com/api/login"
        return self

    async def join_room(self, room_name):
        message = "/join {}".format(room_name)
        await self.send_message("", [message])
        logger.debug("Joined room '{}'".format(room_name))

    async def receive_message(self):
        message = await self.websocket.recv()
        logger.debug("Received message from websocket: {}".format(message))
        return message

    async def send_message(self, room, message_list):
        message = room + "|" + "|".join(message_list)
        logger.debug("Sending message to websocket: {}".format(message))
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'websocket_client.py:52','message':'Sending websocket message','data':{'room':room,'message_preview':message[:200]},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'F'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        await self.websocket.send(message)
        self.last_message = message
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'websocket_client.py:64','message':'Message sent successfully','data':{'room':room},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'F'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion

    async def avatar(self, avatar):
        await self.send_message("", ["/avatar {}".format(avatar)])
        await self.send_message("", ["/cmd userdetails {}".format(self.username)])
        while True:
            # Wait for the query response and check the avatar
            # |queryresponse|QUERYTYPE|JSON
            msg = await self.receive_message()
            msg_split = msg.split("|")
            if msg_split[1] == "queryresponse":
                user_details = json.loads(msg_split[3])
                if user_details["avatar"] == avatar:
                    logger.info("Avatar set to {}".format(avatar))
                else:
                    logger.warning(
                        "Could not set avatar to {}, avatar is {}".format(
                            avatar, user_details["avatar"]
                        )
                    )
                break

    async def close(self):
        await self.websocket.close()

    async def get_id_and_challstr(self):
        while True:
            message = await self.receive_message()
            split_message = message.split("|")
            if split_message[1] == "challstr":
                return split_message[2], split_message[3]

    async def login(self):
        logger.info("Logging in...")
        client_id, challstr = await self.get_id_and_challstr()
        
        # Check if this is a local server (localhost or 127.0.0.1)
        is_local = "localhost" in self.address or "127.0.0.1" in self.address
        
        if is_local:
            # For local servers with noguestsecurity, use simple guest login
            logger.info("Detected local server, using guest login")
            # Use /trn with empty assertion for noguestsecurity mode
            # Format: /trn username,0, (note the empty assertion at the end)
            message = ["/trn " + self.username + ",0,"]
            await self.send_message("", message)
            
            # Wait for login confirmation
            while True:
                msg = await self.receive_message()
                logger.info("LOGIN: Received message: {}".format(msg[:200]))  # Debug logging
                
                if "|updateuser|" in msg and self.username.lower() in msg.lower():
                    logger.info("Successfully logged in as guest: {}".format(self.username))
                    # Extract userid from the updateuser message
                    # Format: |updateuser|USERNAME|GUEST|AVATAR|
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        userid = parts[2].strip().lower()
                        return userid
                    return self.username.lower()
                # Handle name already taken error
                if "|nametaken|" in msg:
                    logger.error("Username is already in use: {}".format(msg))
                    raise LoginError("Username '{}' is already taken. Please log out of that account first or use a different username.".format(self.username))
                # If we get any error, break and report it
                if "|popup|" in msg or "|error|" in msg:
                    logger.error("Login error: {}".format(msg))
                    raise LoginError("Could not log-in: {}".format(msg))
        else:
            # For online servers, use the standard login flow
            response = requests.post(
                self.login_uri,
                data={
                    "name": self.username,
                    "pass": self.password,
                    "challstr": "|".join([client_id, challstr]),
                },
            )

            if response.status_code != 200:
                logger.error("Could not log-in\nDetails:\n{}".format(response.content))
                raise LoginError("Could not log-in")

            response_json = json.loads(response.text[1:])
            if "actionsuccess" not in response_json:
                logger.error("Login Unsuccessful: {}".format(response_json))
                raise LoginError("Could not log-in: {}".format(response_json))

            assertion = response_json.get("assertion")
            message = ["/trn " + self.username + ",0," + assertion]
            logger.info("Successfully logged in")
            await self.send_message("", message)
            await asyncio.sleep(3)
            return response_json["curuser"]["userid"]

    async def update_team(self, team):
        await self.send_message("", ["/utm {}".format(team)])

    async def challenge_user(self, user_to_challenge, battle_format):
        logger.info("Challenging {}...".format(user_to_challenge))
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'websocket_client.py:154','message':'Sending challenge','data':{'user_to_challenge':user_to_challenge,'battle_format':battle_format},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        message = ["/challenge {},{}".format(user_to_challenge, battle_format)]
        await self.send_message("", message)
        self.last_challenge_time = time.time()
        logger.info("CHALLENGE SENT: /challenge {},{}".format(user_to_challenge, battle_format))
        
        # Give server a moment to process the challenge
        await asyncio.sleep(0.5)
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'websocket_client.py:169','message':'Challenge sent successfully','data':{'last_challenge_time':self.last_challenge_time},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'B'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion

    async def accept_challenge(self, battle_format, room_name, timeout=60):
        """
        Accept a challenge from another user.
        
        Args:
            battle_format: Expected battle format (e.g., "gen9vgc2026regfbo3")
            room_name: Room to join to wait for challenges (e.g., "lobby")
            timeout: Maximum time to wait for a challenge in seconds (default: 60)
        """
        import time
        
        if room_name is not None:
            await self.join_room(room_name)

        logger.info("Waiting for a {} challenge (timeout: {}s)".format(battle_format, timeout))
        username = None
        start_time = time.time()
        
        while username is None:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error(f"Timeout waiting for challenge after {timeout} seconds")
                raise TimeoutError(f"No challenge received within {timeout} seconds")
            
            try:
                # Use asyncio.wait_for to add per-message timeout
                msg = await asyncio.wait_for(self.receive_message(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.debug(f"Still waiting for challenge... ({int(elapsed)}s elapsed)")
                continue
            
            split_msg = msg.split("|")
            
            # Debug logging for challenge-related messages
            if len(split_msg) >= 2 and (split_msg[1] == "pm" or "challenge" in msg.lower()):
                logger.info("RECEIVED MESSAGE: {}".format(msg))
                logger.info("Split message has {} parts".format(len(split_msg)))
                if len(split_msg) >= 2:
                    logger.info("Message type: {}".format(split_msg[1]))
            
            # #region agent log
            try:
                with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({'location':'websocket_client.py:175','message':'Checking challenge message','data':{'msg_parts':len(split_msg),'msg_type':split_msg[1] if len(split_msg)>=2 else 'none','battle_format':battle_format},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
            except Exception as e:
                logger.error(f"Debug log write failed: {e}")
            # #endregion
            
            # Check for challenge message - format can vary, so be flexible
            if (
                len(split_msg) >= 6
                and split_msg[1] == "pm"
                and split_msg[3].strip().replace("!", "").replace("‽", "").lower()
                == self.username.lower()
                and split_msg[4].startswith("/challenge")
            ):
                # Extract format from challenge - could be in split_msg[5] or later
                challenge_format = split_msg[5] if len(split_msg) > 5 else ""
                
                # Check if format matches (exact match or contains the format)
                # For Bo3, the format might be sent as "gen9vgc2026regfbo3" or just "gen9vgc2026regf"
                format_matches = (
                    challenge_format == battle_format or
                    challenge_format.lower() == battle_format.lower() or
                    battle_format.lower() in challenge_format.lower() or
                    challenge_format.lower() in battle_format.lower()
                )
                
                if format_matches:
                    username = split_msg[2].strip()
                    logger.info("FOUND VALID CHALLENGE FROM: {} (format: {})".format(username, challenge_format))
                    # #region agent log
                    try:
                        with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            import json, time
                            f.write(json.dumps({'location':'websocket_client.py:194','message':'Found valid challenge, accepting','data':{'username':username,'battle_format':battle_format,'challenge_format':challenge_format},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
                    except Exception as e:
                        logger.error(f"Debug log write failed: {e}")
                    # #endregion
                else:
                    logger.debug(f"Challenge format mismatch: expected '{battle_format}', got '{challenge_format}'")

        message = ["/accept " + username]
        await self.send_message("", message)
        logger.info("SENT ACCEPT COMMAND: /accept {}".format(username))
        # #region agent log
        try:
            with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({'location':'websocket_client.py:208','message':'Sent accept message','data':{'username':username,'message':message},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'C'})+'\n')
        except Exception as e:
            logger.error(f"Debug log write failed: {e}")
        # #endregion
        
        # Log next few messages to see server response
        logger.info("Waiting for server response to accept...")
        for i in range(3):
            try:
                response = await asyncio.wait_for(self.receive_message(), timeout=2.0)
                logger.info(f"POST-ACCEPT MESSAGE {i+1}: {response[:200]}")
                # #region agent log
                try:
                    with open('d:\\Pokemon\\NewPokemonBattleBuddyAI\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({'location':'websocket_client.py:223','message':f'Post-accept message {i+1}','data':{'msg_preview':response[:200],'has_battle':'>battle-' in response},'timestamp':time.time()*1000,'sessionId':'debug-session','hypothesisId':'G'})+'\n')
                except Exception as e:
                    logger.error(f"Debug log write failed: {e}")
                # #endregion
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for post-accept message {i+1}")
                break

    async def search_for_match(self, battle_format):
        logger.info("Searching for ranked {} match".format(battle_format))
        message = ["/search {}".format(battle_format)]
        await self.send_message("", message)

    async def leave_battle(self, battle_tag):
        message = ["/leave {}".format(battle_tag)]
        await self.send_message("", message)

        while True:
            msg = await self.receive_message()
            if battle_tag in msg and "deinit" in msg:
                return

    async def save_replay(self, battle_tag):
        message = ["/savereplay"]
        await self.send_message(battle_tag, message)
