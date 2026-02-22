import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO SIMPLES (IGUAL AO BASE) ==========
NICKNAME_CONFIG = {
    "👑 | Lider | 00": "00 | {name} | {id}",
    "💎 | Lider | 01": "01 | {name} | {id}",
    "👮 | Lider | 02": "02 | {name} | {id}",
    "🎖️ | Lider | 03": "03 | {name} | {id}",
    "🎖️ | Gerente Geral": "G.Geral | {name} | {id}",
    "🎖️ | Gerente De Farm": "G.Farm | {name} | {id}",
    "🎖️ | Gerente De Pista": "G.Pista | {name} | {id}",
    "🎖️ | Gerente de Recrutamento": "G.Rec | {name} | {id}",
    "🎖️ | Supervisor": "Sup | {name} | {id}",
    "🎖️ | Recrutador": "Rec | {name} | {id}",
    "🎖️ | Ceo Elite": "Ceo E | {name} | {id}",
    "🎖️ | Sub Elite": "Sub E | {name} | {id}",
    "🎖️ | Elite": "E | {name} | {id}",
    "🙅‍♂️ | Membro": "M | {name} | {id}",
}

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

# Cargos de staff (quem pode usar o painel)
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

# ========== FUNÇÃO DE NORMALIZAÇÃO ==========
def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def get_cargo_por_nome_flexivel(guild, nome_busca):
    """Busca cargo ignorando diferenças de espaços no nome"""
    if not nome_busca:
        return None
    
    nome_busca_normalizado = normalizar_nome(nome_busca)
    
    for role in guild.roles:
        nome_role_normalizado = normalizar_nome(role.name)
        if nome_role_normalizado == nome_busca_normalizado:
            return role
    
    return None

def member_tem_cargo_flexivel(member, nome_cargo):
    """Verifica se o membro tem um cargo ignorando espaços"""
    if not member or not nome_cargo:
        return False
    
    nome_cargo_normalizado = normalizar_nome(nome_cargo)
    
    for role in member.roles:
        nome_role_normalizado = normalizar_nome(role.name)
        if nome_role_normalizado == nome_cargo_normalizado:
            return True
    
    return False

# ========== FUNÇÕES AUXILIARES (IGUAL AO BASE) ==========
def buscar_usuario_por_fivem_id(guild: discord.Guild, fivem_id: str) -> discord.Member:
    """Busca usuário pelo ID do FiveM no nickname"""
    for member in guild.members:
        if member.nick:
            # Padrão: " | 123456" no final
            if member.nick.endswith(f" | {fivem_id}"):
                return member
    
    return None

def extrair_parte_nickname(nickname: str):
    """Extrai a parte do nome do usuário (segunda parte após o primeiro ' | ')"""
    if not nickname:
        return "User"
    
    # Padrão: "PREFIXO | NOME | ID"
    partes = nickname.split(' | ')
    if len(partes) >= 2:
        return partes[1].strip()
    
    return nickname.strip()

def extrair_id_fivem(nickname: str):
    """Extrai ID do FiveM do nickname (último número após o último ' | ')"""
    if not nickname:
        return None
    
    # Padrão: "PREFIXO | NOME | ID"
    partes = nickname.split(' | ')
    if len(partes) >= 3:
        ultima_parte = partes[-1].strip()
        if ultima_parte.isdigit():
            return ultima_parte
    
    return None

async def atualizar_nickname(member: discord.Member):
    """Atualiza nickname mantendo a estrutura igual ao BASE"""
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
        
        # Encontrar cargo principal (usando busca flexível)
        cargo_principal = None
        for cargo_nome in ORDEM_PRIORIDADE:
            if member_tem_cargo_flexivel(member, cargo_nome):
                cargo_principal = cargo_nome
                break
        
        if not cargo_principal or cargo_principal not in NICKNAME_CONFIG:
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
        print(f"Erro: {e}")
    
    return False

# ========== SISTEMA DE SELEÇÃO DE CARGO ==========
class CargoSelectView(ui.View):
    """View simples para selecionar cargo"""
    def __init__(self, member: discord.Member, action: str):
        super().__init__(timeout=60)
        self.member = member
        self.action = action  # "add" ou "remove"
        
        # Opções de cargo
        options = []
        for i, cargo_nome in enumerate(ORDEM_PRIORIDADE):
            # Extrair prefixo para mostrar
            if " | " in cargo_nome:
                partes = cargo_nome.split(' | ')
                prefixo = partes[0] if len(partes) > 0 else cargo_nome
            else:
                prefixo = cargo_nome
            
            options.append(
                discord.SelectOption(
                    label=prefixo,
                    description=cargo_nome,
                    value=str(i)  # ← USAR ÍNDICE COMO VALUE ÚNICO
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
        
        # Pegar o índice e converter para o nome do cargo
        index = int(self.select.values[0])
        cargo_nome = ORDEM_PRIORIDADE[index]
        
        # Usar busca flexível
        cargo = get_cargo_por_nome_flexivel(interaction.guild, cargo_nome)
        
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

# ========== MODAL DE BUSCA (IGUAL AO BASE) ==========
class SimpleCargoModal(ui.Modal, title="🎯 Gerenciar Cargo"):
    """Modal simples para gerenciar cargo"""
    
    usuario_input = ui.TextInput(
        label="Usuário (@nome ou número do FiveM):",
        placeholder="Ex: @João ou 9237",
        required=True
    )
    
    def __init__(self, action: str):
        super().__init__()
        self.action = action  # "add" ou "remove"
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Verificar se é staff (usando busca flexível)
        is_staff = False
        for role in interaction.user.roles:
            for cargo_staff in STAFF_ROLES:
                if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                    is_staff = True
                    break
            if is_staff:
                break
        
        if not is_staff and not interaction.user.guild_permissions.administrator:
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
                # Primeiro, buscar pelo ID do FiveM no nickname
                member = buscar_usuario_por_fivem_id(interaction.guild, input_text)
                
                # Se não encontrou, buscar pelo ID do Discord
                if not member:
                    try:
                        member = interaction.guild.get_member(int(input_text))
                    except:
                        pass
            
            # 3. Se for texto (nome)
            else:
                # Buscar por nome no nickname primeiro
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
            
            # Extrair ID do FiveM do nickname
            id_fivem = extrair_id_fivem(member.nick or member.name)
            
            # Criar embed simples
            embed = discord.Embed(
                title=f"{'➕ Adicionar' if self.action == 'add' else '➖ Remover'} Cargo",
                description=(
                    f"**Usuário:** {member.mention}\n"
                    f"**Nickname atual:** `{member.nick or member.name}`\n"
                    f"**ID FiveM:** `{id_fivem or 'Não encontrado'}`\n\n"
                    f"Selecione o cargo abaixo:"
                ),
                color=discord.Color.blue() if self.action == "add" else discord.Color.red()
            )
            
            # Mostrar view para selecionar cargo
            view = CargoSelectView(member, self.action)
            
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

# ========== VIEW DO PAINEL (IGUAL AO BASE) ==========
class CleanCargoView(ui.View):
    """View clean do painel de cargos"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="➕ Add Cargo", style=ButtonStyle.green, emoji="➕", custom_id="add_cargo_clean")
    async def add_cargo(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff (usando busca flexível)
        is_staff = False
        for role in interaction.user.roles:
            for cargo_staff in STAFF_ROLES:
                if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                    is_staff = True
                    break
            if is_staff:
                break
        
        if not is_staff and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas staff!", ephemeral=True)
            return
        
        modal = SimpleCargoModal("add")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➖ Rem Cargo", style=ButtonStyle.red, emoji="➖", custom_id="remove_cargo_clean")
    async def remove_cargo(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff (usando busca flexível)
        is_staff = False
        for role in interaction.user.roles:
            for cargo_staff in STAFF_ROLES:
                if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                    is_staff = True
                    break
            if is_staff:
                break
        
        if not is_staff and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas staff!", ephemeral=True)
            return
        
        modal = SimpleCargoModal("remove")
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🔄 Corrigir Nick", style=ButtonStyle.blurple, emoji="🔄", custom_id="fix_nick_clean")
    async def fix_nick(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar staff (usando busca flexível)
        is_staff = False
        for role in interaction.user.roles:
            for cargo_staff in STAFF_ROLES:
                if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                    is_staff = True
                    break
            if is_staff:
                break
        
        if not is_staff and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Apenas staff!", ephemeral=True)
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
        """Cria painel clean de cargos"""
        
        embed = discord.Embed(
            title="⚙️ SISTEMA DE CARGOS",
            description=(
                "**Como funciona:**\n"
                "1. Clique em Add ou Rem\n"
                "2. Digite @usuário ou ID do FiveM\n"
                "3. Selecione o cargo\n"
                "✅ Nickname atualiza automaticamente\n\n"
                "**📌 Importante:**\n"
                "• O nickname mantém a primeira parte\n"
                "• ID do FiveM é preservado após ' | '\n"
                "• Apenas staff pode usar\n\n"
                "**📌 Formato de Nickname:**\n"
                "`Prefixo | Nome | ID`"
            ),
            color=discord.Color.blue()
        )
        
        # Exemplos de nickname
        embed.add_field(
            name="🎯 Exemplos de Nickname",
            value=(
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
            inline=False
        )
        
        embed.add_field(
            name="👑 Staff Permitido",
            value="\n".join([c.split(' | ')[0] if ' | ' in c else c for c in STAFF_ROLES[:6]]) + "\n...",
            inline=False
        )
        
        embed.set_footer(text="Sistema Clean • Busca flexível • Mensagens auto-deletam em 5s")
        
        view = CleanCargoView()
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="fixnick")
    async def fixnick(self, ctx, member: discord.Member = None):
        """Corrige nickname manualmente"""
        if member is None:
            member = ctx.author
        
        # Verificar permissão (só staff pode corrigir outros) - usando busca flexível
        if member != ctx.author:
            is_staff = False
            for role in ctx.author.roles:
                for cargo_staff in STAFF_ROLES:
                    if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                        is_staff = True
                        break
                if is_staff:
                    break
            
            if not is_staff and not ctx.author.guild_permissions.administrator:
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
