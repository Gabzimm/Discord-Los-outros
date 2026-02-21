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

# ORDEM DE PRIORIDADE (usando os NOMES REAIS dos cargos)
ORDEM_PRIORIDADE = [
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
    "🎖️ | Elite",
    "🙅‍♂️ | Membro",
]

# Cargos de staff (usando os NOMES REAIS)
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

# Mapeamento de nomes de cargos para prefixos visuais
CARGO_PARA_PREFIXO = {
    "👑 | Lider | 00": "00",
    "💎 | Lider | 01": "01",
    "👮 | Lider | 02": "02",
    "🎖️ | Lider | 03": "03",
    "🎖️ | Gerente Geral": "G.Geral",
    "🎖️ | Gerente De Farm": "G.Farm",
    "🎖️ | Gerente De Pista": "G.Pista",
    "🎖️ | Gerente de Recrutamento": "G.Rec",
    "🎖️ | Supervisor": "Sup",
    "🎖️ | Recrutador": "Rec",
    "🎖️ | Ceo Elite": "Ceo E",
    "🎖️ | Sub Elite": "Sub E",
    "🎖️ | Elite": "E",
    "🙅‍♂️ | Membro": "M",
}

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
def buscar_usuario_por_fivem_id(guild: discord.Guild, fivem_id: str) -> discord.Member:
    """Busca usuário pelo ID do FiveM no nickname"""
    for member in guild.members:
        if member.nick:
            # Procurar ID no formato " | 123456" no final
            if member.nick.endswith(f" | {fivem_id}"):
                return member
    
    return None

def extrair_parte_nickname(nickname: str):
    """Extrai a parte do nome do usuário (segunda parte após o primeiro ' | ')"""
    if not nickname:
        return "User"
    
    # Formato: "PREFIXO | NOME | ID"
    partes = nickname.split(' | ')
    if len(partes) >= 2:
        return partes[1].strip()
    
    return nickname.strip()

def extrair_id_fivem(nickname: str):
    """Extrai ID do FiveM do nickname (último número após o último ' | ')"""
    if not nickname:
        return None
    
    # Formato: "PREFIXO | NOME | ID"
    partes = nickname.split(' | ')
    if len(partes) >= 3:
        ultima_parte = partes[-1].strip()
        if ultima_parte.isdigit():
            return ultima_parte
    
    return None

def extrair_prefixo_visual(nickname: str):
    """Extrai o prefixo visual do nickname (primeira parte antes do primeiro ' | ')"""
    if not nickname:
        return None
    
    partes = nickname.split(' | ')
    if partes:
        return partes[0].strip()
    
    return None

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
        
        # Encontrar o cargo principal (igual ao script base)
        cargo_principal = None
        for cargo_nome in ORDEM_PRIORIDADE:
            if discord.utils.get(member.roles, name=cargo_nome):
                cargo_principal = cargo_nome
                break
        
        if not cargo_principal:
            return False
        
        # Converter nome do cargo para prefixo visual
        prefixo_visual = CARGO_PARA_PREFIXO.get(cargo_principal, "M")
        
        # Gerar novo nickname
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

def usuario_pode_usar_painel(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar o painel de cargos"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo staff (igual ao script base)
    for role in member.roles:
        if role.name in STAFF_ROLES:
            return True
    
    return False

# ========== SISTEMA DE SELEÇÃO DE CARGO ==========
class CargoSelectView(ui.View):
    """View para selecionar cargo"""
    def __init__(self, member: discord.Member, action: str):
        super().__init__(timeout=60)
        self.member = member
        self.action = action  # "add" ou "remove"
        
        # Opções de cargo (usando os nomes reais)
        options = []
        for cargo_nome in ORDEM_PRIORIDADE:
            # Pegar apenas o prefixo para mostrar (mais limpo)
            prefixo = CARGO_PARA_PREFIXO.get(cargo_nome, "?")
            options.append(
                discord.SelectOption(
                    label=prefixo,
                    description=cargo_nome
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
        
        # Encontrar o nome real do cargo baseado no prefixo
        cargo_nome = None
        for nome, pref in CARGO_PARA_PREFIXO.items():
            if pref == prefixo:
                cargo_nome = nome
                break
        
        if not cargo_nome:
            msg = await interaction.followup.send("❌ Cargo não encontrado!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        cargo = discord.utils.get(interaction.guild.roles, name=cargo_nome)
        
        if not cargo:
            msg = await interaction.followup.send("❌ Cargo não encontrado no servidor!", ephemeral=True)
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
                member = buscar_usuario_por_fivem_id(interaction.guild, input_text)
                
                # Se não encontrou, buscar pelo ID do Discord
                if not member:
                    try:
                        member = interaction.guild.get_member(int(input_text))
                    except:
                        pass
            
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
                        "3. **Nome**: `João` ou parte do nome\n\n"
                        "**📌 Exemplo de nickname com ID:**\n"
                        "`M | João | 9237`"
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
        for cargo_nome in ORDEM_PRIORIDADE:
            prefixo = CARGO_PARA_PREFIXO.get(cargo_nome, "?")
            cargos_text += f"• {prefixo} - {cargo_nome}\n"
        
        embed.add_field(
            name="📋 Cargos Disponíveis",
            value=cargos_text,
            inline=False
        )
        
        embed.add_field(
            name="👑 Staff Permitido",
            value="\n".join(STAFF_ROLES[:6]) + "\n...",
            inline=False
        )
        
        embed.set_footer(text="Sistema Clean • Mensagens auto-deletam em 5s")
        
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
