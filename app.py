import os
import sys
import traceback

# This block catches errors before the bot even starts
try:
    import discord
    from discord import app_commands, ui
    from discord.ext import commands
    from flask import Flask
    from threading import Thread
    import asyncio
except ImportError as e:
    print(f"LIBRERIA MANCANTE: {e}. Assicurati di avere requirements.txt")
    sys.exit(1)

# --- KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Online"

def run_flask():
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Errore Flask: {e}")

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- CONFIG ---
LOGS_CHANNEL_ID = 1488604957262217226 
DOMANDE = [
    "Nome Utente di Discord",
    "Perché vuoi diventare staff? (2-3 frasi)",
    "Quanto tempo potresti dedicare al server ogni giorno?",
    "Perché dovremmo scegliere proprio te? (2-3 frasi)",
    "Prometti di non abusare del tuo potere?",
    "Prometti di rispettare gli ordini dei tuoi superiori?",
    "Cosa faresti se due membri litigano? Che provvedimenti prenderesti?",
    "Cosa faresti se uno staffer abusa del suo potere?",
    "L'applicazione è finita. Desideri aggiungere altro?"
]

# --- VIEWS ---
class ReasonModal(ui.Modal):
    def __init__(self, action, user):
        super().__init__(title=f"{action} Candidatura")
        self.action, self.user = action, user
        self.reason = ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        is_acc = "Accetta" in self.action
        col = discord.Color.green() if is_acc else discord.Color.red()
        txt = "ACCETTATA ✅" if is_acc else "RIFIUTATA ❌"
        try:
            await self.user.send(f"La tua candidatura è stata **{txt}**.\n**Motivo:** {self.reason.value}")
            emb = interaction.message.embeds[0]
            emb.color = col
            emb.add_field(name="Esito", value=f"{txt} da {interaction.user.mention}\nMotivo: {self.reason.value}")
            await interaction.response.edit_message(embed=emb, view=None)
        except:
            await interaction.response.send_message("Log aggiornato, ma DM chiusi.", ephemeral=True)

class StaffReviewView(ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @ui.button(label="Accetta con Motivo", style=discord.ButtonStyle.success)
    async def acc(self, interaction, button):
        await interaction.response.send_modal(ReasonModal("Accetta", self.user))

    @ui.button(label="Rifiuta con Motivo", style=discord.ButtonStyle.danger)
    async def rif(self, interaction, button):
        await interaction.response.send_modal(ReasonModal("Rifiuta", self.user))

class ApplyView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="Candidati Ora", style=discord.ButtonStyle.success, custom_id="app_v7")
    async def btn(self, interaction, button):
        try:
            await interaction.user.send("Iniziamo!")
            await interaction.response.send_message("Controlla i DM!", ephemeral=True)
            asyncio.create_task(self.ask(interaction.user, interaction.guild))
        except:
            await interaction.response.send_message("Apri i DM!", ephemeral=True)

    async def ask(self, user, guild):
        res = []
        for q in DOMANDE:
            await user.send(f"**Domanda:** {q}")
            try:
                m = await bot.wait_for('message', check=lambda m: m.author==user and isinstance(m.channel, discord.DMChannel), timeout=600)
                res.append(m.content)
            except: return
        chan = guild.get_channel(LOGS_CHANNEL_ID)
        if chan:
            emb = discord.Embed(title="Nuova Candidatura", color=discord.Color.blue())
            for q, r in zip(DOMANDE, res): emb.add_field(name=q, value=r[:1024], inline=False)
            await chan.send(embed=emb, view=StaffReviewView(user))

# --- BOT ---
class AppBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = intents.members = intents.direct_messages = True
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        self.add_view(ApplyView())
        await self.tree.sync()

bot = AppBot()

@bot.tree.command(name="setup_apply")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction):
    await interaction.channel.send(view=ApplyView())
    await interaction.response.send_message("Inviato!", ephemeral=True)

if __name__ == "__main__":
    try:
        keep_alive()
        token = os.environ.get('TOKEN')
        if not token:
            print("ERRORE: Variabile TOKEN mancante su Render!")
        else:
            bot.run(token)
    except Exception:
        traceback.print_exc() # Questo stamperà l'errore esatto nei log di Render
