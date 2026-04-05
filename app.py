import os
import discord
from discord import app_commands, ui
from discord.ext import commands
from flask import Flask
from threading import Thread
import asyncio

# --- 1. WEB SERVER (KEEP ALIVE) ---
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

# --- 2. CONFIGURATION ---
LOGS_CHANNEL_ID = 1488894440797110318 

DOMANDE = [
    "Nome Utente di Discord",
    "Perché vuoi diventare staff? (2-3 frasi)",
    "Quanto tempo potresti dedicare al server ogni giorno?",
    "Perché dovremmo scegliere proprio te invece di qualcun altro? (2-3 frasi)",
    "Prometti di non abusare del tuo potere?",
    "Prometti di rispettare gli ordini dei tuoi superiori?",
    "Se vedi due membri del server litigare, cosa faresti? Che provvedimenti prenderesti?",
    "Se uno staffer abusa di potere cosa faresti?",
    "L'applicazione è finita. Desideri aggiungere qualcos'altro?"
]

# --- 3. MODAL FOR REASONS ---
class ReasonModal(ui.Modal):
    def __init__(self, action: str, target_user: discord.User):
        super().__init__(title=f"{action} Candidatura")
        self.action = action
        self.target_user = target_user
        
        self.reason_input = ui.TextInput(
            label="Motivazione",
            style=discord.TextStyle.paragraph,
            placeholder="Scrivi qui il motivo...",
            required=True,
            min_length=5
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        is_approval = "Accetta" in self.action
        color = discord.Color.green() if is_approval else discord.Color.red()
        status_text = "ACCETTATA ✅" if is_approval else "RIFIUTATA ❌"
        
        try:
            embed_dm = discord.Embed(title=f"Esito Candidatura - {interaction.guild.name}", color=color)
            embed_dm.description = f"La tua candidatura è stata **{status_text}**."
            embed_dm.add_field(name="Motivazione dello Staff:", value=self.reason_input.value)
            await self.target_user.send(embed=embed_dm)
            
            embed_log = interaction.message.embeds[0]
            embed_log.color = color
            embed_log.add_field(name="Decisione Finale", value=f"{status_text} da {interaction.user.mention}\n**Motivo:** {self.reason_input.value}", inline=False)
            
            await interaction.response.edit_message(embed=embed_log, view=None)
        except Exception as e:
            await interaction.response.send_message(f"Log aggiornato, ma DM chiusi: {e}", ephemeral=True)

# --- 4. STAFF REVIEW VIEW (THE 4 BUTTONS) ---
class StaffReviewView(ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=None)
        self.target_user = target_user

    # BUTTON 1: Accept without reason
    @ui.button(label="Accetta", style=discord.ButtonStyle.success, emoji="✔️")
    async def approve_simple(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_simple(interaction, "ACCETTATA ✅", discord.Color.green())

    # BUTTON 2: Accept with reason (Modal)
    @ui.button(label="Accetta con Motivo", style=discord.ButtonStyle.success, emoji="📝")
    async def approve_reason(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Accetta", self.target_user))

    # BUTTON 3: Deny without reason
    @ui.button(label="Rifiuta", style=discord.ButtonStyle.danger, emoji="✖️")
    async def deny_simple(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_simple(interaction, "RIFIUTATA ❌", discord.Color.red())

    # BUTTON 4: Deny with reason (Modal)
    @ui.button(label="Rifiuta con Motivo", style=discord.ButtonStyle.danger, emoji="🚫")
    async def deny_reason(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Rifiuta", self.target_user))

    async def process_simple(self, interaction, status_text, color):
        try:
            # Send simple Embed to user
            embed_dm = discord.Embed(title=f"Esito Candidatura - {interaction.guild.name}", color=color)
            embed_dm.description = f"La tua candidatura è stata **{status_text}**."
            await self.target_user.send(embed=embed_dm)
            
            # Update Log
            embed_log = interaction.message.embeds[0]
            embed_log.color = color
            embed_log.add_field(name="Decisione Finale", value=f"{status_text} da {interaction.user.mention}", inline=False)
            
            await interaction.response.edit_message(embed=embed_log, view=None)
        except Exception as e:
            await interaction.response.send_message(f"Log aggiornato, ma DM chiusi: {e}", ephemeral=True)

# --- 5. MAIN APPLY VIEW ---
class ApplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Candidati Ora", style=discord.ButtonStyle.success, custom_id="apply_button_v14_final")
    async def apply_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        try:
            await user.send("📝 L'applicazione è iniziata! Rispondi alle domande qui sotto.")
            await interaction.response.send_message("Ti ho scritto in privato!", ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Errore: Abilita i DM e riprova.", ephemeral=True)

        asyncio.create_task(self.run_interview(user, interaction.guild))

    async def run_interview(self, user, guild):
        risposte = []
        total_questions = len(DOMANDE)
        
        for i, q in enumerate(DOMANDE, 1):
            dm_embed = discord.Embed(
                title="Gestore Applicazioni", 
                description=f"**{i}/{total_questions}. {q}**",
                color=discord.Color.blue()
            )
            await user.send(embed=dm_embed)
            
            def check(m): return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
            try:
                msg = await bot.wait_for('message', check=check, timeout=600.0)
                risposte.append(msg.content)
            except asyncio.TimeoutError:
                await user.send("⏰ Tempo scaduto! La candidatura è stata rifiutata.")
                return

        log_chan = guild.get_channel(LOGS_CHANNEL_ID)
        if log_chan:
            # Send log to staff
            embed_staff = discord.Embed(title="Nuova Candidatura Staff", color=discord.Color.blue())
            embed_staff.set_author(name=user.name, icon_url=user.display_avatar.url)
            for q, r in zip(DOMANDE, risposte):
                embed_staff.add_field(name=q, value=r[:1024], inline=False)
            
            await log_chan.send(embed=embed_staff, view=StaffReviewView(user))
            
            # FINAL DM MESSAGE AS EMBED
            final_dm = discord.Embed(
                title="Applicazione Terminata",
                description="✅ **La tua candidatura è stata inviata correttamente allo staff!**\nTi faremo sapere l'esito il prima possibile.",
                color=discord.Color.green()
            )
            await user.send(embed=final_dm)

# --- 6. BOT CLASS ---
class AppBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ApplyView())
        await self.tree.sync()

bot = AppBot()

@bot.tree.command(name="setup_apply", description="Invia il pannello candidature")
@app_commands.checks.has_permissions(administrator=True)
async def setup_apply(interaction: discord.Interaction):
    embed = discord.Embed(title="💼 Candidature Staff", description="Clicca il pulsante sotto per iniziare. L'applicazione ha un limite di tempo e, se superato, porterà al rifiuto automatico dell'applicazione", color=discord.Color.gold())
    await interaction.channel.send(embed=embed, view=ApplyView())
    await interaction.response.send_message("Pannello inviato!", ephemeral=True)

# --- 7. EXECUTION ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.environ.get('TOKEN')
    if TOKEN:
        bot.run(TOKEN)
