import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os
import re

# ========== CONFIGURAÇÃO ==========
ARQUIVO_PAINEIS = "paineis_hierarquia.json"

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
            
        role_nome = role.name.lower()
        
        # VERIFICAÇÃO ESPECÍFICA PARA ELITES
        if "ceo" in role_nome and "elite" in role_nome:
            cargos_membro.append({
                "display": "Ceo Elite",
                "emoji": "👑",
                "prioridade": 11
            })
            continue
            
        if "sub" in role_nome and "elite" in role_nome:
            cargos_membro.append({
                "display": "Sub Elite",
                "emoji": "⭐",
                "prioridade": 12
            })
            continue
            
        if "elite" in role_nome and "sub" not in role_nome and "ceo" not in role_nome:
            cargos_membro.append({
                "display": "Elite",
                "emoji": "✨",
                "prioridade": 13
            })
            continue
        
        # Para os outros cargos
        role_normalizado = normalizar_para_comparacao(role.name)
        
        for cargo_info in cargos_config:
            if cargo_info["display"] in ["Ceo Elite", "Sub Elite", "Elite"]:
                continue
                
            cargo_normalizado = normalizar_para_comparacao(cargo_info["nome"])
            
            if (role_normalizado == cargo_normalizado or 
                cargo_normalizado in role_normalizado or 
                role_normalizado in cargo_normalizado):
                
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

class PainelHierarquiaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🔄 Atualizar", style=ButtonStyle.primary, emoji="🔄", custom_id="hierarquia_atualizar")
    async def atualizar(self, interaction: discord.Interaction, button: ui.Button):
        cog = interaction.client.get_cog("PainelHierarquia")
        if not cog:
            await interaction.response.send_message("❌ Erro ao atualizar painel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        async for msg in interaction.channel.history(limit=50):
            if msg.author == interaction.client.user and msg.embeds:
                for embed in msg.embeds:
                    if embed.title and any(t in embed.title for t in ["LIDERANÇA", "GERÊNCIA", "SUPERVISÃO", "ELITES", "MEMBROS", "TOTAL"]):
                        await msg.delete()
                        break
        
        embeds = cog.criar_embeds_hierarquia(interaction.guild)
        mensagens = await cog.enviar_multiplas_mensagens(interaction.channel, embeds, view=self)
        
        if mensagens:
            cog.paineis_ativos[str(interaction.guild.id)] = {
                "canal_id": interaction.channel.id,
                "mensagem_id": mensagens[0].id
            }
            cog.salvar_paineis()

class PainelHierarquia(commands.Cog, name="PainelHierarquia"):
    def __init__(self, bot):
        self.bot = bot
        self.paineis_ativos = {}
        print("✅ Módulo PainelHierarquia carregado!")
    
    async def enviar_multiplas_mensagens(self, channel, embeds, view=None):
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
        membros_por_cargo = {cargo["display"]: [] for cargo in CARGOS_REAIS}
        
        for member in guild.members:
            if member.bot:
                continue
            
            cargo_mais_alto = encontrar_cargo_mais_alto(member, CARGOS_REAIS)
            if cargo_mais_alto:
                membros_por_cargo[cargo_mais_alto["display"]].append(member)
        
        todos_embeds = []
        
        # LIDERANÇA
        embed1 = discord.Embed(title="👑 **LIDERANÇA**", color=discord.Color.gold())
        for idx in [0, 1, 2, 3]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            valor = " ".join([m.mention for m in membros]) if membros else "`Lugar Disponível`"
            embed1.add_field(name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`", value=valor, inline=False)
        todos_embeds.append(embed1)
        
        # GERÊNCIA
        embed2 = discord.Embed(title="📊 **GERÊNCIA**", color=discord.Color.blue())
        for idx in [4, 5, 6, 7]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            valor = " ".join([m.mention for m in membros]) if membros else "`Lugar Disponível`"
            embed2.add_field(name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`", value=valor, inline=False)
        todos_embeds.append(embed2)
        
        # SUPERVISÃO
        embed3 = discord.Embed(title="🔍 **SUPERVISÃO**", color=discord.Color.green())
        for idx in [8, 9]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            valor = " ".join([m.mention for m in membros]) if membros else "`Lugar Disponível`"
            embed3.add_field(name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`", value=valor, inline=False)
        todos_embeds.append(embed3)
        
        # ELITES
        embed4 = discord.Embed(title="👑 **ELITES**", color=discord.Color.purple())
        for idx in [10, 11, 12]:
            cargo = CARGOS_REAIS[idx]
            membros = membros_por_cargo[cargo["display"]]
            print(f"  {cargo['display']}: {len(membros)} membros")
            valor = " ".join([m.mention for m in membros]) if membros else "`Lugar Disponível`"
            embed4.add_field(name=f"{cargo['emoji']} **{cargo['display']}** ─ `{len(membros)}`", value=valor, inline=False)
        todos_embeds.append(embed4)
        
        # MEMBROS
        cargo_membro = CARGOS_REAIS[13]
        membros_membro = membros_por_cargo[cargo_membro["display"]]
        
        if membros_membro:
            membros_membro.sort(key=lambda m: m.name.lower())
            texto_atual = ""
            numero_mensagem = 1
            
            for i, membro in enumerate(membros_membro, 1):
                mencao = f"{membro.mention} "
                
                if len(texto_atual + mencao) > 900:
                    titulo = "**MEMBROS:**" if numero_mensagem == 1 else f"**MEMBROS {numero_mensagem}:**"
                    embed = discord.Embed(title=titulo, description=texto_atual, color=discord.Color.light_grey())
                    todos_embeds.append(embed)
                    
                    numero_mensagem += 1
                    texto_atual = mencao
                else:
                    texto_atual += mencao
                
                if i % 5 == 0:
                    texto_atual += "\n"
            
            if texto_atual:
                titulo = "**MEMBROS:**" if numero_mensagem == 1 else f"**MEMBROS {numero_mensagem}:**"
                embed = discord.Embed(title=titulo, description=texto_atual, color=discord.Color.light_grey())
                todos_embeds.append(embed)
        else:
            embed = discord.Embed(title="**MEMBROS:**", description="`Lugar Disponível`", color=discord.Color.light_grey())
            todos_embeds.append(embed)
        
        # TOTAL
        total_membros = sum(len(membros) for membros in membros_por_cargo.values())
        embed_total = discord.Embed(title="📊 **TOTAL**", description=f"**{total_membros}** membros no servidor", color=discord.Color.blue())
        embed_total.set_footer(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        todos_embeds.append(embed_total)
        
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
        except:
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
                async for msg in canal.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        for embed in msg.embeds:
                            if embed.title and any(t in embed.title for t in ["LIDERANÇA", "GERÊNCIA", "SUPERVISÃO", "ELITES", "MEMBROS", "TOTAL"]):
                                await msg.delete()
                                break
                
                embeds = self.criar_embeds_hierarquia(guild)
                mensagens = await self.enviar_multiplas_mensagens(canal, embeds, view=PainelHierarquiaView())
                
                if mensagens:
                    self.paineis_ativos[str(guild.id)]["mensagem_id"] = mensagens[0].id
                    self.salvar_paineis()
            except:
                del self.paineis_ativos[str(guild.id)]
                self.salvar_paineis()
        except:
            pass
    
    @commands.command(name="setup_hierarquia", aliases=["hierarquia"])
    @commands.has_permissions(administrator=True)
    async def setup_hierarquia(self, ctx):
        if not ctx.guild:
            await ctx.send("❌ Este comando só pode ser usado em servidores!")
            return
        
        if str(ctx.guild.id) in self.paineis_ativos:
            embed_confirm = discord.Embed(title="⚠️ Painel já existente", description="Já existe um painel configurado. Deseja substituir?", color=discord.Color.orange())
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
                
                for msg in mensagens:
                    self.bot.add_view(PainelHierarquiaView(), message_id=msg.id)
                
                confirm = await ctx.send(f"✅ **Painel criado com sucesso!** ({len(mensagens)} mensagens)")
                await asyncio.sleep(3)
                await confirm.delete()
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"❌ Erro ao criar painel: {str(e)}")

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

async def setup(bot):
    await bot.add_cog(PainelHierarquia(bot))
    print("✅ Sistema de Painel de Hierarquia configurado!")
