import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
CARGO_BASE_APROVACAO_ID = 1421254143103996045

# Dicionário compartilhado com main.py
# Será preenchido pelo comando !aprovamento
canais_aprovacao = {}

def usuario_pode_aprovar(member: discord.Member) -> bool:
    """Verifica se o usuário pode aprovar sets"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar cargo base
    cargo_base = member.guild.get_role(CARGO_BASE_APROVACAO_ID)
    if not cargo_base:
        return False
    
    # Verificar se tem cargo com posição >= cargo_base
    for role in member.roles:
        if role.position >= cargo_base.position:
            return True
    
    return False

def buscar_usuario_por_id_fivem(guild: discord.Guild, fivem_id: str) -> discord.Member:
    """Busca usuário pelo ID do FiveM no nickname"""
    for member in guild.members:
        if member.nick and member.nick.endswith(f" | {fivem_id}"):
            return member
    return None

# ========== VIEW DO STAFF ==========
class SetStaffView(ui.View):
    """View com botões para staff aprovar/recusar"""
    def __init__(self, fivem_id, game_nick, user_id, discord_user, recrutador_id=None, recrutador_nome=None):
        super().__init__(timeout=None)  # timeout=None é ESSENCIAL para persistência
        self.fivem_id = fivem_id
        self.game_nick = game_nick
        self.user_id = user_id
        self.discord_user = discord_user
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
    
    @ui.button(label="✅ Aprovar Set", style=ButtonStyle.green, custom_id="sets_aprovar_btn", row=0)
    async def aprovar_set(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar permissão
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para aprovar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Buscar membro
            member = interaction.guild.get_member(self.user_id)
            if not member:
                await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            # Criar novo nickname
            novo_nick = f"M | {self.game_nick} | {self.fivem_id}"
            if len(novo_nick) > 32:
                novo_nick = f"M | {self.game_nick[:15]} | {self.fivem_id}"
            
            # Mudar nickname
            await member.edit(nick=novo_nick)
            
            # Dar cargo de membro
            cargo_membro = discord.utils.get(interaction.guild.roles, name="🙅‍♂️ | Membro")
            if not cargo_membro:
                cargo_membro = discord.utils.get(interaction.guild.roles, name="Membro")
            
            if cargo_membro:
                await member.add_roles(cargo_membro)
            
            # Criar embed de aprovação
            embed = discord.Embed(
                title="✅ SET APROVADO!",
                description=(
                    f"**👤 Discord:** {member.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Aprovado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"✅ **Novo nickname:** `{novo_nick}`\n"
                    f"✅ **Cargo:** 🙅‍♂️ | Membro"
                ),
                color=discord.Color.green()
            )
            
            # Adicionar recrutador se existir
            if self.recrutador_nome:
                embed.description += f"\n✅ **Recrutado por:** {self.recrutador_nome}"
            
            # Remover botões
            self.clear_items()
            await interaction.message.edit(embed=embed, view=self)
            
            # Confirmar para o staff
            await interaction.followup.send(f"✅ Set de {member.mention} aprovado!", ephemeral=True)
            
            # Enviar DM para o usuário
            try:
                dm_embed = discord.Embed(
                    title="✅ SEU SET FOI APROVADO!",
                    description=(
                        f"Parabéns! Seu pedido de set foi aprovado!\n\n"
                        f"**📋 Detalhes:**\n"
                        f"• **Nickname:** `{novo_nick}`\n"
                        f"• **ID Fivem:** `{self.fivem_id}`\n"
                        f"• **Cargo:** 🙅‍♂️ | Membro"
                    ),
                    color=discord.Color.green()
                )
                await member.send(embed=dm_embed)
            except:
                pass
                
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    @ui.button(label="❌ Recusar Set", style=ButtonStyle.red, custom_id="sets_recusar_btn", row=0)
    async def recusar_set(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar permissão
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para recusar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Criar embed de recusa
            embed = discord.Embed(
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
                embed.description += f"\n**🤝 Recrutado por:** {self.recrutador_nome}"
            
            # Enviar embed e deletar mensagem original
            await interaction.channel.send(embed=embed)
            await interaction.message.delete()
            
            # Confirmar para o staff
            await interaction.followup.send("✅ Set recusado!", ephemeral=True)
            
            # Avisar o usuário
            try:
                await self.discord_user.send(f"❌ Seu pedido de set (ID: `{self.fivem_id}`) foi recusado por {interaction.user.name}.")
            except:
                pass
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== FORMULÁRIO DE PEDIDO ==========
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
            
            # Validar nick (apenas letras, números e espaços)
            if not re.match(r'^[a-zA-Z0-9\s]+$', self.nick.value):
                await interaction.followup.send("❌ Nick inválido! Use apenas letras e números.", ephemeral=True)
                return
            
            # Verificar se canal de aprovação está configurado
            canal_id = canais_aprovacao.get(interaction.guild.id)
            if not canal_id:
                await interaction.followup.send(
                    "❌ Canal de aprovação não configurado!\n"
                    "Um administrador precisa usar `!aprovamento #canal` primeiro.",
                    ephemeral=True
                )
                return
            
            canal = interaction.guild.get_channel(canal_id)
            if not canal:
                await interaction.followup.send("❌ Canal de aprovação não encontrado!", ephemeral=True)
                return
            
            # Verificar se ID já existe
            async for message in canal.history(limit=200):
                if message.embeds:
                    for embed in message.embeds:
                        if embed.description and f"**🎮 ID Fivem:** `{self.id_fivem.value}`" in embed.description:
                            await interaction.followup.send(f"❌ ID `{self.id_fivem.value}` já está em uso!", ephemeral=True)
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
                    # Extrair nome do nickname
                    if recrutador_member.nick:
                        partes = recrutador_member.nick.split(' | ')
                        recrutador_nome = partes[1] if len(partes) >= 2 else recrutador_member.nick
                    else:
                        recrutador_nome = recrutador_member.name
                else:
                    recrutador_nome = f"ID: {self.recrutador.value}"
            
            # Criar embed do pedido
            descricao = (
                f"**👤 Discord:** {interaction.user.mention}\n"
                f"**🆔 Discord ID:** `{interaction.user.id}`\n"
                f"**🎮 ID Fivem:** `{self.id_fivem.value}`\n"
                f"**👤 Nick do Jogo:** `{self.nick.value}`\n"
                f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            )
            
            if recrutador_nome:
                descricao += f"\n**🤝 Recrutado por:** {recrutador_nome}"
                if recrutador_member:
                    descricao += f" ({recrutador_member.mention})"
            
            descricao += "\n\n**⏳ Status:** Aguardando aprovação"
            
            embed = discord.Embed(
                title="🎮 NOVO PEDIDO DE SET",
                description=descricao,
                color=discord.Color.purple()
            )
            
            # Criar view para staff
            view = SetStaffView(
                self.id_fivem.value,
                self.nick.value,
                interaction.user.id,
                interaction.user,
                self.recrutador.value if self.recrutador.value else None,
                recrutador_nome
            )
            
            # Enviar para o canal de aprovação
            await canal.send(embed=embed, view=view)
            
            # Confirmar para o usuário
            await interaction.followup.send(
                f"✅ **Pedido enviado!**\n"
                f"• ID: `{self.id_fivem.value}`\n"
                f"• Nick: `{self.nick.value}`\n"
                f"{f'• Recrutador: {recrutador_nome}' if recrutador_nome else ''}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== VIEW PRINCIPAL ==========
class SetOpenView(ui.View):
    """View com botão para abrir o formulário"""
    def __init__(self):
        super().__init__(timeout=None)  # timeout=None para persistência
    
    @ui.button(label="Peça seu Set!", style=ButtonStyle.primary, custom_id="sets_pedir_btn")
    async def pedir_set(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetForm()
        await interaction.response.send_modal(modal)

# ========== COG PRINCIPAL ==========
class SetsCog(commands.Cog, name="Sets"):
    """Sistema de Sets e Recrutamentos"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Sets carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Registra views persistentes quando o bot inicia"""
        # Registrar a view principal UMA ÚNICA VEZ
        self.bot.add_view(SetOpenView())
        print("✅ View do Sets registrada para persistência!")
    
    @commands.command(name="aprovamento", aliases=["aprov"])
    @commands.has_permissions(administrator=True)
    async def set_aprovamento(self, ctx, canal: discord.TextChannel = None):
        """📌 Define o canal onde os pedidos de set serão enviados"""
        if not canal:
            canal = ctx.channel
        
        # Salvar no dicionário global
        canais_aprovacao[ctx.guild.id] = canal.id
        
        embed = discord.Embed(
            title="✅ Canal de Aprovação Definido",
            description=f"Os pedidos de set agora serão enviados para: {canal.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        print(f"✅ Canal de aprovação definido: #{canal.name} em {ctx.guild.name}")
    
    @commands.command(name="setup_set", aliases=["setupset"])
    @commands.has_permissions(administrator=True)
    async def setup_set(self, ctx):
        """🎮 Configura o painel de pedido de set"""
        
        # Verificar se canal de aprovação está configurado
        if ctx.guild.id not in canais_aprovacao:
            embed_aviso = discord.Embed(
                title="⚠️ Configure o Canal de Aprovação Primeiro!",
                description=(
                    "Use o comando `!aprovamento #canal` para definir onde os pedidos serão enviados.\n\n"
                    "**Exemplo:**\n"
                    "`!aprovamento #𝐀𝐩𝐫𝐨𝐯𝐚𝐦𝐞𝐧𝐭𝐨`"
                ),
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed_aviso)
            return
        
        canal = ctx.guild.get_channel(canais_aprovacao[ctx.guild.id])
        
        embed = discord.Embed(
            title="🎮 **PEÇA SEU SET AQUI!**",
            description=(
                "Clique no botão abaixo e preencha os dados:\n\n"
                "**📝 Formulário:**\n"
                "1️⃣ **Nick do Jogo** - Seu nome no FiveM\n"
                "2️⃣ **ID do FiveM** - Seu identificador único\n"
                "3️⃣ **ID do Recrutador** - Quem te trouxe ao servidor (opcional)\n\n"
                f"**📋 Pedidos serão enviados para:** {canal.mention}"
            ),
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🤝 Como encontrar ID do Recrutador?",
            value="Procure no nickname da pessoa: `M | Nome | 123456`\nO número após o último '|' é o ID do FiveM",
            inline=False
        )
        
        embed.set_image(url="https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png")
        embed.set_footer(text="Sistema automático • WaveX")
        
        view = SetOpenView()
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="check_id", aliases=["checkid"])
    async def check_id(self, ctx, id_fivem: str):
        """🔍 Verifica se um ID Fivem já está em uso"""
        
        # Verificar se canal de aprovação está configurado
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if not canal_id:
            await ctx.send("❌ Canal de aprovação não configurado! Use `!aprovamento #canal` primeiro.")
            return
        
        canal = ctx.guild.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal de aprovação não encontrado!")
            return
        
        # Validar ID
        if not id_fivem.isdigit():
            await ctx.send("❌ ID deve conter apenas números!")
            return
        
        # Procurar ID nos pedidos
        encontrado = False
        async for message in canal.history(limit=200):
            if message.embeds:
                for embed in message.embeds:
                    if embed.description and f"**🎮 ID Fivem:** `{id_fivem}`" in embed.description:
                        await ctx.send(f"❌ ID `{id_fivem}` já está em uso! [Ver pedido]({message.jump_url})")
                        encontrado = True
                        break
            if encontrado:
                break
        
        if not encontrado:
            await ctx.send(f"✅ ID `{id_fivem}` está disponível!")
    
    @commands.command(name="sets_pendentes", aliases=["pendentes"])
    @commands.has_permissions(administrator=True)
    async def sets_pendentes(self, ctx):
        """📋 Mostra todos os pedidos pendentes"""
        
        # Verificar se canal de aprovação está configurado
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if not canal_id:
            await ctx.send("❌ Canal de aprovação não configurado! Use `!aprovamento #canal` primeiro.")
            return
        
        canal = ctx.guild.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal de aprovação não encontrado!")
            return
        
        # Buscar pedidos pendentes
        pedidos = []
        async for message in canal.history(limit=100):
            if message.embeds and "Aguardando aprovação" in (message.embeds[0].description or ""):
                pedidos.append(message)
        
        if not pedidos:
            await ctx.send("✅ Nenhum pedido pendente!")
            return
        
        embed = discord.Embed(
            title="📋 Pedidos Pendentes",
            description=f"Total: **{len(pedidos)}** pedidos\nCanal: {canal.mention}",
            color=discord.Color.blue()
        )
        
        for i, msg in enumerate(pedidos[:5], 1):
            desc = msg.embeds[0].description or ""
            
            # Extrair informações com regex
            id_match = re.search(r'\*\*🎮 ID Fivem:\*\* `([^`]+)`', desc)
            nick_match = re.search(r'\*\*👤 Nick do Jogo:\*\* `([^`]+)`', desc)
            recrutador_match = re.search(r'\*\*🤝 Recrutado por:\*\* ([^\n]+)', desc)
            
            valor = f"**ID:** `{id_match.group(1) if id_match else '?'}`\n**Nick:** `{nick_match.group(1) if nick_match else '?'}`"
            if recrutador_match:
                valor += f"\n**Recrutador:** {recrutador_match.group(1)}"
            
            embed.add_field(
                name=f"Pedido #{i}",
                value=valor + f"\n[Ver pedido]({msg.jump_url})",
                inline=False
            )
        
        if len(pedidos) > 5:
            embed.add_field(
                name="📊 Estatísticas",
                value=f"Mostrando 5 de {len(pedidos)} pedidos\nUse `!check_id [ID]` para verificar um ID específico",
                inline=False
            )
        
        await ctx.send(embed=embed)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(SetsCog(bot))
    # NÃO adicionar view aqui - já é adicionada no on_ready
    print("✅ Sistema de Sets configurado!")
