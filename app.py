import os
import discord
from discord import app_commands, ui
from discord.ext import commands
from flask import Flask
from threading import Thread
import asyncio
import sys

# --- KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- CONFIGURATION ---
LOGS_CHANNEL_ID = 1488604957262217226 

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

# --- 1. MODAL ---
class ReasonModal(ui.Modal):
    def __init__(self, action: str, user: discord.User):
        super().__init__(title=f"{action} Candidatura")
        self.action = action
        self.target_user = user
        
        self.reason_input = ui.TextInput(
            label="Motivazione",
            style=discord.TextStyle.paragraph,
            placeholder="Inserisci il motivo qui...",
            required=True,
            min_length=5
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        is_approval = "Accetta" in self.action
        color = discord.Color.green() if is_approval else discord.Color.red()
        status_text = "✅ ACCETTATA" if is_approval else "❌ RIFIUTATA"
        
        try:
            embed_dm = discord.Embed(title=f"Esito Candidatura - {interaction.guild.name}", color=color)
            embed_dm.description = f"La tua candidatura è stata **{status_text}**."
            embed_dm.add_field(name="Motivazione dello Staff:", value=self.reason_input.value)
            await self.target_user.send(embed=embed_dm)
            
            embed_log = interaction.message.embeds[0]
            embed_log.color = color
            embed_log.add_field(name="Decisione Finale", value=f"{status_text} da {interaction.user.mention}\n**Motivo:** {self.reason_input.value}")
            
            await interaction.response.edit_message(embed=embed_log, view=None)
        except Exception as e:
            print(f"Error sending DM: {e}")
            await interaction.response.send_message("Log aggiornato, ma l'utente ha i DM chiusi.", ephemeral=True)

# --- 2. VIEWS ---
class StaffReviewView(ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.target_user = user

    @ui.button(label="Accetta con Motivo", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Accetta", self.target_user))

    @ui.button(label="Rifiuta con Motivo", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Rifiuta", self.target_user))

class ApplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Candidati Ora", style=discord.ButtonStyle.success, custom_id="apply_v6_final")
    async def apply_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        try:
            await user.send("📝 Iniziamo! Rispondi alle domande qui sotto.")
            await interaction.response.send_message("Controlla i tuoi DM!", ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Errore: Abilita i DM nelle impostazioni del server.", ephemeral=True)

        asyncio.create_task(self.run_interview(user, interaction.guild))

    async def run_interview(self, user, guild):
        risposte = []
        for q in DOMANDE:
            await user.send(f"**Domanda:** {q}")
            def check(m): return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
            try:
                msg = await bot.wait_for('message', check=check, timeout=600.0)
                risposte.append(msg.content)
            except asyncio.TimeoutError:
                await user.send("⏰ Tempo scaduto! Candidatura annullata.")
                return

        log_chan = guild.get_channel(LOGS_CHANNEL_ID)
        if log_chan:
            embed = discord.Embed(title="Nuova Candidatura Staff", color=discord.Color.blue())
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            for q, r in zip(DOMANDE, risposte):
                embed.add_field(name=q, value=r[:1024], inline=False)
            
            await log_chan.send(embed=embed, view=StaffReviewView(user))
            await user.send("✅ La tua candidatura è stata inviata allo staff!")

# --- 3. BOT SETUP ---
class AppBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.direct_messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ApplyView())
        await self.tree.sync()

bot = AppBot()

@bot.tree.command(name="setup_apply")
@app_commands.checks.has_permissions(administrator=True)
async def setup_apply(interaction: discord.Interaction):
    embed = discord.Embed(title="💼 Candidature Staff", description="Clicca il pulsante sotto per iniziare.", color=discord.Color.gold())
    await interaction.channel.send(embed=embed, view=ApplyView())
    await interaction.response.send_message("Pannello inviato!", ephemeral=True)

# --- ERROR HANDLER FOR LOGS ---
if __name__ == "__main__":
    try:
        keep_alive()
        TOKEN = os.environ.get('TOKEN')
        if not TOKEN:
            print("CRITICAL ERROR: TOKEN variable is missing on Render!")
            sys.exit(1)
        bot.run(TOKEN)
    except Exception as e:
        print(f"BOT CRASHED WITH ERROR: {e}")
        sys.exit(1)
