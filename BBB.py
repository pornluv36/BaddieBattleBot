import discord
import random
import os
import logging
import io
import aiohttp

logging.basicConfig(filename='bot_log.txt', level=logging.INFO)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN is None:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    exit(1)

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# Function to load the current game number from a file
def load_current_game_number():
    if os.path.exists("game_number.txt"):
        with open("game_number.txt", "r") as file:
            try:
                return int(file.read())
            except ValueError:
                return 1
    else:
        return 1

current_game_number = load_current_game_number()
game_active = False
game_ready = False  # Initialize game_ready to False
player1_id = None
player2_id = None

game_details = {
    "player1": {
        "id": None,
        "thread_id": None,
        "images": [],
        "predictions": [],
        "ratings": [],
        "score": 0,
        "health": 100,
        "prediction_prompt_id": None,
        "image_message_ids": [],  # Added this line
    },
    "player2": {
        "id": None,
        "thread_id": None,
        "images": [],
        "predictions": [],
        "ratings": [],
        "score": 0,
        "health": 100,
        "prediction_prompt_id": None,
        "image_message_ids": [],  # Added this line
    },
    "status": "waiting_for_players",
    "round": 0,
}
current_game_number += 1

def reset_game_variables():
    global game_details, game_active, player1_id, player2_id
    game_details = {
        "player1": {
            "id": None,
            "images": [],
            "predictions": [],
            "ratings": [],
            "score": 0,
            "health": 100,
            "prediction_prompt_id": None,
            "image_message_ids": [],  # Added this line
        },
        "player2": {
            "id": None,
            "images": [],
            "predictions": [],
            "ratings": [],
            "score": 0,
            "health": 100,
            "prediction_prompt_id": None,
            "image_message_ids": [],  # Added this line
        },
        "status": "waiting_for_players",
        "round": 0,
    }
    game_active = False
    player1_id = None
    player2_id = None

def reset_round_variables():
    global game_details
    game_details["player1"].update({
        "images": [],
        "predictions": [],
        "ratings": [],
        "score": 0,
        "image_message_ids": [],  # Added this line
    })
    game_details["player2"].update({
        "images": [],
        "predictions": [],
        "ratings": [],
        "score": 0,
        "image_message_ids": [],  # Added this line
    })
    game_details.update({
        "status": "waiting_for_players",
        "round": game_details["round"] + 1,
    })

# Function to save the current game number to a file
def save_current_game_number(game_number):
    with open("game_number.txt", "w") as file:
        file.write(str(game_number))

def set_game_active(new_state):
    global game_active
    if game_active != new_state:
        game_active = new_state

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    global game_active, game_ready, player1_id, player2_id
    print(f"New message received from {message.author}: {message.content}")
    print(f"Message object: {message}")

    if message.author == client.user:
        print("Message is from the bot, ignoring.")
        return

    if message.attachments:
        for attachment in message.attachments:
            print(f"New image uploaded: {attachment.url}")

    if message.content.startswith('$start'):
        if game_active:
            print("Game is already active.")
            await message.channel.send(
                "A game is already active. Please wait for the current game to finish before starting a new one.")
        elif game_ready:
            print("Game has already started.")
        else:
            game_ready = True
            print("Game started!")
            player1_id = message.author.id
            game_details["player1"]["id"] = player1_id  # Update the game_details dictionary
            await message.channel.send(f"Greetings **Player 1**! Waiting for another player to $join")


    elif message.content.startswith('$join'):
        if game_active:
            print("Game is already active.")
            await message.channel.send(
                "A game is already active. Please wait for the current game to finish before joining.")
        elif not game_ready:
            print("Game is not ready yet.")
            await message.channel.send("The game is not yet ready. Please wait for it to be prepared.")
        elif player2_id is not None:
            print("Player 2 has already joined.")
            await message.channel.send("Player 2 has already joined the game.")

        else:
            player2_id = message.author.id
            game_details["player2"]["id"] = player2_id
            await message.channel.send(f"Player 2 has joined the game!")
            await message.channel.send(
                f"Alright players, let's setup **Game {current_game_number}**! Please create a private thread by clicking the 'threads' icon at the top of the window (next to the notification bell) and invite the bot. Here are your private thread names:")
            await message.channel.send(f"Player 1: '** Player {player1_id} Game {current_game_number}**'")
            await message.channel.send(f"Player 2: '** Player {player2_id} Game {current_game_number}**'")
            await message.channel.send(
                "Copy your respective thread name and create a thread with that exact name. Once you've both created and invited the bot to your private threads, you can start uploading images.")


    elif message.content.startswith('$ready'):
        if game_active:
            await message.channel.send(
                "A game is already active. Please wait for the current game to finish before starting a new one.")
        elif not game_ready:
            await message.channel.send("The game is not yet ready. Please wait for it to be prepared.")
        else:
            player1_thread = None
            player2_thread = None
            for thread in message.guild.threads:
                thread_name = thread.name
                if f'Game {current_game_number}' in thread_name:
                    try:
                        player_id_in_thread = int(thread_name.split(' ')[1])  # Extract player ID from the thread name
                    except ValueError:
                        logging.warning(f"Could not extract player ID from thread name: {thread_name}")
                        continue
                    if player_id_in_thread == player1_id:
                        player1_thread = thread
                    elif player_id_in_thread == player2_id:
                        player2_thread = thread

            # Check if the bot is mentioned in a thread
            if client.user in message.mentions and isinstance(message.channel, discord.Thread):
                # Directly store the thread ID without extracting the player ID from the thread name
                if message.author.id == game_details["player1"]["id"]:
                    game_details["player1_thread_id"] = message.channel.id
                elif message.author.id == game_details["player2"]["id"]:
                    game_details["player2_thread_id"] = message.channel.id
            if player1_thread is not None and player2_thread is not None:
                game_active = True
                print("Game started! The private threads are ready.")
                player1_instructions = "Player 1, please upload your images in this private thread."
                player2_instructions = "Player 2, please upload your images in this private thread."
                await player1_thread.send(player1_instructions)
                await player2_thread.send(player2_instructions)
            else:
                await message.channel.send("Both players need to create their private threads and invite the bot.")
                logging.warning("Both player threads not found.")  # Log a warning if both player threads are not found

    # Handling image attachments
    elif isinstance(message.channel, discord.Thread) and message.attachments:
        print("Entered the block to handle image attachments.")  # New print statement

        thread_name = message.channel.name
        try:
            # Extract player ID from the thread name
            player_id_in_thread = int(thread_name.split(' ')[1])
        except ValueError:
            logging.warning(f"Could not extract player ID from thread name: {thread_name}")
            return

        try:
            # Print the values to debug
            print(f"player_id_in_thread: {player_id_in_thread}")
            print(f"game_details: {game_details}")

            # Initialize player_key to None before identifying the player
            player_key = None

            # Identify the player
            if player_id_in_thread == game_details["player1"]["id"]:
                player_key = "player1"
            elif player_id_in_thread == game_details["player2"]["id"]:
                player_key = "player2"
            else:
                logging.warning(f"Unknown player ID in thread name: {thread_name}")
                return

            print(f"Image URLs: {[att.url for att in message.attachments]}")
            print(f"Identified player: {player_key}")  # New print statement

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return

        # The rest of your existing code follows, outside of the try-except block

        # Check if the player has already submitted 3 images
        if len(game_details[player_key]["images"]) >= 3:
            await message.channel.send("You have already submitted 3 images. Please wait for the other player.")
            return

        # Add the images to the player's list of images
        for attachment in message.attachments:
            game_details[player_key]["images"].append(attachment.url)
        await message.channel.send(
            f"You have submitted {len(message.attachments)} image(s). You have now submitted a total of {len(game_details[player_key]['images'])} images.")

        # Check if both players have submitted their three images
        if len(game_details["player1"]["images"]) == 3 and len(game_details["player2"]["images"]) == 3:
            game_details["status"] = "waiting_for_predictions"
            await message.channel.send(
                "Both players have submitted their images. Please react to each of your uploaded images with 🥇, 🥈, or 🥉 to indicate your prediction for that image."
            )

    else:
        if message.attachments:
            # ... (Here, you can add logic to handle attachments sent outside of private threads)
            await message.channel.send("Please send attachments in the private threads.")


@client.event
async def on_reaction_add(reaction, user):
    if isinstance(reaction.message.channel, discord.Thread):
        thread_name = reaction.message.channel.name
        player_key = get_player_key_from_thread_name(thread_name)

        # Check if the reaction is a valid prediction and is added to an image message
        if game_details["status"] == "waiting_for_predictions":
            if is_valid_prediction_reaction(reaction) and reaction.message.id in game_details[player_key][
                "image_message_ids"]:
                await handle_prediction(reaction, user, player_key)
            else:
                await reaction.message.remove_reaction(reaction.emoji, user)

        # Handling ratings based on game status
        elif game_details["status"] == "waiting_for_ratings":
            if is_valid_rating_reaction(reaction) and reaction.message.id in game_details['player1'][
                'image_message_ids'] + game_details['player2']['image_message_ids']:
                await handle_rating(reaction, user, player_key)
            else:
                await reaction.message.remove_reaction(reaction.emoji, user)

        # Handling ratings based on game status
        elif game_details["status"] == "waiting_for_ratings":
            if is_valid_rating_reaction(reaction):
                await handle_rating(reaction, user, player_key)
            else:
                await reaction.message.remove_reaction(reaction.emoji, user)
    if str(reaction.emoji) in ["🥇", "🥈", "🥉"]:
        # Check if the reaction is added to an image message
        if reaction.message.id in game_details["player1"]["image_message_ids"] + game_details["player2"][
            "image_message_ids"]:
            # It's a prediction reaction, handle it accordingly
            await handle_prediction(reaction, user, player_key)
        else:
            # The reaction is not added to an image message, remove the reaction
            await reaction.message.remove_reaction(reaction.emoji, user)

def is_valid_prediction_reaction(reaction):
    """Check if the reaction is a valid prediction reaction."""
    return str(reaction.emoji) in ["🥇", "🥈", "🥉"]


def is_valid_rating_reaction(reaction):
    """Check if the reaction is a valid rating reaction."""
    return str(reaction.emoji) in [str(i) + "\u20E3" for i in range(1, 11)]


def get_player_key_from_thread_name(thread_name):
    """Get the player key from the thread name."""
    if "Player 1" in thread_name:
        return "player1"
    elif "Player 2" in thread_name:
        return "player2"
    else:
        logging.warning(f"Unknown player in thread name: {thread_name}")
        return None
In this modified function, it checks if "Player 1" or "Play


async def handle_prediction(reaction, user, player_key):
    # Logic to handle predictions, such as updating the game_details dictionary with the new prediction
    emoji_to_number = {"🥇": 1, "🥈": 2, "🥉": 3}
    image_index = game_details[player_key]["image_message_ids"].index(reaction.message.id)

    # Save the prediction
    game_details[player_key]["predictions"].append((image_index, emoji_to_number[str(reaction.emoji)]))

    await reaction.message.channel.send(f"Prediction received for image {image_index + 1}: {reaction.emoji}")


async def handle_rating(reaction, user, player_key):
    # Logic to handle ratings, such as updating the game_details dictionary with the new rating
    if game_details["status"] == "waiting_for_ratings":
        if reaction.message.id in game_details['player1']['image_message_ids'] + game_details['player2']['image_message_ids']:  # Updated this line
            valid_reactions = [str(i) + "\u20E3" for i in range(1, 11)]
            if str(reaction.emoji) not in valid_reactions:
                await reaction.message.remove_reaction(reaction.emoji, user)
                return

        # Identify the player and the image being rated
        if reaction.message.id in game_details['player1']['image_message_ids']:  # Updated this line
            rater = "player2"
            image_index = game_details['player1']['image_message_ids'].index(reaction.message.id)  # Updated this line
        else:
            rater = "player1"
            image_index = game_details['player2']['image_message_ids'].index(reaction.message.id)  # Updated this line

        # Save the rating
        rating = int(str(reaction.emoji)[0])  # Get the number from the emoji
        game_details[rater]["ratings"].append((image_index, rating))

async def calculate_scores(channel):
    global game_details

    # Step 1: Retrieve predictions and ratings
    player1_predictions = game_details["player1"]["predictions"]
    player2_predictions = game_details["player2"]["predictions"]
    player1_ratings = [rating[1] for rating in sorted(game_details["player1"]["ratings"], key=lambda x: x[0])]
    player2_ratings = [rating[1] for rating in sorted(game_details["player2"]["ratings"], key=lambda x: x[0])]

    # Step 2: Determine correct predictions and calculate scores (damage points)
    player1_score = sum(player1_ratings[i] for i in range(3) if player1_predictions[i] == player2_ratings.index(
        sorted(player2_ratings, reverse=True)[i]) + 1)
    player2_score = sum(player2_ratings[i] for i in range(3) if player2_predictions[i] == player1_ratings.index(
        sorted(player1_ratings, reverse=True)[i]) + 1)

    # Step 3: Update the scores and health
    game_details["player1"]["score"] += player1_score
    game_details["player2"]["score"] += player2_score
    game_details["player1"]["health"] -= player2_score
    game_details["player2"]["health"] -= player1_score

    # Step 4: Check the game status and inform players
    if game_details["player1"]["health"] <= 0 and game_details["player2"]["health"] <= 0:
        await channel.send("The game is a tie.")
        reset_game_variables()
    elif game_details["player1"]["health"] <= 0:
        await channel.send("Player 2 wins! Player 1 has 0 or less health.")
        reset_game_variables()
    elif game_details["player2"]["health"] <= 0:
        await channel.send("Player 1 wins! Player 2 has 0 or less health.")
        reset_game_variables()
    else:
        await channel.send(
            f"Round complete. Player 1 health: {game_details['player1']['health']}, Player 2 health: {game_details['player2']['health']}. Starting a new round.")
        reset_round_variables()


async def check_predictions_complete(channel):
    global game_details
    if len(game_details["player1"]["predictions"]) == 3 and len(game_details["player2"]["predictions"]) == 3:
        game_details["status"] = "waiting_for_ratings"

        # Shuffle the images before sending them for rating
        random.shuffle(game_details["player1"]["images"])
        random.shuffle(game_details["player2"]["images"])

        # Send the images to the channel for rating
        for img_url in game_details["player1"]["images"]:
            msg = await channel.send(img_url)
            game_details["player1_image_message_ids"].append(msg.id)
        for img_url in game_details["player2"]["images"]:
            msg = await channel.send(img_url)
            game_details["player2_image_message_ids"].append(msg.id)

        # Inform players to rate the images
        await channel.send("All images have been submitted. Please rate each image from 1-10.")


client.run(TOKEN)
