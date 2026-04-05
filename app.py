import os
import discord
from discord import app_commands, ui
from discord.ext import commands
from flask import Flask
from threading import Thread
import asyncio

# --- KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Application Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION ---
# Replace this with the ID of the channel where staff see the results
LOGS_CHANNEL_ID = 1488604957262217226 

# The questions the bot will ask in DMs
DOMANDE = [
    "Nome Utente di Discord",
    "Perché vuoi diventare staff? (2-3 frasi)",
    "Quanto tempo potresti dedicare al server ogni giorno?",
    "Perché dovremmo scegliere proprio te invece di qualcun altro? (2-3 frasi)",
    "Prometti di non abusare del tuo potere?",
    "Prometti di rispettare gli ordini dei tuoi superiori?",
    "Se vedi due membri del server litigare prendendosi a insulti, cosa faresti e quali provvidementi prenderesti?",
    "Se uno staffer abusa di potere o viola una o più regole cosa faresti?",
    "L'applicazione è finita. Desideri aggiungere qualcos'altro?"
]

# --- 1. THE BUTTON IN THE SERVER ---
class ApplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Applicazioni per diventare staff", style=discord.ButtonStyle.success, emoji="📝", custom_id="start_apply_dm")
    async def apply_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        
        try:
            # Try to send a DM to make sure their DMs are open
            await user.send("👋 Ciao! Hai avviato l'applicazione per diventare staff. Rispondi alle seguenti domande per completarla e avere una possibilità di diventare staff.")
            await interaction.response.send_message("Ti ho inviato un messaggio in privato! Controlla i tuoi DM.", ephemeral=True)
        except discord.Forbidden:
            # If DMs are closed, tell them in the server
            return await interaction.response.send_message("❌ Non posso scriverti in privato! Per favore, abilita i messaggi privati (DM) nelle impostazioni di questo server e riprova.", ephemeral=True)

        # Run the question loop in the background so it doesn't freeze the bot
        asyncio.create_task(self.ask_questions(user, interaction.guild))

    async def ask_questions(self, user: discord.User, guild: discord.Guild):
        risposte = []
        
        for i, domanda in enumerate(DOMANDE, 1):
            await user.send(f"**Domanda {i}/{len(DOMANDE)}:**\n{domanda}")
            
            def check(m):
                # Check that the message is in DMs and from the correct user
                return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
            
            try:
                # Wait 5 minutes per question
                msg = await bot.wait_for('message', check=check, timeout=300.0)
                risposte.append(msg.content)
            except asyncio.TimeoutError:
                await user.send("⏰ Tempo scaduto! La tua applicazione è stata annullata perché non hai risposto in tempo.")
                return

        # All questions answered! Send to logs channel
        channel = guild.get_channel(LOGS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📄 Nuova Applicazione Ricevuta", color=discord.Color.blue())
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            
            for q, r in zip(DOMANDE, risposte):
                # If answers are too long, add_field handles up to 1024 chars
                embed.add_field(name=q, value=r if len(r) < 1000 else r[:997] + "...", inline=False)
                
            embed.set_footer(text=f"User ID: {user.id}")
            await channel.send(embed=embed)
            
            await user.send("🎉 Applicazione terminata! Ho inviato le tue risposte allo staff. Ti faremo sapere!")
        else:
            await user.send("⚠️ Si è verificato un errore nell'invio della candidatura. Fai una foto delle domande e mandale a un amministratore.")

# --- 2. THE BOT ---
class AppBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read DM answers
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ApplyView()) # Makes the button permanent
        await self.tree.sync()

bot = AppBot()

@bot.tree.command(name="setup_apply", description="Invia il pannello per le Applicazioni")
@app_commands.checks.has_permissions(administrator=True)
async def setup_apply(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💼 Applicazione Staff", 
        description="Clicca il pulsante qui sotto per avviare l'applicazione. L'applicazione si svolgerà in DM e ci sarà un limite di tempo.",
        color=discord.Color.gold()
    )
    await interaction.channel.send(embed=embed, view=ApplyView())
    await interaction.response.send_message("Pannello inviato correttamente!", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('TOKEN'))
