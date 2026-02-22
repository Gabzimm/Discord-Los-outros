import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
# Cargos de staff (mesmos do sistema de cargos)
STAFF_ROLES = [
    "👑 | Lider | 00",
    "💎 | Lider | 01",
    "👮 | Lider | 02",
    "🎖️ | Lider | 03",
    "🎖️ | Gerente Geral",
    "🎖️ | Gerente De Farm",
    "🎖️ | Gerente De Pista",
    "🎖️ | Gerente de Recrutamento",
    "🎖️ | Supervisor",
    "🎖️ | Recrutador",
    "🎖️ | Ceo Elite",
    "🎖️ | Sub Elite",
]

def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def usuario_e_staff(member: discord.Member) -> bool:
    """Verifica se o usuário TEM cargo de staff (pode ver painéis)"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo staff (com normalização)
    for role in member.roles:
        for cargo_staff in STAFF_ROLES:
            if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                return True
    
    return False

def get_cargos_staff(guild: discord.Guild) -> list:
    """Retorna lista de cargos de staff do servidor"""
    cargos_staff = []
    for role in guild.roles:
        for cargo_nome in STAFF_ROLES:
            if normalizar_nome(role.name) == normalizar_nome(cargo_nome):
                cargos_staff.append(role)
                break
    
    return sorted(cargos_staff, key=lambda r: r.position, reverse=True)

# ========== CLASSES PRINCIPAIS ==========

class GestorFinalizadoView(ui.View):
    """View após gestor fechado - APENAS STAFF PODE VER"""
    def __init__(self, gestor_owner_id, gestor_channel):
        super().__init__(timeout=None)
        self.gestor_owner_id = gestor_owner_id
        self.gestor_channel = gestor_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Apenas staff pode interagir"""
        if not usuario_e_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Apenas a staff pode interagir com gestores fechados!",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="✅ Reabrir Gestor", style=ButtonStyle.green, custom_id="staff_reabrir_gestor")
    async def reabrir_gestor(self, interaction: discord.Interaction, button: ui.Button):
        """Apenas staff pode reabrir"""
        await interaction.response.defer()
        
        overwrites = self.gestor_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = True
        
        await self.gestor_channel.edit(overwrites=overwrites)
        
        if self.gestor_channel.name.startswith("🔒-"):
            novo_nome = f"🎫-{self.gestor_channel.name[2:]}"
            await self.gestor_channel.edit(name=novo_nome)
        
        embed_reaberto = discord.Embed(
            title="🔄 Gestor Reaberto",
            description=f"Gestor reaberto por {interaction.user.mention}",
            color=discord.Color.blue()
        )
        
        # Criar views novamente
        staff_view = GestorStaffView(self.gestor_owner_id, self.gestor_channel)
        user_view = GestorUserView(self.gestor_owner_id, self.gestor_channel)
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        await self.gestor_channel.send(embed=embed_reaberto)
        await self.gestor_channel.send("**🔧 Painel da Staff:**", view=staff_view)
        await self.gestor_channel.send("**👤 Painel do Usuário:**", view=user_view)

class GestorUserView(ui.View):
    """View do usuário - APENAS FECHAR GESTOR"""
    def __init__(self, gestor_owner_id, gestor_channel):
        super().__init__(timeout=None)
        self.gestor_owner_id = gestor_owner_id
        self.gestor_channel = gestor_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se é o dono do gestor"""
        if interaction.user.id != self.gestor_owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu o gestor pode usar este painel!",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="🔒 Fechar Gestor", style=ButtonStyle.gray, emoji="🔒", custom_id="user_close_gestor")
    async def close_gestor(self, interaction: discord.Interaction, button: ui.Button):
        """Usuário pode fechar o próprio gestor"""
        await interaction.response.defer()
        
        # Fechar o gestor
        overwrites = self.gestor_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.gestor_channel.edit(overwrites=overwrites)
        if not self.gestor_channel.name.startswith("🔒-"):
            await self.gestor_channel.edit(name=f"🔒-{self.gestor_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        # Mensagem de fechamento
        embed_fechado = discord.Embed(
            title="🔒 Gestor de Farm Fechado",
            description=(
                f"**👤 Fechado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.gestor_channel.send(embed=embed_fechado)
        
        # Enviar painel da staff para reabrir
        await self.gestor_channel.send(
            "**🔧 Painel da Staff (reabrir gestor):**", 
            view=GestorFinalizadoView(self.gestor_owner_id, self.gestor_channel)
        )

class GestorStaffView(ui.View):
    """View da staff - FECHAR E DELETAR"""
    def __init__(self, gestor_owner_id, gestor_channel):
        super().__init__(timeout=None)
        self.gestor_owner_id = gestor_owner_id
        self.gestor_channel = gestor_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se é staff"""
        if not usuario_e_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Este painel é apenas para a staff!",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="🔒 Fechar Gestor", style=ButtonStyle.gray, emoji="🔒", custom_id="staff_close_gestor")
    async def close_gestor(self, interaction: discord.Interaction, button: ui.Button):
        """Staff pode fechar o gestor"""
        await interaction.response.defer()
        
        overwrites = self.gestor_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.gestor_channel.edit(overwrites=overwrites)
        if not self.gestor_channel.name.startswith("🔒-"):
            await self.gestor_channel.edit(name=f"🔒-{self.gestor_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        # Mensagem de fechamento
        embed_fechado = discord.Embed(
            title="🔒 Gestor de Farm Fechado",
            description=(
                f"**👑 Fechado por (Staff):** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.gestor_channel.send(embed=embed_fechado)
        await self.gestor_channel.send("**🔧 Painel da Staff (reabrir):**", view=GestorFinalizadoView(self.gestor_owner_id, self.gestor_channel))
    
    @ui.button(label="🗑️ Deletar Gestor", style=ButtonStyle.red, emoji="🗑️", custom_id="staff_delete_gestor")
    async def delete_gestor(self, interaction: discord.Interaction, button: ui.Button):
        """Staff pode deletar o gestor"""
        await interaction.response.defer()
        
        # Mensagem de deleção
        embed = discord.Embed(
            title="🗑️ Gestor de Farm Deletado",
            description=(
                f"**👑 Deletado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.red()
        )
        
        # Enviar mensagem no canal antes de deletar
        await self.gestor_channel.send(embed=embed)
        
        # Aguardar 3 segundos para a mensagem ser vista
        await asyncio.sleep(3)
        
        # Deletar o canal
        await self.gestor_channel.delete()

class GestorOpenView(ui.View):
    """View inicial - apenas botão para abrir gestor"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Abrir Gestor de Farm", style=ButtonStyle.primary, emoji="🎫", custom_id="open_gestor")
    async def open_gestor(self, interaction: discord.Interaction, button: ui.Button):
        print(f"[GESTOR] Iniciando criação de gestor para {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 1. VERIFICAÇÃO DO CANAL BASE (onde o !setup_tickets foi executado)
            # O canal base é onde o comando foi executado - ele define a categoria
            canal_base = interaction.channel
            categoria = canal_base.category
            
            if not categoria:
                print("[GESTOR] O canal base não está em uma categoria")
                await interaction.followup.send(
                    "❌ O canal onde o painel foi configurado precisa estar em uma categoria!",
                    ephemeral=True
                )
                return
            
            print(f"[GESTOR] Usando categoria: {categoria.name}")
            
            # 2. VERIFICAR GESTORES EXISTENTES DO USUÁRIO
            gestores_abertos = []
            for channel in categoria.channels:
                if isinstance(channel, discord.TextChannel):
                    if channel.topic and str(interaction.user.id) in channel.topic:
                        # Verificar se não está fechado (nome não começa com 🔒)
                        if not channel.name.startswith("🔒-"):
                            gestores_abertos.append(channel)
                            print(f"[GESTOR] Gestor já aberto: {channel.name}")
            
            if gestores_abertos:
                await interaction.followup.send(
                    f"❌ Você já tem um gestor aberto: {gestores_abertos[0].mention}",
                    ephemeral=True
                )
                return
            
            # 3. CONFIGURAR PERMISSÕES
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
            
            # 4. ADICIONAR CARGOS STAFF
            cargos_staff = get_cargos_staff(interaction.guild)
            for role in cargos_staff:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True
                )
                print(f"[GESTOR] Cargo staff adicionado: {role.name}")
            
            # 5. CRIAR CANAL
            nome_usuario = interaction.user.display_name
            nome_limpo = ''.join(c for c in nome_usuario if c.isalnum() or c in [' ', '-', '_'])
            nome_limpo = nome_limpo.strip()
            
            if not nome_limpo:
                nome_limpo = f"user{interaction.user.id}"
            
            nome_canal = f"🎫-{nome_limpo[:20]}"
            print(f"[GESTOR] Criando canal: {nome_canal}")
            
            gestor_channel = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,  # Usa a MESMA categoria do canal base
                overwrites=overwrites,
                topic=f"Gestor de {interaction.user.name} | ID: {interaction.user.id}",
                reason=f"Gestor criado por {interaction.user.name}"
            )
            
            print(f"[GESTOR] Canal criado: {gestor_channel.name}")
            
            # 6. ENVIAR MENSAGENS NO GESTOR
            embed = discord.Embed(
                title=f"🎫 Gestor de Farm - {interaction.user.display_name}",
                description=(
                    f"**👤 Aberto por:** {interaction.user.mention}\n"
                    f"**🆔 ID:** `{interaction.user.id}`\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    "**📝 Descreva seu problema ou dúvida abaixo:**"
                ),
                color=discord.Color.purple()
            )
            
            # Criar as views
            staff_view = GestorStaffView(interaction.user.id, gestor_channel)
            user_view = GestorUserView(interaction.user.id, gestor_channel)
            
            await gestor_channel.send(
                content=f"## 👋 Olá {interaction.user.mention}!\nSeu Gestor de Farm foi criado com sucesso.",
                embed=embed
            )
            
            # Enviar painéis
            await gestor_channel.send("**🔧 Painel da Staff:**", view=staff_view)
            await gestor_channel.send("**👤 Painel do Usuário:**", view=user_view)
            
            # 7. CONFIRMAR PARA O USUÁRIO
            await interaction.followup.send(
                f"✅ **Gestor criado com sucesso!**\nAcesse: {gestor_channel.mention}",
                ephemeral=True
            )
            
            print(f"[GESTOR] Gestor criado com SUCESSO para {interaction.user.name}")
            
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

class GestorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Gestor de Farm carregado!")
    
    @commands.command(name="setup_gestor", aliases=["setup_tickets"])
    @commands.has_permissions(administrator=True)
    async def setup_gestor(self, ctx):
        """Configura o painel do Gestor de Farm"""
        print(f"[SETUP] Configurando painel por {ctx.author.name}")
        
        embed_info = discord.Embed(
            title="🎫 **GESTOR DE FARM**",
            description=(
                "**Clique no botão abaixo para abrir um Gestor de Farm**\n\n"
                "Use este canal para:\n"
                "• Dúvidas sobre farm\n"
                "• Entrega de farm\n"
                "• Reportar problemas no farm\n"
                "• Outras questões relacionadas"
            ),
            color=discord.Color.purple()
        )
        
        embed_info.set_footer(text="Sistema de Gestor de Farm • WaveX")
        
        view = GestorOpenView()
        
        await ctx.send(embed=embed_info, view=view)
        await ctx.message.delete()
        
        print(f"[SETUP] Painel configurado em #{ctx.channel.name} (Categoria: {ctx.channel.category.name if ctx.channel.category else 'Nenhuma'})")
    
    @commands.command(name="verificar_acesso")
    @commands.has_permissions(administrator=True)
    async def verificar_acesso(self, ctx, member: discord.Member = None):
        """Verifica se um membro é staff"""
        if member is None:
            member = ctx.author
        
        e_staff = usuario_e_staff(member)
        
        embed = discord.Embed(
            title="🔍 Verificação de Acesso",
            color=discord.Color.green() if e_staff else discord.Color.red()
        )
        
        embed.add_field(name="👤 Usuário", value=member.mention, inline=True)
        embed.add_field(name="👑 É Staff?", value="SIM" if e_staff else "NÃO", inline=True)
        
        # Listar cargos de staff do usuário
        cargos_staff = []
        for role in member.roles:
            for cargo_nome in STAFF_ROLES:
                if normalizar_nome(role.name) == normalizar_nome(cargo_nome):
                    cargos_staff.append(role.name)
                    break
        
        if cargos_staff:
            embed.add_field(
                name="📋 Cargos de Staff",
                value="\n".join(cargos_staff[:5]),
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GestorCog(bot))
    bot.add_view(GestorOpenView())
    print("✅ Sistema de Gestor de Farm configurado com views persistentes!")
