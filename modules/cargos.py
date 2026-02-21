import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO DE CARGOS (NOMES REAIS) ==========
CARGOS_CONFIG = {
    "👑 | Lider | 00": 1474880677827579935,
    "💎 | Lider | 01": 1474880748803723294,
    "👮 | Lider | 02": 1474880750909128874,
    "🎖️ | Lider | 03": 1474880752566014156,
    "🎖️ | Gerente Geral": 1474880754214371539,
    "🎖️ | Gerente De Farm": 1474880755078533241,
    "🎖️ | Gerente De Pista": 1474880756026179825,
    "🎖️ | Gerente de Recrutamento": 1474880756433162353,
    "🎖️ | Supervisor": 1474880757385134130,
    "🎖️ | Recrutador": 1474880757984923708,
    "🎖️ | Ceo Elite": 1474881051569688656,
    "🎖️ | Sub Elite": 1474881053108731945,
    "🎖️ | Elite": 1474881054300180631,
    "🙅‍♂️ | Membro": 1474669904547549265,
}

# Mapeamento de prefixos visuais para os cargos
PREFIXO_PARA_CARGO = {
    "00": "👑 | Lider | 00",
    "01": "💎 | Lider | 01",
    "02": "👮 | Lider | 02",
    "03": "🎖️ | Lider | 03",
    "G.Geral": "🎖️ | Gerente Geral",
    "G.Farm": "🎖️ | Gerente De Farm",
    "G.Pista": "🎖️ | Gerente De Pista",
    "G.Rec": "🎖️ | Gerente de Recrutamento",
    "Sup": "🎖️ | Supervisor",
    "Rec": "🎖️ | Recrutador",
    "Ceo E": "🎖️ | Ceo Elite",
    "Sub E": "🎖️ | Sub Elite",
    "E": "🎖️ | Elite",
    "M": "🙅‍♂️ | Membro",
}

# Ordem de prioridade visual (do maior para o menor)
PREFIXOS_VISUAIS = [
    "00", "01", "02", "03", "G.Geral", "G.Farm", "G.Pista", "G.Rec",
    "Sup", "Rec", "Ceo E", "Sub E", "E", "M"
]

# Cargos que podem usar o painel (staff)
STAFF_PREFIXOS = [
    "00", "01", "02", "03", "G.Geral", "G.Farm", "G.Pista", "G.Rec",
    "Sup", "Rec", "Ceo E", "Sub E"
]

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

# ========== FUNÇÕES AUXILIARES ==========
def extrair_parte_nickname(nickname: str):
    """Extrai a parte do nome do usuário (remove clan tags, números extras, etc)"""
    if not nickname:
        return "User"
    
    # Dividir por ' | ' primeiro
    partes = nickname.split(' | ')
    
    # Se tiver 3 partes: "PREFIXO | NOME | ID"
    if len(partes) >= 3:
        nome = partes[1].strip()
    # Se tiver 2 partes: "NOME | ID"
    elif len(partes) == 2:
        nome = partes[0].strip()
    else:
        nome = nickname.strip()
    
    # Remover qualquer coisa entre parênteses (ex: (10000))
    nome = re.sub(r'\s*\([^)]*\)', '', nome)
    
    # Remover números soltos no meio do nome
    nome = re.sub(r'\s+\d+\s*$', '', nome)  # Remove números no final
    nome = re.sub(r'\s+\d+\s+', ' ', nome)  # Remove números no meio
    
    return nome.strip() or "User"

def extrair_id_fivem(nickname: str):
    """Extrai ID do FiveM do nickname (sempre o ÚLTIMO número)"""
    if not nickname:
        return None
    
    # Encontrar TODOS os números no nickname
    numeros = re.findall(r'\b(\d+)\b', nickname)
    
    if numeros:
        # Retornar o ÚLTIMO número (assumindo que é o ID do FiveM)
        return numeros[-1]
    
    return None

def extrair_prefixo_visual(nickname: str):
    """Extrai o prefixo visual do nickname"""
    if not nickname:
        return None
    
    # Tentar pegar a primeira parte antes do primeiro |
    partes = nickname.split(' | ')
    if partes:
        prefixo = partes[0].strip()
        # Verificar se o prefixo está na lista de prefixos visuais
        if prefixo in PREFIXOS_VISUAIS:
            return prefixo
    
    return None

def get_cargo_por_prefixo(guild: discord.Guild, prefixo: str):
    """Retorna o objeto cargo baseado no prefixo"""
    if prefixo not in PREFIXO_PARA_CARGO:
        return None
    
    nome_cargo = PREFIXO_PARA_CARGO[prefixo]
    cargo_id = CARGOS_CONFIG.get(nome_cargo)
    
    if cargo_id:
        return guild.get_role(cargo_id)
    return None

def get_prefixo_por_cargo(role: discord.Role) -> str:
    """Retorna o prefixo baseado no cargo"""
    for prefixo, nome_cargo in PREFIXO_PARA_CARGO.items():
        if role.name == nome_cargo or role.id == CARGOS_CONFIG.get(nome_cargo):
            return prefixo
    return None

def usuario_pode_usar_painel(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar o painel de cargos"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo staff
    for role in member.roles:
        prefixo = get_prefixo_por_cargo(role)
        if prefixo in STAFF_PREFIXOS:
            return True
    
    return False

async def atualizar_nickname(member: discord.Member):
    """Atualiza nickname baseado no cargo principal"""
    try:
        # Verificar permissões
        if not member.guild.me.guild_permissions.manage_nicknames:
            return False
        
        # Extrair partes do nickname atual
        nickname_atual = member.nick or member.name
        parte_nome = extrair_parte_nickname(nickname_atual)
        id_fivem = extrair_id_fivem(nickname_atual)
        
        # Se não tiver ID, usar placeholder
        if not id_fivem:
            id_fivem = "000000"
        
        # Se o nome estiver vazio, usar o nome do usuário
        if not parte_nome or parte_nome == "User":
            parte_nome = member.name.split('#')[0]
        
        # Limpar o nome: remover caracteres especiais e espaços extras
        parte_nome = re.sub(r'[^\w\s]', '', parte_nome)
        parte_nome = ' '.join(parte_nome.split())
        
        # Determinar o prefixo visual baseado nos cargos do membro
        prefixo_visual = "M"  # Padrão
        
        # Verificar cargos do membro (do maior para o menor)
        for role in sorted(member.roles, key=lambda r: r.position, reverse=True):
            prefixo = get_prefixo_por_cargo(role)
            if prefixo:
                prefixo_visual = prefixo
                break
        
        # Gerar novo nickname no formato "PREFIXO | NOME | ID"
        template = NICKNAME_CONFIG.get(prefixo_visual, NICKNAME_CONFIG["M"])
        novo_nick = template.format(name=parte_nome, id=id_fivem)
        
        # Limitar a 32 caracteres
        if len(novo_nick) > 32:
            # Encurtar o nome
            nome_curto = parte_nome[:15]
            novo_nick = template.format(name=nome_curto, id=id_fivem)
            
            if len(novo_nick) > 32:
                # Último caso: remover espaços
                novo_nick = novo_nick.replace(' ', '')
                novo_nick = novo_nick[:32]
        
        # Aplicar se for diferente
        if member.nick != novo_nick:
            await member.edit(nick=novo_nick)
            return True
            
    except Exception as e:
        print(f"Erro ao atualizar nickname: {e}")
    
    return False

# ========== SISTEMA DE SELEÇÃO DE CARGO ==========
class CargoSelectView(ui.View):
    """View para selecionar cargo"""
    def __init__(self, member: discord.Member, action: str):
        super().__init__(timeout=60)
        self.member = member
        self.action = action  # "add" ou "remove"
        
        # Opções de cargo
        options = []
        for prefixo in PREFIXOS_VISUAIS:
            nome_cargo = PREFIXO_PARA_CARGO.get(prefixo, "Desconhecido")
            options.append(
                discord.SelectOption(
                    label=prefixo,
                    description=nome_cargo
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
        
        prefixo = self.select.values[0]
        cargo = get_cargo_por_prefixo(interaction.guild, prefixo)
        
        if not cargo:
            msg = await interaction.followup.send(f"❌ Cargo para prefixo {prefixo} não encontrado!", ephemeral=True)
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
                        "2. **ID do FiveM**: `9237` (deve estar no nickname)\n"
                        "3. **Nome**: `João` ou parte do nome"
                    ),
                    color=discord.Color.red()
                )
                msg = await interaction.followup.send(embed=embed, ephemeral=True)
                await asyncio.sleep(8)
                await msg.delete()
                return
            
            # Extrair informações do nickname
            id_fivem = extrair_id_fivem(member.nick or member.name)
            prefixo_atual = extrair_prefixo_visual(member.nick or member.name)
            
            # Mostrar view para selecionar cargo
            view = CargoSelectView(member, self.action)
            
            embed = discord.Embed(
                title=f"{'➕ Adicionar' if self.action == 'add' else '➖ Remover'} Cargo",
                description=(
                    f"**Usuário:** {member.mention}\n"
                    f"**Nickname atual:** `{member.nick or member.name}`\n"
                    f"**Prefixo atual:** `{prefixo_atual or 'Nenhum'}`\n"
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
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        modal = CargoModal("add")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➖ Rem Cargo", style=ButtonStyle.red, emoji="➖", custom_id="remove_cargo_clean")
    async def remove_cargo(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        modal = CargoModal("remove")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🔄 Corrigir Nick", style=ButtonStyle.blurple, emoji="🔄", custom_id="fix_nick_clean")
    async def fix_nick(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
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
                "`Prefixo | Nome | ID`\n\n"
                "**Exemplos:**\n"
                "• `00 | Torres | 9237`\n"
                "• `01 | Torres | 9237`\n"
                "• `02 | Torres | 9237`\n"
                "• `03 | Torres | 9237`\n"
                "• `G.Geral | Torres | 9237`\n"
                "• `G.Farm | Torres | 9237`\n"
                "• `G.Pista | Torres | 9237`\n"
                "• `G.Rec | Torres | 9237`\n"
                "• `Sup | Torres | 9237`\n"
                "• `Rec | Torres | 9237`\n"
                "• `Ceo E | Torres | 9237`\n"
                "• `Sub E | Torres | 9237`\n"
                "• `E | Torres | 9237`\n"
                "• `M | Torres | 9237`"
            ),
            color=discord.Color.blue()
        )
        
        # Lista de cargos disponíveis
        cargos_text = ""
        for prefixo in PREFIXOS_VISUAIS:
            cargos_text += f"• {prefixo} - {PREFIXO_PARA_CARGO[prefixo]}\n"
        
        embed.add_field(
            name="📋 Cargos Disponíveis",
            value=cargos_text,
            inline=False
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
    
    @commands.command(name="verificar_prefixo")
    @commands.has_permissions(administrator=True)
    async def verificar_prefixo(self, ctx, member: discord.Member = None):
        """Verifica o prefixo de um usuário"""
        if member is None:
            member = ctx.author
        
        nickname = member.nick or member.name
        prefixo = extrair_prefixo_visual(nickname)
        id_fivem = extrair_id_fivem(nickname)
        nome = extrair_parte_nickname(nickname)
        
        embed = discord.Embed(
            title="🔍 Verificação de Prefixo",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👤 Usuário", value=member.mention, inline=True)
        embed.add_field(name="🏷️ Nickname", value=f"`{nickname}`", inline=False)
        embed.add_field(name="🎯 Prefixo", value=f"`{prefixo or 'Nenhum'}`", inline=True)
        embed.add_field(name="🆔 ID FiveM", value=f"`{id_fivem or 'Nenhum'}`", inline=True)
        embed.add_field(name="📝 Nome", value=f"`{nome}`", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CargosCog(bot))
    bot.add_view(CleanCargoView())
    print("✅ Sistema de Cargos configurado com views persistentes!")
