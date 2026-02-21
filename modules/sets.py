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

# ========== VIEW DO STAFF ==========
class SetStaffView(ui.View):
    def __init__(self, fivem_id, game_nick, user_id, discord_user, recrutador_id=None, recrutador_nome=None):
        super().__init__(timeout=None)
        self.fivem_id_value = fivem_id  # ← MUDADO PARA self.fivem_id_value
        self.game_nick = game_nick
        self.user_id = user_id
        self.discord_user = discord_user
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
    
    @ui.button(label="✅ Aprovar Set", style=ButtonStyle.green, custom_id="aprovar_set_btn", row=0)
    async def aprovar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            member = interaction.guild.get_member(self.user_id)
            if not member:
                await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            # Mudar nickname
            novo_nick = f"M | {self.game_nick} | {self.fivem_id_value}"
            if len(novo_nick) > 32:
                novo_nick = f"M | {self.game_nick[:15]} | {self.fivem_id_value}"
            
            await member.edit(nick=novo_nick)
            
            # Dar cargo
            cargo = discord.utils.get(interaction.guild.roles, name="🙅‍♂️ | Membro") or discord.utils.get(interaction.guild.roles, name="Membro")
            if cargo:
                await member.add_roles(cargo)
            
            # Embed de aprovação
            embed = discord.Embed(
                title="✅ SET APROVADO!",
                description=(
                    f"**👤 Discord:** {member.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id_value}`\n"
                    f"**👤 Nick:** `{self.game_nick}`\n"
                    f"**👑 Aprovado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    f"\n✅ **Nickname:** `{novo_nick}`\n"
                    f"✅ **Cargo:** 🙅‍♂️ | Membro"
                ),
                color=discord.Color.green()
            )
            
            if self.recrutador_nome:
                embed.description += f"\n✅ **Recrutador:** {self.recrutador_nome}"
            
            # Remover botões
            self.clear_items()
            await interaction.message.edit(embed=embed, view=self)
            
            await interaction.followup.send(f"✅ Set de {member.mention} aprovado!", ephemeral=True)
            
            # DM
            try:
                await member.send(f"✅ Seu set foi aprovado! Agora você é **{novo_nick}**")
            except:
                pass
                
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    @ui.button(label="❌ Recusar Set", style=ButtonStyle.red, custom_id="recusar_set_btn", row=0)
    async def recusar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            embed = discord.Embed(
                title="❌ SET RECUSADO",
                description=(
                    f"**👤 Discord:** {self.discord_user.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id_value}`\n"
                    f"**👤 Nick:** `{self.game_nick}`\n"
                    f"**👑 Recusado por:** {interaction.user.mention}"
                ),
                color=discord.Color.red()
            )
            
            await interaction.channel.send(embed=embed)
            await interaction.message.delete()
            await interaction.followup.send("✅ Set recusado!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== MODAL DO FORMULÁRIO ==========
class SetForm(ui.Modal, title="📝 Pedido de Set"):
    nick = ui.TextInput(
        label="1. Seu Nick no Jogo:",
        placeholder="Ex: João Silva",
        required=True,
        max_length=32
    )
    
    id_fivem = ui.TextInput(
        label="2. Seu ID do FiveM:",
        placeholder="Ex: 123456",
        required=True,
        max_length=20
    )
    
    recrutador = ui.TextInput(
        label="3. ID de quem te recrutou:",
        placeholder="Ex: 9237 (opcional)",
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validar ID do FiveM
            if not self.id_fivem.value.isdigit():
                await interaction.followup.send("❌ ID do FiveM deve conter apenas números!", ephemeral=True)
                return
            
            # Verificar canal de aprovação
            canal_id = canais_aprovacao.get(interaction.guild.id)
            if not canal_id:
                await interaction.followup.send("❌ Canal de aprovação não configurado! Use `!aprovamento #canal`", ephemeral=True)
                return
            
            canal = interaction.guild.get_channel(canal_id)
            if not canal:
                await interaction.followup.send("❌ Canal de aprovação não encontrado!", ephemeral=True)
                return
            
            # Verificar se ID já existe
            async for msg in canal.history(limit=200):
                if msg.embeds and f"**🎮 ID Fivem:** `{self.id_fivem.value}`" in (msg.embeds[0].description or ""):
                    await interaction.followup.send(f"❌ ID `{self.id_fivem.value}` já em uso!", ephemeral=True)
                    return
            
            # Processar recrutador
            recrutador_nome = None
            recrutador_member = None
            
            if self.recrutador.value and self.recrutador.value.strip():
                if not self.recrutador.value.isdigit():
                    await interaction.followup.send("❌ ID do recrutador deve conter apenas números!", ephemeral=True)
                    return
                
                recrutador_member = buscar_usuario_por_id_fivem(interaction.guild, self.recrutador.value)
                if recrutador_member:
                    recrutador_nome = recrutador_member.nick or recrutador_member.name
                else:
                    recrutador_nome = f"ID: {self.recrutador.value}"
            
            # Criar embed
            desc = (
                f"**👤 Discord:** {interaction.user.mention}\n"
                f"**🆔 Discord ID:** `{interaction.user.id}`\n"
                f"**🎮 ID Fivem:** `{self.id_fivem.value}`\n"
                f"**👤 Nick:** `{self.nick.value}`\n"
                f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            )
            
            if recrutador_nome:
                desc += f"\n**🤝 Recrutado por:** {recrutador_nome}"
                if recrutador_member:
                    desc += f" ({recrutador_member.mention})"
            
            desc += "\n\n**⏳ Status:** Aguardando aprovação"
            
            embed = discord.Embed(
                title="🎮 NOVO PEDIDO DE SET",
                description=desc,
                color=discord.Color.purple()
            )
            
            # Enviar para aprovação
            view = SetStaffView(
                self.id_fivem.value,
                self.nick.value,
                interaction.user.id,
                interaction.user,
                self.recrutador.value if self.recrutador.value else None,
                recrutador_nome
            )
            
            await canal.send(embed=embed, view=view)
            
            await interaction.followup.send(
                f"✅ **Pedido enviado!**\n• ID: `{self.id_fivem.value}`\n• Nick: `{self.nick.value}`",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== VIEW PRINCIPAL ==========
class SetOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Peça seu Set!", style=ButtonStyle.primary, custom_id="pedir_set_btn")
    async def pedir_set(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SetForm())

# ========== COG PRINCIPAL ==========
class SetsCog(commands.Cog, name="Sets"):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Sets carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(SetOpenView())
        print("✅ Views do Sets registradas!")
    
    @commands.command(name="aprovamento", aliases=["aprov", "setcanal"])
    @commands.has_permissions(administrator=True)
    async def set_canal(self, ctx, canal: discord.TextChannel = None):
        if not canal:
            canal = ctx.channel
        
        canais_aprovacao[ctx.guild.id] = canal.id
        
        embed = discord.Embed(
            title="✅ Canal Definido",
            description=f"Pedidos de set vão para: {canal.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="setup_set", aliases=["setupset"])
    @commands.has_permissions(administrator=True)
    async def setup_set(self, ctx):
        if ctx.guild.id not in canais_aprovacao:
            await ctx.send("⚠️ Use `!aprovamento #canal` primeiro!")
            return
        
        canal = ctx.guild.get_channel(canais_aprovacao[ctx.guild.id])
        
        embed = discord.Embed(
            title="🎮 PEÇA SEU SET AQUI!",
            description=(
                "Clique no botão abaixo e preencha:\n\n"
                "1️⃣ **Nick do Jogo**\n"
                "2️⃣ **ID do FiveM**\n"
                "3️⃣ **ID do Recrutador** (opcional)\n\n"
                f"📌 **Pedidos vão para:** {canal.mention}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_image(url="https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png")
        
        await ctx.send(embed=embed, view=SetOpenView())
        await ctx.message.delete()
    
    @commands.command(name="check_id")
    async def check_id(self, ctx, id_fivem: str):
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if not canal_id:
            await ctx.send("❌ Use `!aprovamento` primeiro!")
            return
        
        canal = ctx.guild.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal não encontrado!")
            return
        
        if not id_fivem.isdigit():
            await ctx.send("❌ ID deve conter apenas números!")
            return
        
        encontrado = False
        async for msg in canal.history(limit=200):
            if msg.embeds and f"**🎮 ID Fivem:** `{id_fivem}`" in (msg.embeds[0].description or ""):
                await ctx.send(f"❌ ID `{id_fivem}` já em uso! [Ver]({msg.jump_url})")
                encontrado = True
                break
        
        if not encontrado:
            await ctx.send(f"✅ ID `{id_fivem}` disponível!")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(SetsCog(bot))
    bot.add_view(SetOpenView())
    print("✅ Sets configurado com views persistentes!")
