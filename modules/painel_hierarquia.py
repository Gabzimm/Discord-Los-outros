import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os
import re

# ========== CONFIGURAÇÃO ==========
# Arquivo para salvar o painel
ARQUIVO_PAINEIS = "paineis_hierarquia.json"

# Mapeamento de nomes de cargos REAIS para exibição (em ORDEM DECRESCENTE - do maior para o menor)
CARGOS_REAIS = [
    {"nome": "👑 | Lider | 00", "display": "00", "emoji": "👑", "prioridade": 1},
    {"nome": "💎 | Lider | 01", "display": "01", "emoji": "💎", "prioridade": 2},
    {"nome": "👮 | Lider | 02", "display": "02", "emoji": "👮", "prioridade": 3},
    {"nome": "🎖️ | Lider | 03", "display": "03", "emoji": "🎖️", "prioridade": 4},
    {"nome": "🎖️ | Gerente Geral", "display": "G.Geral", "emoji": "📊", "prioridade": 5},
    {"nome": "🎖️ | Gerente De Farm", "display": "G.Farm", "emoji": "🌾", "prioridade": 6},
    {"nome": "🎖️ | Gerente De Pista", "display": "G.Pista", "emoji": "🏁", "prioridade": 7},
    {"nome": "🎖️ | Gerente de Recrutamento", "display": "G.Rec", "emoji": "🤝", "prioridade": 8},
    {"nome": "🎖️ | Supervisor", "display": "Sup", "emoji": "👁️", "prioridade": 9},
    {"nome": "🎖️ | Recrutador", "display": "Rec", "emoji": "🔍", "prioridade": 10},
    {"nome": "🎖️ | Ceo Elite", "display": "Ceo E", "emoji": "👑", "prioridade": 11},
    {"nome": "🎖️ | Sub Elite", "display": "Sub E", "emoji": "⭐", "prioridade": 12},
    {"nome": "🎖️ | Elite", "display": "E", "emoji": "✨", "prioridade": 13},
    {"nome": "🙅‍♂️ | Membro", "display": "M", "emoji": "👤", "prioridade": 14},
]

def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def extrair_nome_limpo(nickname: str) -> str:
    """Extrai apenas o nome do usuário (sem prefixo e ID)"""
    if not nickname:
        return None
    
    # Formato esperado: "00 | Nome | ID" ou "M | Nome | ID"
    partes = nickname.split(' | ')
    if len(partes) >= 2:
        return partes[1].strip()
    
    return nickname

def encontrar_cargo_mais_alto(member, cargos_config):
    """Encontra o CARGO MAIS ALTO do membro baseado na prioridade"""
    cargos_membro = []
    
    for role in member.roles:
        for cargo_info in cargos_config:
            if normalizar_nome(role.name) == normalizar_nome(cargo_info["nome"]):
                cargos_membro.append({
                    "nome": cargo_info["nome"],
                    "display": cargo_info["display"],
                    "emoji": cargo_info["emoji"],
                    "prioridade": cargo_info["prioridade"]
                })
                break
    
    if not cargos_membro:
        return None
    
    # Ordenar por prioridade (menor número = mais alto)
    cargos_membro.sort(key=lambda x: x["prioridade"])
    
    # Retornar o cargo mais alto (menor prioridade)
    return cargos_membro[0]

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
        """Cria o embed com a hierarquia completa - TODOS OS CARGOS VISÍVEIS"""
        
        # Dicionário para armazenar membros por cargo
        membros_por_cargo = {cargo["display"]: [] for cargo in CARGOS_REAIS}
        
        # Percorrer todos os membros do servidor
        for member in guild.members:
            if member.bot:
                continue  # Ignorar bots
            
            # Encontrar o CARGO MAIS ALTO do membro
            cargo_mais_alto = encontrar_cargo_mais_alto(member, CARGOS_REAIS)
            
            if cargo_mais_alto:
                display = cargo_mais_alto["display"]
                
                # Extrair nome limpo (sem prefixo e ID)
                nome_limpo = extrair_nome_limpo(member.nick or member.name)
                if not nome_limpo:
                    nome_limpo = member.name.split('#')[0]
                
                # Adicionar à lista do cargo correto
                membros_por_cargo[display].append({
                    "nome": nome_limpo,
                    "mention": member.mention,
                    "nick_completo": member.nick or member.name
                })
        
        # Criar o embed
        embed = discord.Embed(
            title="📋 **HIERARQUIA DO SERVIDOR**",
            description="Estrutura completa de cargos do servidor:",
            color=discord.Color.gold()
        )
        
        total_membros = 0
        
        # MOSTRAR TODOS OS CARGOS, mesmo com 0 membros
        for cargo_info in sorted(CARGOS_REAIS, key=lambda x: x["prioridade"]):
            display = cargo_info["display"]
            emoji = cargo_info["emoji"]
            membros = membros_por_cargo.get(display, [])
            quantidade = len(membros)
            total_membros += quantidade
            
            if quantidade == 0:
                # Mostrar que não tem ninguém neste cargo
                valor = "`Nenhum membro`"
            else:
                # Criar lista com todos os membros
                lista_membros = []
                for m in membros:
                    lista_membros.append(m["mention"])
                
                valor = ", ".join(lista_membros)
                
                # Se ultrapassar o limite, dividir em múltiplos campos
                if len(valor) > 1024:
                    partes = []
                    parte_atual = []
                    tamanho_atual = 0
                    
                    for m in membros:
                        menc = m["mention"]
                        if tamanho_atual + len(menc) + 2 > 1000:
                            partes.append(", ".join(parte_atual))
                            parte_atual = [menc]
                            tamanho_atual = len(menc)
                        else:
                            if parte_atual:
                                tamanho_atual += len(menc) + 2
                            else:
                                tamanho_atual += len(menc)
                            parte_atual.append(menc)
                    
                    if parte_atual:
                        partes.append(", ".join(parte_atual))
                    
                    # Primeira parte
                    embed.add_field(
                        name=f"{emoji} **{display}** ─ `{quantidade}`",
                        value=partes[0][:1024],
                        inline=False
                    )
                    
                    # Partes adicionais
                    for i, parte in enumerate(partes[1:], 1):
                        embed.add_field(
                            name=f"{emoji} **{display}** (cont. {i})",
                            value=parte[:1024],
                            inline=False
                        )
                else:
                    embed.add_field(
                        name=f"{emoji} **{display}** ─ `{quantidade}`",
                        value=valor[:1024],
                        inline=False
                    )
        
        # Total de membros
        embed.add_field(
            name="📊 **TOTAL**",
            value=f"`{total_membros}` membros no servidor",
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
        
        confirm = await ctx.send("✅ **Painel de hierarquia criado com sucesso!** Todos os cargos são mostrados.")
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
