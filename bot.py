import discord
from discord.ext import commands
import os
from flask import Flask, request, jsonify
from threading import Thread

# --- KEEP ALIVE SECTION ---
app = Flask('')

@app.route('/')
def home():
    return "Miiverse Bot is Online!"

@app.route('/request_account', methods=['POST'])
def request_account():
    print("[ACCOUNT REQUEST] Received a new account request from the EXE!", flush=True)
    # Post to beta-testers channel via a flag, handled in bot loop
    app.config['PENDING_REQUESTS'] = app.config.get('PENDING_REQUESTS', 0) + 1
    return jsonify({"status": "ok"}), 200

def run_web():
    port = int(os.environ.get('BOT_PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- BOT SECTION ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# --- WATCHED MESSAGES ---
ACTIVE_MESSAGE_IDS = [
    # 1499853301423018186,  # DISABLED - first message
    1499002118651252818,    # ACTIVE - current message
]

WATCH_CHANNEL_ID = 1498997050723926016
BETA_CHANNEL_ID = 1502946572541886675
PASSCODE = "5858"

# Tracks users waiting to enter their passcode
pending_passcode = set()

# Hook Flask to post Discord messages
import asyncio

@app.route('/request_account', methods=['POST'])
def request_account():
    print("[ACCOUNT REQUEST] New request from EXE!", flush=True)
    asyncio.run_coroutine_threadsafe(notify_beta_channel(), bot.loop)
    return jsonify({"status": "ok"}), 200

async def notify_beta_channel():
    channel = bot.get_channel(BETA_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📥 New Account Request",
            description="Someone entered the secret code in the **Miiverse PC Port** app and is requesting a new account & passcode.",
            color=0x00AEFF
        )
        embed.set_footer(text="Send them a passcode via DM!")
        await channel.send(embed=embed)
        print("[ACCOUNT REQUEST] Posted to beta channel.", flush=True)
    else:
        print(f"[ACCOUNT REQUEST ERROR] Could not find channel {BETA_CHANNEL_ID}", flush=True)

@bot.event
async def on_ready():
    print(f"[READY] Logged in as {bot.user}", flush=True)
    print(f"[ACTIVE MESSAGES] {ACTIVE_MESSAGE_IDS}", flush=True)
    print(f"[GUILDS] Bot is in these servers:", flush=True)
    for guild in bot.guilds:
        print(f"  - {guild.name} (ID: {guild.id})", flush=True)

    channel = bot.get_channel(WATCH_CHANNEL_ID)
    if channel:
        print(f"[CHANNEL] Found channel: #{channel.name}", flush=True)
    else:
        print(f"[CHANNEL ERROR] Cannot find channel {WATCH_CHANNEL_ID}", flush=True)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id not in ACTIVE_MESSAGE_IDS:
        return

    print(f"[REACTION] message_id={payload.message_id} | emoji={str(payload.emoji)!r} | user={payload.user_id}", flush=True)

    if str(payload.emoji) == "\U0001f64f":
        guild = bot.get_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        if member.bot:
            print(f"[SKIP] User is a bot", flush=True)
            return

        pending_passcode.add(member.id)
        print(f"[PASSCODE] Asking {member} for passcode", flush=True)

        try:
            await member.send("Please enter your passcode to receive the download link:")
        except Exception as e:
            print(f"[DM ERROR] {e}", flush=True)
            pending_passcode.discard(member.id)
    else:
        print(f"[SKIP] Emoji mismatch: got {str(payload.emoji)!r}", flush=True)


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not isinstance(message.channel, discord.DMChannel):
        return
    if message.author.id not in pending_passcode:
        return

    if message.content.strip() == PASSCODE:
        pending_passcode.discard(message.author.id)
        print(f"[PASSCODE] Correct code from {message.author}", flush=True)

        await message.channel.send("new account registered")

        embed = discord.Embed(
            title="\U0001f64f Miiverse PC Port - Beta Access",
            description="Access granted! Please do not leak this link.",
            color=0x00AEFF
        )
        embed.add_field(name="Link", value="[Download here](https://your-link.com)")
        await message.channel.send(embed=embed)
    else:
        await message.channel.send("Incorrect passcode. Please try again:")
        print(f"[PASSCODE] Wrong code from {message.author}: {message.content!r}", flush=True)

    await bot.process_commands(message)


keep_alive()
bot.run(os.environ['TOKEN'])
