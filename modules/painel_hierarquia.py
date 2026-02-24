import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os
import re
import math

# ========== CONFIGURAÇÃO ==========
# Arquivo para salvar o painel
ARQUIVO_PAINEIS = "paineis_hierarquia.json"

# Mapeamento de nomes de cargos REAIS para exibição (em ORDEM DECRESCENTE - do maior para o menor)
CARGOS_REAIS = [
    {"nome": "👑 | Lider | 00", "display": "Lider 00", "emoji": "👑", "prioridade": 1},
    {"nome": "💎 | Lider | 01", "display": "Lider 01", "emoji": "💎", "prioridade": 2},
    {"nome": "👮 | Lider | 02", "display": "Lider 02", "emoji": "👮", "prioridade": 3},
    {"nome": "🎖️ | Lider | 03", "display": "Lider 03", "emoji": "🎖️", "prioridade": 4},
    {"nome": "🎖️ | Gerente Geral", "display": "Gerente Geral", "emoji": "📊", "prioridade": 5},
    {"nome": "🎖️ | Gerente De Farm", "display": "Gerente De Farm", "emoji": "🌾", "prioridade": 6},
    {"nome": "🎖️ | Gerente De Pista", "display": "Gerente De Pista", "emoji": "🏁", "prioridade": 7},
    {"nome": "🎖️ | Gerente de Recrutamento", "display": "Gerente de Recrutamento", "emoji": "🤝", "prioridade": 8},
    {"nome": "🎖️ | Supervisor", "display": "Supervisor", "emoji": "👁️", "prioridade": 9},
    {"nome": "🎖️ | Recrutador", "display": "Recrutador", "emoji": "🔍", "prioridade": 10},
    {"nome": "🎖️ | Ceo Elite", "display": "Ceo Elite", "emoji": "👑", "prioridade": 11},
    {"nome": "🎖️ | Sub Elite", "display": "Sub Elite", "emoji": "⭐", "prioridade": 12},
    {"nome": "🎖️ | Elite", "display": "Elite", "emoji": "✨", "prioridade": 13},
    {"nome": "🙅‍♂️ | Membro", "display": "Membro", "emoji": "👤", "prioridade": 14},
]

def normalizar_para_comparacao(texto: str) -> str:
    """Remove tudo que não é letra ou número para comparação"""
    if not texto:
        return ""
    texto_limpo = re.sub(r'[^\w\s]', '', texto)
    texto_limpo = re.sub(r'\s+', '', texto_limpo)
    return texto_limpo.lower()

def encontrar_cargo_mais_alto(member, cargos_config):
    """Encontra o CARGO MAIS ALTO do membro baseado na prioridade"""
    cargos_membro = []
    
    for role in member.roles:
        if role.name == "@everyone":
            continue
            
        role_normalizado = normalizar_para_comparacao(role.name)
        
        for cargo_info in cargos_config:
            cargo_normalizado = normalizar_para_comparacao(cargo_info["nome"])
            
            if (role_normalizado == cargo_normalizado or 
                cargo_normalizado in role_normalizado or 
                role_normalizado in cargo_normalizado or
                (cargo_info["display"] == "Elite" and "elite" in role_normalizado and "sub" not in role_normalizado and "ceo" not in role_normalizado) or
                (cargo_info["display"] == "Sub Elite" and "subelite" in role_normalizado) or
                (cargo_info["display"] == "Ceo Elite" and "ceoelite" in role_normalizado)):
                
                cargos_membro.append({
                    "display": cargo_info["display"],
                    "emoji": cargo_info["emoji"],
                    "prioridade": cargo_info["prioridade"]
                })
                break
    
    if not cargos_membro:
        return None
    
    cargos_membro.sort(key=lambda x: x["prioridade"])
    return cargos_membro[0]

# ========== VIEW DO PAINEL ==========
class PainelHierarquiaView(ui.View):
    """View com botão para atualizar"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🔄 Atualizar", style=ButtonStyle.primary, emoji="🔄", custom_id="hierarquia_atualizar")
    async def atualizar(self, interaction: discord.Interaction, button: ui.Button):
        """Atualiza o painel manualmente"""
        cog = interaction.client.get_cog("PainelHierarquia")
        if not cog:
            await interaction.response.send_message("❌ Erro ao atualizar painel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Apaga todas as mensagens antigas do painel
        channel = interaction.channel
        async for msg in channel.history(limit=50):
            if msg.author == interaction.client.user and msg.embeds:
                for embed in msg.embeds:
                    if embed.title and any(t in embed.title for t in ["LIDERANÇA", "GERÊNCIA", "SUPERVISÃO", "ELITES", "MEMBROS", "TOTAL"]):
                        await msg.delete()
                        break
        
        # Envia novo painel
        embeds = cog.criar_embeds_hierarquia(interaction.guild)
        mensagens = await cog.enviar_multiplas_mensagens(channel, embeds, view=self)
        
        if mensagens:
            cog.paineis_ativos[str(interaction.guild.id)] = {
                "canal_id": channel.id,
                "mensagem_id": mensagens[0].id
            }
            cog.salvar_paineis()

# ========== COG PRINCIPAL ==========
class PainelHierarquia(commands.Cog, name="PainelHierarquia"):
    """Sistema de Painel de Hierarquia"""
    
    def __init__(self, bot):
        self.bot = bot
        self.paineis_ativos = {}
        print("✅ Módulo PainelHierarquia carregado!")
    
    async def enviar_multiplas_mensagens(self, channel, embeds, view=None):
        """Envia múltiplos embeds, respeitando limite de 10 por mensagem"""
        mensagens = []
        embeds_atual = []
        
        for embed in embeds:
            if len(embeds_atual) >= 10:
                msg = await channel.send(embeds=embeds_atual)
                mensagens.append(msg)
                embeds_atual = []
            embeds_atual.append(embed)
        
        if embeds_atual:
            if view:
                msg = await channel.send(embeds=embeds_atual, view=view)
            else:
                msg = await channel.send(embeds=embeds_atual)
            mensagens.append(msg)
        
        return mensagens
    
    def criar_embeds_hierarquia(self, guild):
        """Cria os embeds com a hierarquia completa"""
        
        print(f"\n📊 GERANDO HIERARQUIA para {guild.name}")
        
        # Dicionário para armazenar membros por cargo
        membros_por_cargo = {cargo["display"]: [] for cargo in CARGOS_REAIS}
        
        # Coletar membros por cargo
        for member in guild.members:
            if member.bot:
                continue
            
            cargo_mais_alto = encontrar_cargo_mais_alto(member, CARGOS_REAIS)
            if cargo_mais_alto:
                membros_por_cargo[cargo_mais_alto["display"]].append(member)
        
        # Lista de todos os embeds
        todos_embeds = []
        
        # ========== LIDERANÇA ==========
        embed1 = discord.Embed(
            title="👑 **LIDERANÇA**",
            description="Estrutura de liderança do servidor",
            color=discord.Color.gold()
        )
        
        for idx in [0, 1, 2, 3]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            
            if membros:
                valor = " ".join([m.mention for m in membros])
            else:
                valor = "`Lugar Disponível`"
            
            embed1.add_field(
                name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`",
                value=valor,
                inline=False
            )
        todos_embeds.append(embed1)
        
        # ========== GERÊNCIA ==========
        embed2 = discord.Embed(
            title="📊 **GERÊNCIA**",
            description="Gerentes do servidor",
            color=discord.Color.blue()
        )
        
        for idx in [4, 5, 6, 7]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            
            if membros:
                valor = " ".join([m.mention for m in membros])
            else:
                valor = "`Lugar Disponível`"
            
            embed2.add_field(
                name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`",
                value=valor,
                inline=False
            )
        todos_embeds.append(embed2)
        
        # ========== SUPERVISÃO ==========
        embed3 = discord.Embed(
            title="🔍 **SUPERVISÃO**",
            description="Supervisores e recrutadores",
            color=discord.Color.green()
        )
        
        for idx in [8, 9]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            
            if membros:
                valor = " ".join([m.mention for m in membros])
            else:
                valor = "`Lugar Disponível`"
            
            embed3.add_field(
                name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`",
                value=valor,
                inline=False
            )
        todos_embeds.append(embed3)
        
        # ========== ELITES ==========
        embed4 = discord.Embed(
            title="👑 **ELITES**",
            description="Ceo Elite, Sub Elite e Elite",
            color=discord.Color.purple()
        )
        
        for idx in [10, 11, 12]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            
            if membros:
                valor = " ".join([m.mention for m in membros])
            else:
                valor = "`Lugar Disponível`"
            
            embed4.add_field(
                name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`",
                value=valor,
                inline=False
            )
        todos_embeds.append(embed4)
        
        # ========== MEMBROS (COM MÚLTIPLAS MENSAGENS) ==========
        cargo_membro = CARGOS_REAIS[13]
        membros_membro = membros_por_cargo[cargo_membro["display"]]
        
        print(f"\n📝 MEMBROS: {len(membros_membro)} encontrados")
        
        if membros_membro:
            # Ordena membros
            membros_membro.sort(key=lambda m: m.name.lower())
            
            texto_atual = ""
            numero_mensagem = 1
            
            for i, membro in enumerate(membros_membro, 1):
                mencao = f"{membro.mention} "
                
                # Se passar do limite, cria nova mensagem
                if len(texto_atual + mencao) > 900:
                    titulo = "**MEMBROS:**" if numero_mensagem == 1 else f"**MEMBROS {numero_mensagem}:**"
                    embed = discord.Embed(
                        title=titulo,
                        description=texto_atual,
                        color=discord.Color.light_grey()
                    )
                    todos_embeds.append(embed)
                    
                    # Prepara próxima mensagem
                    numero_mensagem += 1
                    texto_atual = mencao
                else:
                    texto_atual += mencao
                    
                # Adiciona quebra de linha a cada 5 membros
                if i % 5 == 0:
                    texto_atual += "\n"
            
            # Última mensagem
            if texto_atual:
                titulo = "**MEMBROS:**" if numero_mensagem == 1 else f"**MEMBROS {numero_mensagem}:**"
                embed = discord.Embed(
                    title=titulo,
                    description=texto_atual,
                    color=discord.Color.light_grey()
                )
                todos_embeds.append(embed)
        else:
            # Sem membros
            embed = discord.Embed(
                title="**MEMBROS:**",
                description="`Lugar Disponível`",
                color=discord.Color.light_grey()
            )
            todos_embeds.append(embed)
        
        # ========== TOTAL ==========
        total_membros = sum(len(membros) for membros in membros_por_cargo.values())
        embed_total = discord.Embed(
            title="📊 **TOTAL**",
            description=f"**{total_membros}** membros no servidor",
            color=discord.Color.blue()
        )
        embed_total.set_footer(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        embed_total.timestamp = datetime.now()
        todos_embeds.append(embed_total)
        
        print(f"✅ Total de embeds criados: {len(todos_embeds)}")
        return todos_embeds
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.atualizar_todos_paineis(after.guild)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.atualizar_todos_paineis(member.guild)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.atualizar_todos_paineis(member.guild)
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ PainelHierarquia cog pronto!")
        await self.carregar_paineis()
    
    async def carregar_paineis(self):
        try:
            if os.path.exists(ARQUIVO_PAINEIS):
                with open(ARQUIVO_PAINEIS, 'r', encoding='utf-8') as f:
                    self.paineis_ativos = json.load(f)
                
                print(f"📋 Carregando {len(self.paineis_ativos)} painéis...")
                
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
                            print(f"  ✅ Painel recuperado em #{canal.name}")
                        except:
                            del self.paineis_ativos[guild_id]
                    except:
                        continue
                
                self.salvar_paineis()
        except Exception as e:
            print(f"Erro ao carregar painéis: {e}")
            self.paineis_ativos = {}
    
    def salvar_paineis(self):
        try:
            with open(ARQUIVO_PAINEIS, 'w', encoding='utf-8') as f:
                json.dump(self.paineis_ativos, f, indent=4)
        except:
            pass
    
    async def atualizar_todos_paineis(self, guild=None):
        if guild:
            guild_id = str(guild.id)
            if guild_id in self.paineis_ativos:
                await self._atualizar_painel_guild(guild)
    
    async def _atualizar_painel_guild(self, guild):
        try:
            dados = self.paineis_ativos.get(str(guild.id))
            if not dados:
                return
            
            canal = guild.get_channel(dados["canal_id"])
            if not canal:
                return
            
            try:
                # Apaga todas as mensagens antigas do painel
                async for msg in canal.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        for embed in msg.embeds:
                            if embed.title and any(t in embed.title for t in ["LIDERANÇA", "GERÊNCIA", "SUPERVISÃO", "ELITES", "MEMBROS", "TOTAL"]):
                                await msg.delete()
                                break
                
                # Envia novo painel
                embeds = self.criar_embeds_hierarquia(guild)
                mensagens = await self.enviar_multiplas_mensagens(canal, embeds, view=PainelHierarquiaView())
                
                if mensagens:
                    self.paineis_ativos[str(guild.id)]["mensagem_id"] = mensagens[0].id
                    self.salvar_paineis()
                    
                    print(f"  ✅ Painel atualizado em #{canal.name} com {len(mensagens)} mensagens")
            except Exception as e:
                print(f"Erro ao atualizar painel: {e}")
                del self.paineis_ativos[str(guild.id)]
                self.salvar_paineis()
        except:
            pass
    
    @commands.command(name="setup_hierarquia", aliases=["hierarquia"])
    @commands.has_permissions(administrator=True)
    async def setup_hierarquia(self, ctx):
        """📋 Configura o painel de hierarquia no canal atual"""
        
        if not ctx.guild:
            await ctx.send("❌ Este comando só pode ser usado em servidores!")
            return
        
        if str(ctx.guild.id) in self.paineis_ativos:
            embed_confirm = discord.Embed(
                title="⚠️ Painel já existente",
                description="Já existe um painel configurado. Deseja substituir?",
                color=discord.Color.orange()
            )
            
            view = ConfirmaSubstituirView(self, ctx)
            await ctx.send(embed=embed_confirm, view=view)
            return
        
        await self.criar_novo_painel(ctx)
    
    async def criar_novo_painel(self, ctx):
        try:
            embeds = self.criar_embeds_hierarquia(ctx.guild)
            mensagens = await self.enviar_multiplas_mensagens(ctx.channel, embeds, view=PainelHierarquiaView())
            
            if mensagens:
                self.paineis_ativos[str(ctx.guild.id)] = {
                    "canal_id": ctx.channel.id,
                    "mensagem_id": mensagens[0].id
                }
                self.salvar_paineis()
                
                # Adiciona view em todas as mensagens
                for msg in mensagens:
                    self.bot.add_view(PainelHierarquiaView(), message_id=msg.id)
                
                confirm = await ctx.send(f"✅ **Painel criado com sucesso!** ({len(mensagens)} mensagens)")
                await asyncio.sleep(3)
                await confirm.delete()
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"❌ Erro ao criar painel: {str(e)}")
            print(f"Erro ao criar painel: {e}")

# ========== VIEW DE CONFIRMAÇÃO ==========
class ConfirmaSubstituirView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="✅ Sim, substituir", style=ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if str(self.ctx.guild.id) in self.cog.paineis_ativos:
            del self.cog.paineis_ativos[str(self.ctx.guild.id)]
            self.cog.salvar_paineis()
        
        await self.cog.criar_novo_painel(self.ctx)
        await interaction.message.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(PainelHierarquia(bot))
    print("✅ Sistema de Painel de Hierarquia configurado!")
