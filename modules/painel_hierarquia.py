import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os
import re

# ========== CONFIGURAÇÃO ==========
# Cargos em ordem hierárquica (do maior para o menor)
CARGOS_HIERARQUIA = [
    {"nome": "👑 Lider 00", "emoji": "👑", "display": "00"},
    {"nome": "💎 Lider 01", "emoji": "💎", "display": "01"},
    {"nome": "👮 Lider 02", "emoji": "👮", "display": "02"},
    {"nome": "🎖️ Lider 03", "emoji": "🎖️", "display": "03"},
    {"nome": "🎖️ Gerente Geral", "emoji": "📊", "display": "G.Geral"},
    {"nome": "🎖️ Gerente De Farm", "emoji": "🌾", "display": "G.Farm"},
    {"nome": "🎖️ Gerente De Pista", "emoji": "🏁", "display": "G.Pista"},
    {"nome": "🎖️ Gerente de Recrutamento", "emoji": "🤝", "display": "G.Rec"},
    {"nome": "🎖️ Supervisor", "emoji": "👁️", "display": "Sup"},
    {"nome": "🎖️ Recrutador", "emoji": "🔍", "display": "Rec"},
    {"nome": "🎖️ Ceo Elite", "emoji": "👑", "display": "Ceo E"},
    {"nome": "🎖️ Sub Elite", "emoji": "⭐", "display": "Sub E"},
    {"nome": "🎖️ Elite", "emoji": "✨", "display": "E"},
    {"nome": "🙅‍♂️ Membro", "emoji": "👤", "display": "M"},
]

# Arquivo para salvar o painel
ARQUIVO_PAINEIS = "paineis_hierarquia.json"

def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def get_cargo_display(role_name: str) -> str:
    """Retorna o display name do cargo baseado no nome real"""
    for cargo in CARGOS_HIERARQUIA:
        if normalizar_nome(cargo["nome"]) == normalizar_nome(role_name):
            return cargo["display"]
    return "?"

def get_cargo_emoji(role_name: str) -> str:
    """Retorna o emoji do cargo baseado no nome real"""
    for cargo in CARGOS_HIERARQUIA:
        if normalizar_nome(cargo["nome"]) == normalizar_nome(role_name):
            return cargo["emoji"]
    return "❓"

# ========== VIEW DO PAINEL ==========
class PainelHierarquiaView(ui.View):
    """View com botões para navegação"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🔄 Atualizar", style=ButtonStyle.primary, emoji="🔄", custom_id="hierarquia_atualizar")
    async def atualizar(self, interaction: discord.Interaction, button: ui.Button):
        """Atualiza o painel manualmente"""
        cog = interaction.client.get_cog("PainelHierarquia")
        if not cog:
            await interaction.response.send_message("❌ Erro ao atualizar painel!", ephemeral=True)
            return
        
        embed = cog.criar_embed_hierarquia(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

# ========== COG PRINCIPAL ==========
class PainelHierarquiaCog(commands.Cog, name="PainelHierarquia"):
    """Sistema de Painel de Hierarquia"""
    
    def __init__(self, bot):
        self.bot = bot
        self.paineis_ativos = {}  # {guild_id: {"canal_id": canal_id, "mensagem_id": mensagem_id}}
        print("✅ Módulo PainelHierarquia carregado!")
    
    def criar_embed_hierarquia(self, guild):
        """Cria o embed com a hierarquia completa do servidor"""
        
        # Organizar membros por cargo
        membros_por_cargo = {cargo["display"]: [] for cargo in CARGOS_HIERARQUIA}
        
        for member in guild.members:
            if member.bot:
                continue  # Ignorar bots
            
            # Encontrar o cargo mais alto do membro
            cargo_encontrado = None
            for cargo_info in CARGOS_HIERARQUIA:
                for role in member.roles:
                    if normalizar_nome(role.name) == normalizar_nome(cargo_info["nome"]):
                        cargo_encontrado = cargo_info["display"]
                        break
                if cargo_encontrado:
                    break
            
            if cargo_encontrado:
                # Adicionar à lista do cargo
                nome_exibicao = member.display_name
                if member.nick:
                    # Tentar extrair apenas o nome (sem prefixo e ID)
                    partes = member.nick.split(' | ')
                    if len(partes) >= 2:
                        nome_exibicao = partes[1].strip()
                
                membros_por_cargo[cargo_encontrado].append({
                    "nome": nome_exibicao,
                    "mention": member.mention,
                    "nick": member.nick or member.name
                })
        
        # Criar o embed
        embed = discord.Embed(
            title="📋 **HIERARQUIA DO SERVIDOR**",
            description="Estrutura organizacional completa do servidor",
            color=discord.Color.gold()
        )
        
        # Adicionar campos para cada cargo (do maior para o menor)
        total_membros = 0
        for cargo_info in CARGOS_HIERARQUIA:
            display = cargo_info["display"]
            emoji = cargo_info["emoji"]
            membros = membros_por_cargo.get(display, [])
            quantidade = len(membros)
            total_membros += quantidade
            
            if quantidade == 0:
                valor = "`Nenhum membro`"
            elif quantidade <= 5:
                # Mostrar todos se forem poucos
                nomes = []
                for m in membros:
                    # Limitar tamanho do nome
                    nome = m["nome"][:20]
                    nomes.append(f"`{nome}`")
                valor = ", ".join(nomes)
            else:
                # Mostrar os primeiros 5 e indicar quantos mais
                nomes = []
                for m in membros[:5]:
                    nome = m["nome"][:20]
                    nomes.append(f"`{nome}`")
                valor = ", ".join(nomes) + f" e mais {quantidade - 5}"
            
            embed.add_field(
                name=f"{emoji} **{display}** ─ `{quantidade}`",
                value=valor[:1024] or "`Nenhum membro`",  # Discord limit
                inline=False
            )
        
        # Total de membros
        embed.add_field(
            name="📊 **TOTAL**",
            value=f"`{total_membros}` membros organizados",
            inline=False
        )
        
        embed.set_footer(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        embed.timestamp = datetime.now()
        
        return embed
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Atualiza painéis quando um membro muda de cargo"""
        if before.roles != after.roles:
            await self.atualizar_todos_paineis(after.guild)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Atualiza painéis quando um novo membro entra"""
        await self.atualizar_todos_paineis(member.guild)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Atualiza painéis quando um membro sai"""
        await self.atualizar_todos_paineis(member.guild)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Quando o bot inicia, recarrega painéis existentes"""
        print("✅ PainelHierarquia cog pronto!")
        await self.carregar_paineis()
    
    async def carregar_paineis(self):
        """Tenta carregar painéis salvos anteriormente"""
        try:
            if os.path.exists(ARQUIVO_PAINEIS):
                with open(ARQUIVO_PAINEIS, 'r', encoding='utf-8') as f:
                    self.paineis_ativos = json.load(f)
                
                print(f"📋 Carregando {len(self.paineis_ativos)} painéis de hierarquia salvos...")
                
                for guild_id, dados in list(self.paineis_ativos.items()):
                    try:
                        guild = self.bot.get_guild(int(guild_id))
                        if not guild:
                            continue
                        
                        canal = guild.get_channel(dados["canal_id"])
                        if not canal:
                            continue
                        
                        try:
                            mensagem = await canal.fetch_message(dados["mensagem_id"])
                            self.bot.add_view(PainelHierarquiaView(), message_id=mensagem.id)
                            print(f"  ✅ Painel recuperado em #{canal.name} ({guild.name})")
                        except:
                            del self.paineis_ativos[guild_id]
                    except:
                        continue
                
                self.salvar_paineis()
        except:
            self.paineis_ativos = {}
    
    def salvar_paineis(self):
        """Salva os painéis ativos em arquivo"""
        try:
            with open(ARQUIVO_PAINEIS, 'w', encoding='utf-8') as f:
                json.dump(self.paineis_ativos, f, indent=4)
        except:
            pass
    
    async def atualizar_todos_paineis(self, guild=None):
        """Atualiza todos os painéis ou de um servidor específico"""
        if guild:
            # Atualizar apenas de um servidor
            guild_id = str(guild.id)
            if guild_id in self.paineis_ativos:
                await self._atualizar_painel_guild(guild)
        else:
            # Atualizar todos
            print("🔄 Atualizando todos os painéis de hierarquia...")
            for guild_id in list(self.paineis_ativos.keys()):
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        await self._atualizar_painel_guild(guild)
                except:
                    continue
    
    async def _atualizar_painel_guild(self, guild):
        """Atualiza o painel de um servidor específico"""
        try:
            dados = self.paineis_ativos.get(str(guild.id))
            if not dados:
                return
            
            canal = guild.get_channel(dados["canal_id"])
            if not canal:
                return
            
            try:
                mensagem = await canal.fetch_message(dados["mensagem_id"])
                embed = self.criar_embed_hierarquia(guild)
                await mensagem.edit(embed=embed)
                print(f"  ✅ Painel de hierarquia atualizado em #{canal.name}")
            except Exception as e:
                print(f"  ❌ Erro ao atualizar painel: {e}")
                del self.paineis_ativos[str(guild.id)]
                self.salvar_paineis()
        except:
            pass
    
    @commands.command(name="setup_hierarquia", aliases=["hierarquia"])
    @commands.has_permissions(administrator=True)
    async def setup_hierarquia(self, ctx):
        """📋 Configura o painel de hierarquia no canal atual"""
        
        # Verificar se já existe um painel neste servidor
        if str(ctx.guild.id) in self.paineis_ativos:
            embed_confirm = discord.Embed(
                title="⚠️ Painel já existente",
                description="Já existe um painel de hierarquia configurado neste servidor. Deseja substituir pelo novo?",
                color=discord.Color.orange()
            )
            
            view = ConfirmaSubstituirView(self, ctx)
            await ctx.send(embed=embed_confirm, view=view)
            return
        
        await self.criar_novo_painel(ctx)
    
    async def criar_novo_painel(self, ctx):
        """Cria um novo painel no canal"""
        
        embed = self.criar_embed_hierarquia(ctx.guild)
        view = PainelHierarquiaView()
        
        mensagem = await ctx.send(embed=embed, view=view)
        
        self.paineis_ativos[str(ctx.guild.id)] = {
            "canal_id": ctx.channel.id,
            "mensagem_id": mensagem.id
        }
        self.salvar_paineis()
        
        self.bot.add_view(PainelHierarquiaView(), message_id=mensagem.id)
        
        confirm = await ctx.send("✅ **Painel de hierarquia criado com sucesso!** Ele será atualizado automaticamente.")
        await asyncio.sleep(3)
        await confirm.delete()
        await ctx.message.delete()

# ========== VIEW DE CONFIRMAÇÃO ==========
class ConfirmaSubstituirView(ui.View):
    """View para confirmar substituição do painel"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="✅ Sim, substituir", style=ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if str(self.ctx.guild.id) in self.cog.paineis_ativos:
            del self.cog.paineis_ativos[str(self.ctx.guild.id)]
            self.cog.salvar_paineis()
        
        await self.cog.criar_novo_painel(self.ctx)
        await interaction.message.delete()
    
    @ui.button(label="❌ Não, cancelar", style=ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(PainelHierarquiaCog(bot))
    print("✅ Sistema de Painel de Hierarquia configurado!")
