import os
import discord
from dotenv import load_dotenv
from main import eval_submission, get_creds, log_submission, safe_filename

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

bot_client = get_creds()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    osr_attachment = next((a for a in message.attachments if a.filename.endswith(".osr")), None)
    if not(osr_attachment):
        return
    os.makedirs("replays", exist_ok=True)
    replay_path = f"replays/{osr_attachment.filename}"
    await osr_attachment.save(replay_path)

    screenshot_attachment = next((a for a in message.attachments if a.filename.lower().endswith((".png", ".jpg", ".jpeg"))), None)
    screenshot_path = None
    if screenshot_attachment:
        ext = os.path.splitext(screenshot_attachment.filename)[1]
        filename = safe_filename(message.author.id, message.created_at, ext)
        screenshot_path = f"replays/{filename}"
        await screenshot_attachment.save(screenshot_path)

    result = eval_submission(bot_client, replay_path)
    log_submission(message.author.id, message.author.name, message.created_at, replay_path, screenshot_path, result)

    match tier := result["tier"]:
        case "correct":
            m = result["match"]
            await message.channel.send(f"Correct map!")
        case "close_diff":
            await message.channel.send(f"Close diff!")
        case "close_artist":
            await message.channel.send(f"Close artist!")
        case "incorrect":
            await message.channel.send(f"Incorrect map!")

client.run(os.getenv("DISCORD_TOKEN"))