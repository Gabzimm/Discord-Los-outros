import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
# ID do cargo base (deste para cima podem ver o painel)
CARGO_BASE_ID = 1393998691354018094  # Substitua pelo ID do seu cargo

# ========== FUNÇÕES AUXILIARES ==========
def usuario_pode_ver_painel(member: discord.Member) -> bool:
    """Verifica se o usuário pode ver o painel de controle baseado no cargo"""
    if not member:
        return False
    
    # Staff sempre pode (dono, adm, etc)
    if member.guild_permissions.administrator:
        return True
    
    # Buscar o cargo base
    cargo_base = member.guild.get_role(CARGO_BASE_ID)
    if not cargo_base:
        print(f"⚠️ Cargo base ID {CARGO_BASE_ID} não encontrado!")
        return False
    
    # Verificar se o membro tem algum cargo com posição >= cargo_base
    for role in member.roles:
        if role.position >= cargo_base.position:
            return True
    
    return False

def get_cargos_acima_base(guild: discord.Guild) -> list:
    """Retorna lista de cargos com posição >= cargo base"""
    cargo_base = guild.get_role(CARGO_BASE_ID)
    if not cargo_base:
        return []
    
    cargos_permitidos = []
    for role in guild.roles:
        if role.position >= cargo_base.position:
            cargos_permitidos.append(role)
    
    return sorted(cargos_permitidos, key=lambda r: r.position, reverse=True)

# ========== CLASSES PRINCIPAIS ==========

class TicketFinalizadoView(ui.View):
    """View após ticket fechado - APENAS QUEM PODE VER PAINEL"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    @ui.button(label="✅ Finalizar Ticket", style=ButtonStyle.green, custom_id="finalizar_ticket")
    async def finalizar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem pode ver o painel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🏁 Ticket Finalizado",
            description=f"Ticket finalizado por {interaction.user.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        await self.ticket_channel.send(embed=embed)
    
    @ui.button(label="🔄 Reabrir Ticket", style=ButtonStyle.blurple, custom_id="reabrir_ticket")
    async def reabrir_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem pode ver o painel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = True
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        if self.ticket_channel.name.startswith("🔒-"):
            novo_nome = f"🎫-{self.ticket_channel.name[2:]}"
            await self.ticket_channel.edit(name=novo_nome)
        
        embed_reaberto = discord.Embed(
            title="🔄 Ticket Reaberto",
            description=f"Ticket reaberto por {interaction.user.mention}",
            color=discord.Color.blue()
        )
        
        reaberto_view = TicketReabertoView(self.ticket_owner_id, self.ticket_channel)
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        await self.ticket_channel.send(embed=embed_reaberto)
        await self.ticket_channel.send("**Painel de Controle:**", view=reaberto_view)

class TicketReabertoView(ui.View):
    """View quando ticket é reaberto - com Deletar e Fechar"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", custom_id="close_ticket_reaberto", row=0)
    async def close_ticket_reaberto(self, interaction: discord.Interaction, button: ui.Button):
        # Dono do ticket pode fechar, ou quem pode ver painel
        if interaction.user.id != self.ticket_owner_id and not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem abriu ou quem pode ver o painel pode fechar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.ticket_channel.edit(overwrites=overwrites)
        if not self.ticket_channel.name.startswith("🔒-"):
            await self.ticket_channel.edit(name=f"🔒-{self.ticket_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            user_info = f"{user.mention}\nID: `{user.id}`"
        except:
            user_info = f"ID: `{self.ticket_owner_id}`"
        
        embed_fechado = discord.Embed(
            title="📋 Ticket Fechado",
            description=(
                f"**👤 Usuário:** {user_info}\n"
                f"**👑 Fechado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.ticket_channel.send(embed=embed_fechado)
        await self.ticket_channel.send("**Painel de Controle (apenas quem pode ver):**", view=TicketFinalizadoView(self.ticket_owner_id, self.ticket_channel))
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", custom_id="delete_ticket_reaberto", row=0)
    async def delete_ticket_reaberto(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem pode ver o painel pode deletar tickets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🗑️ Ticket Deletado",
            description=f"Ticket deletado por {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await self.ticket_channel.send(embed=embed)
        
        await asyncio.sleep(3)
        await self.ticket_channel.delete()
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            await user.send("🗑️ Seu ticket foi deletado pela equipe de suporte.")
        except:
            pass

class TicketStaffView(ui.View):
    """View inicial do ticket aberto - com Deletar e Fechar"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", custom_id="close_ticket_staff", row=0)
    async def close_ticket_staff(self, interaction: discord.Interaction, button: ui.Button):
        # Dono do ticket pode fechar, ou quem pode ver painel
        if interaction.user.id != self.ticket_owner_id and not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem abriu ou quem pode ver o painel pode fechar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.ticket_channel.edit(overwrites=overwrites)
        if not self.ticket_channel.name.startswith("🔒-"):
            await self.ticket_channel.edit(name=f"🔒-{self.ticket_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            user_info = f"{user.mention}\nID: `{user.id}`"
        except:
            user_info = f"ID: `{self.ticket_owner_id}`"
        
        embed_fechado = discord.Embed(
            title="📋 Ticket Fechado",
            description=(
                f"**👤 Usuário:** {user_info}\n"
                f"**👑 Fechado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.ticket_channel.send(embed=embed_fechado)
        await self.ticket_channel.send("**Painel de Controle (apenas quem pode ver):**", view=TicketFinalizadoView(self.ticket_owner_id, self.ticket_channel))
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", custom_id="delete_ticket_staff", row=0)
    async def delete_ticket_staff(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_ver_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas quem pode ver o painel pode deletar tickets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🗑️ Ticket Deletado",
            description=f"Ticket deletado por {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await self.ticket_channel.send(embed=embed)
        
        await asyncio.sleep(3)
        await self.ticket_channel.delete()
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            await user.send("🗑️ Seu ticket foi deletado pela equipe de suporte.")
        except:
            pass

class TicketOpenView(ui.View):
    """View inicial - apenas botão para abrir ticket"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Abrir Ticket", style=ButtonStyle.primary, emoji="🎫", custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        print(f"[TICKET] Iniciando criação de ticket para {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 1. VERIFICAÇÃO DO CANAL BASE
            canal_ticket_base = None
            
            for channel in interaction.guild.text_channels:
                channel_lower = channel.name.lower()
                if "ticket" in channel_lower or "𝐓𝐢𝐜𝐤𝐞𝐭" in channel.name:
                    canal_ticket_base = channel
                    print(f"[TICKET] Canal base encontrado: {channel.name}")
                    break
            
            if not canal_ticket_base:
                print("[TICKET] Nenhum canal com 'ticket' encontrado")
                await interaction.followup.send(
                    "❌ Nenhum canal com 'ticket' no nome foi encontrado!",
                    ephemeral=True
                )
                return
            
            # 2. VERIFICAR CATEGORIA
            categoria = canal_ticket_base.category
            
            if not categoria:
                categoria = interaction.channel.category
            
            if not categoria:
                print("[TICKET] Nenhuma categoria disponível")
                await interaction.followup.send(
                    "❌ Não foi possível determinar a categoria para o ticket!",
                    ephemeral=True
                )
                return
            
            print(f"[TICKET] Categoria: {categoria.name}")
            
            # 3. VERIFICAR TICKETS EXISTENTES
            tickets_abertos = []
            for channel in categoria.channels:
                if isinstance(channel, discord.TextChannel):
                    if channel.topic and str(interaction.user.id) in channel.topic:
                        tickets_abertos.append(channel)
                        print(f"[TICKET] Ticket já aberto: {channel.name}")
            
            if tickets_abertos:
                await interaction.followup.send(
                    f"❌ Você já tem um ticket aberto: {tickets_abertos[0].mention}",
                    ephemeral=True
                )
                return
            
            # 4. CONFIGURAR PERMISSÕES
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False
                ),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
            
            # 5. ADICIONAR CARGOS QUE PODEM VER O PAINEL (baseado no ID base)
            cargos_permitidos = get_cargos_acima_base(interaction.guild)
            for role in cargos_permitidos:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True
                )
                print(f"[TICKET] Cargo adicionado: {role.name} (posição: {role.position})")
            
            # 6. CRIAR CANAL
            nome_usuario = interaction.user.display_name
            nome_limpo = ''.join(c for c in nome_usuario if c.isalnum() or c in [' ', '-', '_'])
            nome_limpo = nome_limpo.strip()
            
            if not nome_limpo:
                nome_limpo = f"user{interaction.user.id}"
            
            nome_canal = f"🎫-{nome_limpo[:20]}"
            print(f"[TICKET] Criando canal: {nome_canal}")
            
            ticket_channel = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user.name} | ID: {interaction.user.id}",
                reason=f"Ticket criado por {interaction.user.name}"
            )
            
            print(f"[TICKET] Canal criado: {ticket_channel.name}")
            
            # 7. ENVIAR MENSAGENS NO TICKET
            embed = discord.Embed(
                title=f"🎫 Ticket de {interaction.user.display_name}",
                description=(
                    f"**👤 Aberto por:** {interaction.user.mention}\n"
                    f"**🆔 ID:** `{interaction.user.id}`\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    "**📝 Descreva seu problema ou dúvida abaixo:**"
                ),
                color=discord.Color.purple()
            )
            
            staff_view = TicketStaffView(interaction.user.id, ticket_channel)
            
            await ticket_channel.send(
                content=f"## 👋 Olá {interaction.user.mention}!\nSeu ticket foi criado com sucesso.",
                embed=embed
            )
            
            await ticket_channel.send("**🔧 Painel de Controle:**", view=staff_view)
            
            # 8. CONFIRMAR PARA O USUÁRIO
            await interaction.followup.send(
                f"✅ **Ticket criado com sucesso!**\nAcesse: {ticket_channel.mention}",
                ephemeral=True
            )
            
            print(f"[TICKET] Ticket criado com SUCESSO para {interaction.user.name}")
            
        except discord.Forbidden:
            print("[ERRO] Permissão negada")
            await interaction.followup.send(
                "❌ **Erro de permissão!**",
                ephemeral=True
            )
            
        except discord.HTTPException as e:
            print(f"[ERRO] HTTP {e.status}")
            await interaction.followup.send(
                f"❌ **Erro do Discord:** Tente novamente.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"[ERRO] {type(e).__name__}: {e}")
            await interaction.followup.send(
                f"❌ **Erro:** `{type(e).__name__}`",
                ephemeral=True
            )

# ========== COMANDOS ==========

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Tickets carregado!")
    
    @commands.command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Configura o painel de tickets"""
        print(f"[SETUP] Configurando painel por {ctx.author.name}")
        
        # Verificar se o cargo base existe
        cargo_base = ctx.guild.get_role(CARGO_BASE_ID)
        if not cargo_base:
            await ctx.send(f"⚠️ **Cargo base não encontrado!**\nID: `{CARGO_BASE_ID}`\nVerifique se o ID está correto.")
            return
        
        # Listar cargos que terão acesso
        cargos_permitidos = get_cargos_acima_base(ctx.guild)
        
        embed_info = discord.Embed(
            title="🎫 **SISTEMA DE TICKETS**",
            description=(
                "**Clique no botão abaixo para abrir um ticket**\n\n"
                "Escolha esta opção se você precisa de ajuda com:\n"
                "• Duvidas privadas\n"
                "• Entrga de farm\n"
                "• Reportar jogadores\n"
                "• Outras questões importante"
            ),
            color=discord.Color.purple()
        )
        
        embed_info.set_image(url="")
        embed_info.set_footer(text="Sistema de ticket • WaveX")
        
        view = TicketOpenView()
        
        await ctx.send(embed=embed_info, view=view)
        await ctx.message.delete()
        
        print(f"[SETUP] Painel configurado em #{ctx.channel.name}")
    
    @commands.command(name="verificar_acesso")
    @commands.has_permissions(administrator=True)
    async def verificar_acesso(self, ctx, member: discord.Member = None):
        """Verifica se um membro pode ver o painel"""
        if member is None:
            member = ctx.author
        
        pode_ver = usuario_pode_ver_painel(member)
        
        cargo_base = ctx.guild.get_role(CARGO_BASE_ID)
        
        embed = discord.Embed(
            title="🔍 Verificação de Acesso",
            color=discord.Color.green() if pode_ver else discord.Color.red()
        )
        
        embed.add_field(name="👤 Usuário", value=member.mention, inline=True)
        embed.add_field(name="✅ Pode ver painel?", value="SIM" if pode_ver else "NÃO", inline=True)
        
        if cargo_base:
            embed.add_field(name="🎯 Cargo Base", value=f"{cargo_base.mention}\nPosição: {cargo_base.position}", inline=True)
            
            # Listar cargos do usuário com posição
            cargos_acima = []
            for role in member.roles:
                if role.position >= cargo_base.position and role.name != "@everyone":
                    cargos_acima.append(f"{role.name} (pos: {role.position})")
            
            if cargos_acima:
                embed.add_field(
                    name="📋 Cargos com acesso",
                    value="\n".join(cargos_acima[:5]),
                    inline=False
                )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    # Registrar view persistente
    bot.add_view(TicketOpenView())
    print("✅ Sistema de Tickets configurado com views persistentes!")
