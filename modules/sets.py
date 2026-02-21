import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
CARGO_BASE_APROVACAO_ID = 1421254143103996045
canais_aprovacao = {}

def usuario_pode_aprovar(member: discord.Member) -> bool:
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    cargo_base = member.guild.get_role(CARGO_BASE_APROVACAO_ID)
    if not cargo_base:
        return False
    for role in member.roles:
        if role.position >= cargo_base.position:
            return True
    return False

def buscar_usuario_por_id_fivem(guild: discord.Guild, fivem_id: str) -> discord.Member:
    for member in guild.members:
        if member.nick and member.nick.endswith(f" | {fivem_id}"):
            return member
    return None

# ========== VIEWS ==========
class SetStaffView(ui.View):
    def __init__(self, fivem_id, game_nick, user_id, discord_user, recrutador_id, recrutador_nome):
        super().__init__(timeout=None)
        self.fivem_id = fivem_id
        self.game_nick = game_nick
        self.user_id = user_id
        self.discord_user = discord_user
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
    
    @ui.button(label="✅ Aprovar Set", style=ButtonStyle.green, custom_id="aprovar_set")
    async def aprovar(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            member = interaction.guild.get_member(self.user_id)
            if not member:
                await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            novo_nick = f"M | {self.game_nick} | {self.fivem_id}"
            if len(novo_nick) > 32:
                novo_nick = f"M | {self.game_nick[:15]} | {self.fivem_id}"
            
            await member.edit(nick=novo_nick)
            
            cargo = discord.utils.get(interaction.guild.roles, name="🙅‍♂️ | Membro") or discord.utils.get(interaction.guild.roles, name="Membro")
            if cargo:
                await member.add_roles(cargo)
            
            embed = discord.Embed(
                title="✅ SET APROVADO!",
                description=(
                    f"**👤 Discord:** {member.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Aprovado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"✅ **Nickname:** `{novo_nick}`\n"
                    f"✅ **Cargo:** 🙅‍♂️ | Membro"
                ),
                color=discord.Color.green()
            )
            
            if self.recrutador_nome:
                embed.description += f"\n✅ **Recrutado por:** {self.recrutador_nome}"
            
            self.clear_items()
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send(f"✅ Set aprovado!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    @ui.button(label="❌ Recusar Set", style=ButtonStyle.red, custom_id="recusar_set")
    async def recusar(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            embed = discord.Embed(
                title="❌ SET RECUSADO",
                description=(
                    f"**👤 Discord:** {self.discord_user.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Recusado por:** {interaction.user.mention}"
                ),
                color=discord.Color.red()
            )
            
            if self.recrutador_nome:
                embed.description += f"\n**🤝 Recrutado por:** {self.recrutador_nome}"
            
            await interaction.channel.send(embed=embed)
            await interaction.message.delete()
            await interaction.followup.send("✅ Set recusado!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class SetForm(ui.Modal, title="📝 Pedido de Set"):
    nick = ui.TextInput(label="1. Seu Nick no Jogo:", required=True)
    id_fivem = ui.TextInput(label="2. Seu ID do FiveM:", required=True)
    recrutador = ui.TextInput(label="3. ID do Recrutador (obrigatório):", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if not self.id_fivem.value.isdigit() or not self.recrutador.value.isdigit():
            await interaction.followup.send("❌ IDs devem conter apenas números!", ephemeral=True)
            return
        
        canal_id = canais_aprovacao.get(interaction.guild.id)
        if not canal_id:
            await interaction.followup.send("❌ Use !aprovamento #canal primeiro!", ephemeral=True)
            return
        
        canal = interaction.guild.get_channel(canal_id)
        if not canal:
            await interaction.followup.send("❌ Canal inválido!", ephemeral=True)
            return
        
        recrutador_member = buscar_usuario_por_id_fivem(interaction.guild, self.recrutador.value)
        recrutador_nome = recrutador_member.nick or recrutador_member.name if recrutador_member else f"ID: {self.recrutador.value}"
        
        desc = (
            f"**👤 Discord:** {interaction.user.mention}\n"
            f"**🆔 Discord ID:** `{interaction.user.id}`\n"
            f"**🎮 ID Fivem:** `{self.id_fivem.value}`\n"
            f"**👤 Nick do Jogo:** `{self.nick.value}`\n"
            f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"\n**🤝 Recrutado por:** {recrutador_nome}"
        )
        
        if recrutador_member:
            desc += f" ({recrutador_member.mention})"
        
        desc += "\n\n**⏳ Status:** Aguardando aprovação"
        
        embed = discord.Embed(title="🎮 NOVO PEDIDO DE SET", description=desc, color=discord.Color.purple())
        view = SetStaffView(self.id_fivem.value, self.nick.value, interaction.user.id, interaction.user, self.recrutador.value, recrutador_nome)
        
        await canal.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Pedido enviado!", ephemeral=True)

class SetOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Peça seu Set!", style=ButtonStyle.primary, custom_id="pedir_set")
    async def pedir(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SetForm())

# ========== COG ==========
class SetsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Sets carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(SetOpenView())
    
    @commands.command(name="aprovamento")
    @commands.has_permissions(administrator=True)
    async def set_canal(self, ctx, canal: discord.TextChannel = None):
        if not canal:
            canal = ctx.channel
        
        canais_aprovacao[ctx.guild.id] = canal.id
        msg = await ctx.send(f"✅ Canal de Aprovação Definido: {canal.mention}")
        await asyncio.sleep(3)
        await msg.delete()
    
    @commands.command(name="setup_set")
    @commands.has_permissions(administrator=True)
    async def setup_set(self, ctx):
        if ctx.guild.id not in canais_aprovacao:
            await ctx.send("⚠️ Configure o Canal de Aprovação Primeiro!\nUse !aprovamento #canal")
            return
        
        canal = ctx.guild.get_channel(canais_aprovacao[ctx.guild.id])
        
        embed = discord.Embed(
            title="🎮 PEÇA SEU SET AQUI!",
            description=(
                f"Clique no botão abaixo para pedir seu set.\n\n"
                f"**📝 Campos:**\n"
                f"1️⃣ Nick do Jogo\n"
                f"2️⃣ ID do FiveM\n"
                f"3️⃣ ID do Recrutador (obrigatório)\n\n"
                f"📋 Pedidos vão para: {canal.mention}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_image(url="https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png")
        
        await ctx.send(embed=embed, view=SetOpenView())
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(SetsCog(bot))
