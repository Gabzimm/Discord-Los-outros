import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO DE NICKNAMES ==========
NICKNAME_CONFIG = {
    "00": "00 | {name} | {id}",
    "01": "01 | {name} | {id}",
    "02": "02 | {name} | {id}",
    "03": "03 | {name} | {id}",
    "G.Geral": "G.Geral | {name} | {id}",
    "G.Farm": "G.Farm | {name} | {id}",
    "G.Pista": "G.Pista | {name} | {id}",
    "G.Rec": "G.Rec | {name} | {id}",
    "Sup": "Sup | {name} | {id}",
    "Rec": "Rec | {name} | {id}",
    "Ceo E": "Ceo E | {name} | {id}",
    "Sub E": "Sub E | {name} | {id}",
    "E": "E | {name} | {id}",
    "M": "M | {name} | {id}",
}

# Ordem de prioridade (do maior para o menor)
ORDEM_PRIORIDADE = [
    "00", "01", "02", "03", "G.Geral", "G.Farm", "G.Pista", "G.Rec",
    "Sup", "Rec", "Ceo E", "Sub E", "E", "M"
]

# Cargos que podem usar o painel (staff)
STAFF_ROLES = [
    "00", "01", "02", "03", "G.Geral", "G.Farm", "G.Pista", "G.Rec",
    "Sup", "Rec", "Ceo E", "Sub E"
]

# ========== FUNÇÕES AUXILIARES ==========
def extrair_parte_nickname(nickname: str):
    """Extrai a parte do nome do usuário (antes do ' | ') ignorando prefixos"""
    if not nickname:
        return "User"
    
    # Dividir por ' | '
    partes = nickname.split(' | ')
    
    # Se tiver 3 partes: "PREFIXO | NOME | ID"
    if len(partes) >= 2:
        return partes[1].strip()
    
    # Se tiver 2 partes: "NOME | ID"
    if len(partes) == 2:
        return partes[0].strip()
    
    return nickname.strip()

def extrair_id_fivem(nickname: str):
    """Extrai ID do FiveM do nickname (últimos números após o último ' | ')"""
    if not nickname:
        return None
    
    # Dividir por ' | '
    partes = nickname.split(' | ')
    
    # Se tiver pelo menos 2 partes, a última pode ser o ID
    if len(partes) >= 2:
        ultima_parte = partes[-1].strip()
        if ultima_parte.isdigit():
            return ultima_parte
    
    return None

async def atualizar_nickname(member: discord.Member):
    """Atualiza nickname baseado no cargo principal usando config_cargos"""
    try:
        # Verificar permissões
        if not member.guild.me.guild_permissions.manage_nicknames:
            return False
        
        # Buscar o gerenciador de cargos
        cog = member.guild.get_cog("CargosManagerCog")
        if not cog:
            print("⚠️ CargosManagerCog não encontrado!")
            return False
        
        manager = cog.manager
        
        # Extrair partes do nickname atual
        nickname_atual = member.nick or member.name
        parte_nome = extrair_parte_nickname(nickname_atual)
        id_fivem = extrair_id_fivem(nickname_atual)
        
        # Se não tiver ID, tentar extrair de algum lugar ou usar placeholder
        if not id_fivem:
            id_fivem = "000000"
        
        # Encontrar o cargo principal baseado na ordem de prioridade
        cargo_principal = None
        for cargo_nome in ORDEM_PRIORIDADE:
            cargo = manager.get_cargo_por_nome(member.guild.id, cargo_nome)
            if cargo and cargo in member.roles:
                cargo_principal = cargo_nome
                break
        
        if not cargo_principal:
            return False
        
        # Verificar se o cargo está na config
        if cargo_principal not in NICKNAME_CONFIG:
            return False
        
        # Gerar novo nickname
        template = NICKNAME_CONFIG[cargo_principal]
        novo_nick = template.format(name=parte_nome, id=id_fivem)
        
        # Limitar a 32 caracteres
        if len(novo_nick) > 32:
            novo_nick = novo_nick[:32]
        
        # Aplicar se for diferente
        if member.nick != novo_nick:
            await member.edit(nick=novo_nick)
            return True
            
    except Exception as e:
        print(f"Erro ao atualizar nickname: {e}")
    
    return False

def usuario_pode_usar_painel(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar o painel de cargos"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo staff
    for role in member.roles:
        if role.name in STAFF_ROLES:
            return True
    
    return False

# ========== SISTEMA DE SELEÇÃO DE CARGO ==========
class CargoSelectView(ui.View):
    """View para selecionar cargo usando config_cargos"""
    def __init__(self, member: discord.Member, action: str):
        super().__init__(timeout=60)
        self.member = member
        self.action = action  # "add" ou "remove"
        
        # Buscar gerenciador de cargos
        cog = member.guild.get_cog("CargosManagerCog")
        self.manager = cog.manager if cog else None
        
        # Opções de cargo
        options = []
        cargos_disponiveis = [
            ("00", "Dono"),
            ("01", "Dono Alternativo"),
            ("02", "Dono Alternativo"),
            ("03", "Dono Alternativo"),
            ("G.Geral", "Gerente Geral"),
            ("G.Farm", "Gerente de Farm"),
            ("G.Pista", "Gerente de Pista"),
            ("G.Rec", "Gerente de Recrutamento"),
            ("Sup", "Supervisor"),
            ("Rec", "Recrutador"),
            ("Ceo E", "CEO Elite"),
            ("Sub E", "Sub Elite"),
            ("E", "Elite"),
            ("M", "Membro"),
        ]
        
        for cargo_nome, desc in cargos_disponiveis:
            options.append(
                discord.SelectOption(
                    label=cargo_nome,
                    description=desc
                )
            )
        
        self.select = ui.Select(
            placeholder="Selecione o cargo...",
            options=options,
            custom_id="cargo_select"
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        cargo_nome = self.select.values[0]
        
        # Buscar cargo usando o manager
        if not self.manager:
            msg = await interaction.followup.send("❌ Gerenciador de cargos não disponível!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        cargo = self.manager.get_cargo_por_nome(interaction.guild.id, cargo_nome)
        
        if not cargo:
            msg = await interaction.followup.send(f"❌ Cargo `{cargo_nome}` não encontrado!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        try:
            if self.action == "add":
                await self.member.add_roles(cargo)
                mensagem = f"✅ Cargo `{cargo.name}` adicionado para {self.member.mention}"
            else:
                await self.member.remove_roles(cargo)
                mensagem = f"✅ Cargo `{cargo.name}` removido de {self.member.mention}"
            
            # Atualizar nickname
            await atualizar_nickname(self.member)
            
            # Enviar mensagem temporária
            msg = await interaction.followup.send(mensagem, ephemeral=False)
            await asyncio.sleep(5)
            await msg.delete()
            
            # Deletar a mensagem com o select também
            await interaction.delete_original_response()
            
        except discord.Forbidden:
            msg = await interaction.followup.send("❌ Sem permissão!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            msg = await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()

# ========== MODAL DE BUSCA ==========
class CargoModal(ui.Modal, title="🎯 Gerenciar Cargo"):
    """Modal para buscar usuário"""
    
    usuario_input = ui.TextInput(
        label="Usuário (@nome ou ID do FiveM):",
        placeholder="Ex: @João ou 9237",
        required=True
    )
    
    def __init__(self, action: str):
        super().__init__()
        self.action = action  # "add" ou "remove"
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Verificar se pode usar o painel
        if not usuario_pode_usar_painel(interaction.user):
            msg = await interaction.followup.send("❌ Apenas staff pode usar!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        # Buscar gerenciador de cargos
        cog = interaction.guild.get_cog("CargosManagerCog")
        if not cog:
            msg = await interaction.followup.send("❌ Gerenciador de cargos não disponível!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        manager = cog.manager
        
        # Encontrar usuário
        member = None
        input_text = self.usuario_input.value
        
        try:
            # 1. Se for menção (@usuário)
            if "<@" in input_text:
                user_id = input_text.replace("<@", "").replace(">", "").replace("!", "")
                member = interaction.guild.get_member(int(user_id))
            
            # 2. Se for apenas números (ID do FiveM)
            elif input_text.isdigit():
                # Buscar pelo ID do FiveM nos nicknames
                for guild_member in interaction.guild.members:
                    if guild_member.nick:
                        id_fivem = extrair_id_fivem(guild_member.nick)
                        if id_fivem == input_text:
                            member = guild_member
                            break
            
            # 3. Se for texto (nome)
            else:
                # Buscar por nome no nickname
                for guild_member in interaction.guild.members:
                    if guild_member.nick and input_text.lower() in guild_member.nick.lower():
                        member = guild_member
                        break
                
                # Se não encontrou no nickname, buscar no nome
                if not member:
                    for guild_member in interaction.guild.members:
                        if input_text.lower() in guild_member.name.lower():
                            member = guild_member
                            break
            
            if not member:
                embed = discord.Embed(
                    title="❌ Usuário não encontrado!",
                    description=(
                        f"Não encontrei nenhum usuário com: `{input_text}`\n\n"
                        "**Formas de buscar:**\n"
                        "1. **Menção**: `@João`\n"
                        "2. **ID do FiveM**: `9237`\n"
                        "3. **Nome**: `João` ou parte do nome"
                    ),
                    color=discord.Color.red()
                )
                msg = await interaction.followup.send(embed=embed, ephemeral=True)
                await asyncio.sleep(8)
                await msg.delete()
                return
            
            # Extrair ID do FiveM do nickname
            id_fivem = extrair_id_fivem(member.nick or member.name)
            
            # Mostrar view para selecionar cargo
            view = CargoSelectView(member, self.action)
            
            embed = discord.Embed(
                title=f"{'➕ Adicionar' if self.action == 'add' else '➖ Remover'} Cargo",
                description=(
                    f"**Usuário:** {member.mention}\n"
                    f"**Nickname atual:** `{member.nick or member.name}`\n"
                    f"**ID FiveM:** `{id_fivem or 'Não encontrado'}`\n\n"
                    f"Selecione o cargo abaixo:"
                ),
                color=discord.Color.green() if self.action == "add" else discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erro!",
                description=f"Ocorreu um erro: `{str(e)}`",
                color=discord.Color.red()
            )
            msg = await interaction.followup.send(embed=embed, ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()

# ========== VIEW DO PAINEL PRINCIPAL ==========
class CleanCargoView(ui.View):
    """View do painel de cargos"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="➕ Add Cargo", style=ButtonStyle.green, emoji="➕", custom_id="add_cargo_clean")
    async def add_cargo(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        modal = CargoModal("add")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➖ Rem Cargo", style=ButtonStyle.red, emoji="➖", custom_id="remove_cargo_clean")
    async def remove_cargo(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        modal = CargoModal("remove")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🔄 Corrigir Nick", style=ButtonStyle.blurple, emoji="🔄", custom_id="fix_nick_clean")
    async def fix_nick(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Corrigir nickname do próprio usuário
        success = await atualizar_nickname(interaction.user)
        
        if success:
            msg = await interaction.followup.send(f"✅ Nickname corrigido para `{interaction.user.nick}`", ephemeral=True)
        else:
            msg = await interaction.followup.send("❌ Não foi possível corrigir o nickname", ephemeral=True)
        
        await asyncio.sleep(5)
        await msg.delete()

# ========== COG PRINCIPAL ==========
class CargosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Sistema de Cargos carregado!")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Atualiza nickname quando cargo muda"""
        if before.roles != after.roles:
            await asyncio.sleep(1)
            await atualizar_nickname(after)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Carrega view persistente"""
        self.bot.add_view(CleanCargoView())
        print("✅ View de cargos carregada")
    
    @commands.command(name="setup_cargos")
    @commands.has_permissions(administrator=True)
    async def setup_cargos(self, ctx):
        """Cria painel de cargos"""
        
        embed = discord.Embed(
            title="⚙️ SISTEMA DE CARGOS",
            description=(
                "**Como funciona:**\n"
                "1. Clique em Add ou Rem\n"
                "2. Digite @usuário ou ID do FiveM\n"
                "3. Selecione o cargo\n"
                "✅ Nickname atualiza automaticamente\n\n"
                "**📌 Formato de Nickname:**\n"
                "`Cargo | Nome | ID`\n\n"
                "**Exemplos:**\n"
                "• `00 | Torres | 9237`\n"
                "• `G.Geral | Torres | 9237`\n"
                "• `E | Torres | 9237`\n"
                "• `M | Torres | 9237`"
            ),
            color=discord.Color.blue()
        )
        
        # Lista de cargos disponíveis
        cargos_text = ""
        for cargo in ORDEM_PRIORIDADE:
            cargos_text += f"• {cargo}\n"
        
        embed.add_field(
            name="📋 Cargos Disponíveis",
            value=cargos_text,
            inline=True
        )
        
        embed.add_field(
            name="👑 Staff Permitido",
            value="\n".join(STAFF_ROLES[:10]),
            inline=True
        )
        
        embed.set_footer(text="Sistema Integrado • Mensagens auto-deletam em 5s")
        
        view = CleanCargoView()
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="fixnick")
    async def fixnick(self, ctx, member: discord.Member = None):
        """Corrige nickname manualmente"""
        if member is None:
            member = ctx.author
        
        # Verificar staff (só staff pode corrigir outros)
        if member != ctx.author and not usuario_pode_usar_painel(ctx.author):
            await ctx.send("❌ Você não tem permissão para corrigir nickname de outros!", delete_after=5)
            return
        
        success = await atualizar_nickname(member)
        
        if success:
            msg = await ctx.send(f"✅ Nickname de {member.mention} corrigido para `{member.nick}`")
        else:
            msg = await ctx.send(f"❌ Não foi possível corrigir o nickname de {member.mention}")
        
        await asyncio.sleep(5)
        await msg.delete()

async def setup(bot):
    await bot.add_cog(CargosCog(bot))
    bot.add_view(CleanCargoView())
    print("✅ Sistema de Cargos configurado com views persistentes!")
