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
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
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

# --- 1. MODAL PER LE MOTIVAZIONI ---
class ReasonModal(ui.Modal):
    def __init__(self, action: str, user: discord.User):
        super().__init__(title=f"{action} Candidatura")
        self.action = action
        self.target_user = user
        self.reason = ui.TextInput(
            label="Motivazione",
            style=discord.TextStyle.paragraph,
            placeholder="Inserisci qui il motivo...",
            required=True,
            min_length=5
        )

    async def on_submit(self, interaction: discord.Interaction):
        color = discord.Color.green() if "Accetta" in self.action else discord.Color.red()
        status_text = "✅ ACCETTATA" if "Accetta" in self.action else "❌ RIFIUTATA"
        
        try:
            embed_dm = discord.Embed(
                title=f"Aggiornamento Candidatura - {interaction.guild.name}",
                description=f"Ciao! La tua candidatura è stata **{status_text}**.",
                color=color
            )
            embed_dm.add_field(name="Motivazione dello Staff:", value=self.reason.value)
            await self.target_user.send(embed=embed_dm)
            
            # Aggiorna il messaggio nel canale log
            original_embed = interaction.message.embeds[0]
            original_embed.color = color
            original_embed.add_field(name="Esito", value=f"{status_text} da {interaction.user.mention}\n**Motivo:** {self.reason.value}", inline=False)
            
            await interaction.response.edit_message(embed=original_embed, view=None)
            await interaction.followup.send(f"Risposta inviata a {self.target_user.name}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Non ho potuto inviare il DM all'utente (DM chiusi), ma ho aggiornato il log.", ephemeral=True)

# --- 2. VIEW PER LO STAFF (LOG) ---
class StaffReviewView(ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.target_user = user

    @ui.button(label="Accetta", style=discord.ButtonStyle.success, custom_id="approve_simple")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_action(interaction, "Accetta (Senza motivo)", "La tua candidatura è stata accettata! Benvenuto nello staff.")

    @ui.button(label="Accetta con Motivo", style=discord.ButtonStyle.success, custom_id="approve_reason")
    async def approve_reason(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Accetta con", self.target_user))

    @ui.button(label="Rifiuta", style=discord.ButtonStyle.danger, custom_id="deny_simple")
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        await self.process_action(interaction, "Rifiutata (Senza motivo)", "Ci dispiace, ma la tua candidatura è stata rifiutata.")

    @ui.button(label="Rifiuta con Motivo", style=discord.ButtonStyle.danger, custom_id="deny_reason")
    async def deny_reason(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ReasonModal("Rifiuta con", self.target_user))

    async def process_action(self, interaction, action_name, dm_text):
        color = discord.Color.green() if "Accetta" in action_name else discord.Color.red()
        try:
            await self.target_user.send(f"**{interaction.guild.name}**: {dm_text}")
            
            original_embed = interaction.message.embeds[0]
            original_embed.color = color
            original_embed.add_field(name="Esito", value=f"{action_name} da {interaction.user.mention}", inline=False)
            
            await interaction.response.edit_message(embed=original_embed, view=None)
        except discord.Forbidden:
            await interaction.response.send_message("DM chiusi, azione eseguita solo sul log.", ephemeral=True)

# --- 3. VIEW DEL PULSANTE INIZIALE ---
class ApplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Applicazioni per diventare staff", style=discord.ButtonStyle.success, emoji="📝", custom_id="start_apply_dm")
    async def apply_button(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.user
        try:
            await user.send("👋 Ciao! Hai avviato l'applicazione. Rispondi alle seguenti domande.")
            await interaction.response.send_message("Controlla i tuoi DM!", ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Abilita i DM e riprova.", ephemeral=True)

        asyncio.create_task(self.ask_questions(user, interaction.guild))

    async def ask_questions(self, user: discord.User, guild: discord.Guild):
        risposte = []
        for i, domanda in enumerate(DOMANDE, 1):
            await user.send(f"**Domanda {i}/{len(DOMANDE)}:**\n{domanda}")
            def check(m): return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
            try:
                msg = await bot.wait_for('message', check=check, timeout=600.0)
                risposte.append(msg.content)
            except asyncio.TimeoutError:
                await user.send("⏰ Tempo scaduto!")
                return

        channel = guild.get_channel(LOGS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📄 Nuova Applicazione", color=discord.Color.blue())
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
            for q, r in zip(DOMANDE, risposte):
                embed.add_field(name=q, value=r[:1020], inline=False)
            
            # Invio al log con la View per lo staff
            await channel.send(embed=embed, view=StaffReviewView(user))
            await user.send("🎉 Applicazione inviata!")

# --- 4. BOT SETUP ---
class AppBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True
        intents.direct_messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ApplyView())
        # Nota: StaffReviewView non può essere aggiunta qui facilmente perché richiede l'oggetto 'user' dinamico.
        # Tuttavia, funzionerà finché il bot non si riavvia.
        await self.tree.sync()

bot = AppBot()

@bot.tree.command(name="setup_apply", description="Invia il pannello Applicazioni")
@app_commands.checks.has_permissions(administrator=True)
async def setup_apply(interaction: discord.Interaction):
    await interaction.channel.send(view=ApplyView())
    await interaction.response.send_message("Inviato!", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('TOKEN'))
