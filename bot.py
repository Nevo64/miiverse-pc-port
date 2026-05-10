import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask, jsonify
from threading import Thread

# --- KEEP ALIVE SECTION ---
app = Flask('')

@app.route('/')
def home():
    return "Miiverse Bot is Online!"

@app.route('/request_account', methods=['POST'])
def request_account():
    print("[ACCOUNT REQUEST] New request from EXE!", flush=True)
    asyncio.run_coroutine_threadsafe(notify_beta_channel(), bot.loop)
    return jsonify({"status": "ok"}), 200

def kill_port(port):
    import signal
    try:
        hex_port = format(port, '04X')
        with open('/proc/net/tcp') as f:
            lines = f.readlines()[1:]
        for line in lines:
            parts = line.split()
            if parts[1].split(':')[1].upper() == hex_port:
                inode = parts[9]
                for pid in os.listdir('/proc'):
                    if not pid.isdigit():
                        continue
                    try:
                        for fd in os.listdir(f'/proc/{pid}/fd'):
                            try:
                                link = os.readlink(f'/proc/{pid}/fd/{fd}')
                                if f'[{inode}]' in link:
                                    os.kill(int(pid), signal.SIGTERM)
                                    print(f"[PORT] Freed port {port} (killed PID {pid})", flush=True)
                                    return
                            except Exception:
                                pass
                    except Exception:
                        pass
    except Exception as e:
        print(f"[PORT] Could not free port {port}: {e}", flush=True)

def run_web():
    port = int(os.environ.get('PORT', 5000))
    kill_port(port)
    domains = os.environ.get('REPLIT_DOMAINS', '')
    if domains:
        primary = domains.split(',')[0].strip()
        public_url = f"https://{primary}/api"
    else:
        public_url = f"http://localhost:{port}/api"
    print(f"[WEB] Flask starting on port {port}", flush=True)
    print(f"[WEB] /request_account endpoint: {public_url}/request_account", flush=True)
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
