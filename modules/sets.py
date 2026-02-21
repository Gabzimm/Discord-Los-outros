import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
CARGO_BASE_APROVACAO_ID = 1421254143103996045

# Dicionário para armazenar o canal de aprovação de cada servidor
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

# ========== CLASSES DO SISTEMA DE SET ==========

class SetStaffView(ui.View):
    def __init__(self, fivem_id, game_nick, user_id, discord_user, recrutador_id=None, recrutador_nome=None):
        super().__init__(timeout=None)
        self.fivem_id = fivem_id
        self.game_nick = game_nick
        self.user_id = user_id
        self.discord_user = discord_user
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
    
    @ui.button(label="✅ Aprovar Set", style=ButtonStyle.green, custom_id="aprovar_set", row=0)
    async def aprovar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para aprovar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            member = interaction.guild.get_member(self.user_id)
            if not member:
                await interaction.followup.send(f"❌ Usuário não encontrado! ID: `{self.user_id}`", ephemeral=True)
                return
            
            novo_nick = f"M | {self.game_nick} | {self.fivem_id}"
            if len(novo_nick) > 32:
                nome_curto = self.game_nick[:15]
                novo_nick = f"M | {nome_curto} | {self.fivem_id}"
            
            await member.edit(nick=novo_nick)
            print(f"✅ Nickname alterado para: {novo_nick}")
            
            membro_role = discord.utils.get(interaction.guild.roles, name="🙅‍♂️ | Membro")
            if not membro_role:
                membro_role = discord.utils.get(interaction.guild.roles, name="Membro")
            
            if membro_role:
                await member.add_roles(membro_role)
                print(f"✅ Cargo '🙅‍♂️ | Membro' adicionado a {member.name}")
            
            embed_aprovado = discord.Embed(
                title="✅ SET APROVADO!",
                description=(
                    f"**👤 Discord:** {member.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Aprovado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                ),
                color=discord.Color.green()
            )
            
            if self.recrutador_nome and self.recrutador_id:
                embed_aprovado.description += f"**🤝 Recrutado por:** {self.recrutador_nome} (ID: `{self.recrutador_id}`)\n"
                interaction.client.dispatch('recrutamento_contabilizar', {
                    'recrutador_id': self.recrutador_id,
                    'recrutador_nome': self.recrutador_nome,
                    'recrutado_id': self.user_id,
                    'recrutado_nome': member.name,
                    'data': datetime.now().isoformat()
                })
            
            embed_aprovado.description += f"\n✅ **Novo formato:** `{novo_nick}`\n✅ **Cargo:** 🙅‍♂️ | Membro"
            
            self.clear_items()
            await interaction.message.edit(embed=embed_aprovado, view=self)
            
            await interaction.followup.send(
                f"✅ Set de {member.mention} aprovado!\n"
                f"• Nickname: `{novo_nick}`\n"
                f"• Cargo: 🙅‍♂️ | Membro",
                ephemeral=True
            )
            
            try:
                embed_dm = discord.Embed(
                    title="✅ SEU SET FOI APROVADO!",
                    description=(
                        f"Parabéns! Seu pedido de set foi aprovado por {interaction.user.mention}\n\n"
                        f"**📋 Detalhes:**\n"
                        f"• **Nickname:** `{novo_nick}`\n"
                        f"• **ID Fivem:** `{self.fivem_id}`\n"
                        f"• **Cargo:** 🙅‍♂️ | Membro\n\n"
                        f"🎮 Bem-vindo ao servidor!"
                    ),
                    color=discord.Color.green()
                )
                if self.recrutador_nome:
                    embed_dm.description += f"\n🤝 **Recrutado por:** {self.recrutador_nome}"
                await member.send(embed=embed_dm)
            except:
                pass
                
        except Exception as e:
            print(f"❌ Erro ao aprovar set: {type(e).__name__}: {e}")
            await interaction.followup.send(f"❌ Erro: {type(e).__name__}: {e}", ephemeral=True)
    
    @ui.button(label="❌ Recusar Set", style=ButtonStyle.red, custom_id="recusar_set", row=0)
    async def recusar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para recusar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            mensagem_pedido = interaction.message
            
            embed_recusado = discord.Embed(
                title="❌ SET RECUSADO",
                description=(
                    f"**👤 Discord:** {self.discord_user.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Recusado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ),
                color=discord.Color.red()
            )
            
            if self.recrutador_nome:
                embed_recusado.description += f"\n**🤝 Recrutado por:** {self.recrutador_nome}"
            
            await interaction.channel.send(embed=embed_recusado)
            await mensagem_pedido.delete()
            await interaction.followup.send("✅ Set recusado e mensagem excluída!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class SetForm(ui.Modal, title="📝 Pedido de Set"):
    game_nick = ui.TextInput(
        label="1. Seu Nick no Jogo:",
        placeholder="Ex: João Silva",
        style=discord.TextStyle.short,
        required=True,
        max_length=32
    )
    
    fivem_id = ui.TextInput(
        label="2. Seu ID do FiveM:",
        placeholder="Ex: 123456",
        style=discord.TextStyle.short,
        required=True,
        max_length=20
    )
    
    recrutador_id = ui.TextInput(
        label="3. ID de quem te recrutou:",
        placeholder="Ex: 9237 (ID do FiveM do recrutador)",
        style=discord.TextStyle.short,
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            if not self.fivem_id.value.isdigit():
                error_msg = await interaction.followup.send("❌ ID do FiveM deve conter apenas números!", ephemeral=True)
                await asyncio.sleep(5)
                await error_msg.delete()
                return
            
            if not re.match(r'^[a-zA-Z0-9 _\-\.]+$', self.game_nick.value):
                error_msg = await interaction.followup.send("❌ Nick inválido!", ephemeral=True)
                await asyncio.sleep(5)
                await error_msg.delete()
                return
            
            recrutador_nome = None
            recrutador_member = None
            recrutador_fivem_id = None
            
            if self.recrutador_id.value and self.recrutador_id.value.strip():
                recrutador_fivem_id = self.recrutador_id.value.strip()
                
                if not recrutador_fivem_id.isdigit():
                    error_msg = await interaction.followup.send("❌ ID do recrutador deve conter apenas números!", ephemeral=True)
                    await asyncio.sleep(5)
                    await error_msg.delete()
                    return
                
                recrutador_member = buscar_usuario_por_id_fivem(interaction.guild, recrutador_fivem_id)
                
                if recrutador_member:
                    if recrutador_member.nick:
                        nome_parts = recrutador_member.nick.split(' | ')
                        recrutador_nome = nome_parts[1].strip() if len(nome_parts) >= 2 else recrutador_member.nick
                    else:
                        recrutador_nome = recrutador_member.name
                else:
                    recrutador_nome = f"ID: {recrutador_fivem_id}"
            
            canal_id = canais_aprovacao.get(interaction.guild.id)
            if not canal_id:
                await interaction.followup.send(
                    "❌ Canal de aprovação não configurado!\n"
                    "Um administrador precisa usar `!aprovamento #canal` primeiro.",
                    ephemeral=True
                )
                return
            
            canal_aprovamento = interaction.guild.get_channel(canal_id)
            if not canal_aprovamento:
                await interaction.followup.send("❌ Canal de aprovação não encontrado!", ephemeral=True)
                return
            
            async for message in canal_aprovamento.history(limit=200):
                if message.embeds and f"**🎮 ID Fivem:** `{self.fivem_id.value}`" in (message.embeds[0].description or ""):
                    await interaction.followup.send(f"❌ ID `{self.fivem_id.value}` já está em uso!", ephemeral=True)
                    return
            
            descricao = (
                f"**👤 Discord:** {interaction.user.mention}\n"
                f"**🆔 Discord ID:** `{interaction.user.id}`\n"
                f"**🎮 ID Fivem:** `{self.fivem_id.value}`\n"
                f"**👤 Nick do Jogo:** `{self.game_nick.value}`\n"
                f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            )
            
            if recrutador_nome:
                descricao += f"\n**🤝 Recrutado por:** {recrutador_nome}"
                if recrutador_member:
                    descricao += f" ({recrutador_member.mention})"
                descricao += f"\n**🔍 ID Recrutador:** `{recrutador_fivem_id}`"
            
            descricao += "\n\n**⏳ Status:** Aguardando aprovação"
            
            embed = discord.Embed(
                title="🎮 NOVO PEDIDO DE SET",
                description=descricao,
                color=discord.Color.purple()
            )
            
            view = SetStaffView(
                self.fivem_id.value, 
                self.game_nick.value, 
                interaction.user.id, 
                interaction.user,
                recrutador_fivem_id,
                recrutador_nome
            )
            
            await canal_aprovamento.send(embed=embed, view=view)
            
            success_msg = await interaction.followup.send(
                f"✅ **Pedido enviado!**\n"
                f"• ID: `{self.fivem_id.value}`\n"
                f"• Nick: `{self.game_nick.value}`\n"
                f"{f'• Recrutador: {recrutador_nome}' if recrutador_nome else ''}",
                ephemeral=True
            )
            await asyncio.sleep(10)
            await success_msg.delete()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class SetOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Peça seu Set!", style=ButtonStyle.primary, custom_id="pedir_set")
    async def pedir_set(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetForm()
        await interaction.response.send_modal(modal)

class SetsCog(commands.Cog, name="Sets"):
    """📋 Sistema de Sets e Recrutamentos"""
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Sets carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(SetOpenView())
        print("✅ Views de Sets registradas!")
    
    @commands.command(name="setup_set", aliases=["setupset"])
    @commands.has_permissions(administrator=True)
    async def setup_set(self, ctx):
        if ctx.guild.id not in canais_aprovacao:
            embed_aviso = discord.Embed(
                title="⚠️ Configure o Canal de Aprovação Primeiro!",
                description="Use o comando `!aprovamento #canal` para definir onde os pedidos serão enviados.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed_aviso)
            return
        
        canal = ctx.guild.get_channel(canais_aprovacao[ctx.guild.id])
        
        embed = discord.Embed(
            title="🎮 **PEÇA SEU SET AQUI!**",
            description=(
                "Clique no botão abaixo e preencha os dados:\n\n"
                "1️⃣ **Nick do Jogo**\n"
                "2️⃣ **ID do FiveM**\n"
                "3️⃣ **ID do Recrutador**\n\n"
                f"**📋 Pedidos vão para:** {canal.mention}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_image(url="https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png")
        
        view = SetOpenView()
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="aprovamento", aliases=["aprov"])
    @commands.has_permissions(administrator=True)
    async def set_aprovamento(self, ctx, canal: discord.TextChannel = None):
        if not canal:
            canal = ctx.channel
        
        canais_aprovacao[ctx.guild.id] = canal.id
        
        embed = discord.Embed(
            title="✅ Canal de Aprovação Definido",
            description=f"Os pedidos de set agora serão enviados para: {canal.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="check_id")
    async def check_id(self, ctx, *, fivem_id: str):
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if not canal_id:
            await ctx.send("❌ Use `!aprovamento #canal` primeiro.")
            return
        
        canal = ctx.guild.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal não encontrado!")
            return
        
        if not fivem_id.isdigit():
            await ctx.send("❌ ID deve conter apenas números!")
            return
        
        encontrado = False
        async for message in canal.history(limit=200):
            if message.embeds and f"**🎮 ID Fivem:** `{fivem_id}`" in (message.embeds[0].description or ""):
                await ctx.send(f"❌ ID `{fivem_id}` já em uso! [Ver pedido]({message.jump_url})")
                encontrado = True
                break
        
        if not encontrado:
            await ctx.send(f"✅ ID `{fivem_id}` não está em uso!")

async def setup(bot):
    await bot.add_cog(SetsCog(bot))
    bot.add_view(SetOpenView())
    print("✅ Sistema de Sets configurado!")
