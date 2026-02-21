import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os

# ========== CONFIGURAÇÃO ==========
ARQUIVO_RECRUTADORES = "recrutadores.json"

class GerenciadorRecrutadores:
    """Gerencia os dados de recrutadores"""
    
    def __init__(self):
        self.recrutadores = {}  # {recrutador_id: {"nome": nome, "total": 0}}
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados do arquivo JSON"""
        try:
            if os.path.exists(ARQUIVO_RECRUTADORES):
                with open(ARQUIVO_RECRUTADORES, 'r', encoding='utf-8') as f:
                    self.recrutadores = json.load(f)
                print(f"✅ Dados de recrutadores carregados: {len(self.recrutadores)} recrutadores")
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            self.recrutadores = {}
    
    def salvar_dados(self):
        """Salva dados no arquivo JSON"""
        try:
            with open(ARQUIVO_RECRUTADORES, 'w', encoding='utf-8') as f:
                json.dump(self.recrutadores, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome):
        """Adiciona +1 ao total do recrutador"""
        recrutador_id = str(recrutador_id)
        
        if recrutador_id not in self.recrutadores:
            self.recrutadores[recrutador_id] = {
                "nome": recrutador_nome,
                "total": 0
            }
        
        self.recrutadores[recrutador_id]["total"] += 1
        self.recrutadores[recrutador_id]["nome"] = recrutador_nome  # Atualiza nome
        self.salvar_dados()
        
        print(f"✅ Recrutamento adicionado: {recrutador_nome} agora tem {self.recrutadores[recrutador_id]['total']} recrutas")
    
    def get_top_recrutadores(self, limite=10):
        """Retorna os top recrutadores"""
        # Converter para lista e ordenar
        lista = []
        for rid, dados in self.recrutadores.items():
            lista.append({
                "id": rid,
                "nome": dados["nome"],
                "total": dados["total"]
            })
        
        # Ordenar por total (maior primeiro)
        lista.sort(key=lambda x: x["total"], reverse=True)
        return lista[:limite]
    
    def get_total_geral(self):
        """Retorna total de recrutamentos"""
        total = 0
        for dados in self.recrutadores.values():
            total += dados["total"]
        return total
    
    def get_total_recrutadores(self):
        """Retorna número de recrutadores ativos"""
        return len(self.recrutadores)

# ========== VIEW DO PAINEL ==========
class PainelRecView(ui.View):
    """View com botões para o painel"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🔄 Atualizar", style=ButtonStyle.primary, custom_id="painel_rec_atualizar", row=0)
    async def atualizar(self, interaction: discord.Interaction, button: ui.Button):
        """Atualiza o painel manualmente"""
        # Buscar o cog para acessar o gerenciador
        cog = interaction.client.get_cog("PainelRec")
        if not cog:
            await interaction.response.send_message("❌ Erro ao atualizar painel!", ephemeral=True)
            return
        
        # Criar novo embed
        embed = cog.criar_embed_painel(interaction.guild)
        
        # Editar mensagem
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="📊 Estatísticas", style=ButtonStyle.secondary, custom_id="painel_rec_estatisticas", row=0)
    async def estatisticas(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra estatísticas detalhadas"""
        cog = interaction.client.get_cog("PainelRec")
        if not cog:
            await interaction.response.send_message("❌ Erro!", ephemeral=True)
            return
        
        total_geral = cog.gerenciador.get_total_geral()
        total_recrutadores = cog.gerenciador.get_total_recrutadores()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Recrutamento",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total de Recrutamentos", value=f"**{total_geral}**", inline=True)
        embed.add_field(name="Recrutadores Ativos", value=f"**{total_recrutadores}**", inline=True)
        
        if total_geral > 0:
            media = total_geral / total_recrutadores if total_recrutadores > 0 else 0
            embed.add_field(name="Média por Recrutador", value=f"**{media:.1f}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== COG PRINCIPAL ==========
class PainelRecCog(commands.Cog, name="PainelRec"):
    """Sistema de Painel de Recrutadores"""
    
    def __init__(self, bot):
        self.bot = bot
        self.gerenciador = GerenciadorRecrutadores()
        self.paineis_ativos = {}  # {guild_id: {"canal_id": canal_id, "mensagem_id": mensagem_id}}
        print("✅ Módulo PainelRec carregado!")
    
    def criar_embed_painel(self, guild):
        """Cria o embed do painel"""
        top = self.gerenciador.get_top_recrutadores(10)
        total_geral = self.gerenciador.get_total_geral()
        
        embed = discord.Embed(
            title="🏆 **PAINEL DE RECRUTADORES**",
            description="Ranking dos melhores recrutadores do servidor!",
            color=discord.Color.gold()
        )
        
        if not top:
            embed.add_field(
                name="📊 Nenhum recrutamento ainda",
                value="Seja o primeiro a recrutar alguém e apareça aqui!",
                inline=False
            )
        else:
            # Top 3 com medalhas
            for i, rec in enumerate(top[:3], 1):
                if i == 1:
                    medalha = "🥇 **1º Lugar**"
                    cor = "🥇"
                elif i == 2:
                    medalha = "🥈 **2º Lugar**"
                    cor = "🥈"
                else:
                    medalha = "🥉 **3º Lugar**"
                    cor = "🥉"
                
                embed.add_field(
                    name=f"{medalha}",
                    value=f"**{rec['nome']}**\n{cor} `{rec['total']}` recruta(s)",
                    inline=False
                )
            
            # Demais posições (4º em diante)
            if len(top) > 3:
                outros = ""
                for i, rec in enumerate(top[3:], 4):
                    outros += f"`{i}º` **{rec['nome']}** — `{rec['total']}` recruta(s)\n"
                
                embed.add_field(
                    name="📋 **Demais Posições**",
                    value=outros,
                    inline=False
                )
        
        # Rodapé com estatísticas
        embed.set_footer(text=f"📊 Total de recrutamentos: {total_geral} • Atualizado automaticamente")
        embed.timestamp = datetime.now()
        
        return embed
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Quando o bot inicia, recarrega painéis existentes"""
        print("✅ PainelRec cog pronto!")
        
        # Tentar carregar painéis salvos
        await self.carregar_paineis()
    
    async def carregar_paineis(self):
        """Tenta carregar painéis salvos anteriormente"""
        try:
            if os.path.exists("paineis_rec.json"):
                with open("paineis_rec.json", 'r', encoding='utf-8') as f:
                    self.paineis_ativos = json.load(f)
                
                print(f"📋 Carregando {len(self.paineis_ativos)} painéis salvos...")
                
                # Para cada painel salvo, tentar recuperar a mensagem
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
                            # Se conseguiu, registrar a view novamente
                            self.bot.add_view(PainelRecView(), message_id=mensagem.id)
                            print(f"  ✅ Painel recuperado em #{canal.name} ({guild.name})")
                        except:
                            # Mensagem não existe mais, remover
                            del self.paineis_ativos[guild_id]
                    except:
                        continue
                
                # Salvar versão limpa
                self.salvar_paineis()
        except:
            self.paineis_ativos = {}
    
    def salvar_paineis(self):
        """Salva os painéis ativos em arquivo"""
        try:
            with open("paineis_rec.json", 'w', encoding='utf-8') as f:
                json.dump(self.paineis_ativos, f, indent=4)
        except:
            pass
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome):
        """Método público para outros módulos adicionarem recrutamentos"""
        self.gerenciador.adicionar_recrutamento(recrutador_id, recrutador_nome)
        
        # Atualizar todos os painéis ativos
        asyncio.create_task(self.atualizar_todos_paineis())
    
    async def atualizar_todos_paineis(self):
        """Atualiza todos os painéis ativos"""
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
                    embed = self.criar_embed_painel(guild)
                    await mensagem.edit(embed=embed)
                except:
                    # Mensagem não existe mais, remover
                    del self.paineis_ativos[guild_id]
                    self.salvar_paineis()
            except:
                continue
    
    @commands.command(name="setup_painel", aliases=["painel"])
    @commands.has_permissions(administrator=True)
    async def setup_painel(self, ctx):
        """🏆 Configura o painel de recrutadores no canal atual"""
        
        # Verificar se já existe um painel neste servidor
        if str(ctx.guild.id) in self.paineis_ativos:
            # Perguntar se quer substituir
            embed_confirm = discord.Embed(
                title="⚠️ Painel já existente",
                description="Já existe um painel configurado neste servidor. Deseja substituir pelo novo?",
                color=discord.Color.orange()
            )
            
            # Botões de confirmação
            view = ConfirmaSubstituirView(self, ctx)
            await ctx.send(embed=embed_confirm, view=view)
            return
        
        await self.criar_novo_painel(ctx)
    
    async def criar_novo_painel(self, ctx):
        """Cria um novo painel no canal"""
        
        embed = self.criar_embed_painel(ctx.guild)
        view = PainelRecView()
        
        mensagem = await ctx.send(embed=embed, view=view)
        
        # Salvar painel
        self.paineis_ativos[str(ctx.guild.id)] = {
            "canal_id": ctx.channel.id,
            "mensagem_id": mensagem.id
        }
        self.salvar_paineis()
        
        # Registrar view para persistência
        self.bot.add_view(PainelRecView(), message_id=mensagem.id)
        
        # Mensagem de confirmação (auto-delete)
        confirm = await ctx.send("✅ **Painel criado com sucesso!** O ranking será atualizado automaticamente.")
        await asyncio.sleep(3)
        await confirm.delete()
        await ctx.message.delete()
    
    @commands.command(name="rec_stats")
    @commands.has_permissions(administrator=True)
    async def rec_stats(self, ctx):
        """📊 Mostra estatísticas detalhadas"""
        
        total_geral = self.gerenciador.get_total_geral()
        total_recrutadores = self.gerenciador.get_total_recrutadores()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Recrutamento",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total de Recrutamentos", value=f"**{total_geral}**", inline=True)
        embed.add_field(name="Recrutadores Ativos", value=f"**{total_recrutadores}**", inline=True)
        
        if total_geral > 0:
            media = total_geral / total_recrutadores if total_recrutadores > 0 else 0
            embed.add_field(name="Média por Recrutador", value=f"**{media:.1f}**", inline=True)
        
        # Top 3
        top = self.gerenciador.get_top_recrutadores(3)
        if top:
            top_text = ""
            for i, rec in enumerate(top, 1):
                top_text += f"`{i}º` **{rec['nome']}** — `{rec['total']}` recruta(s)\n"
            
            embed.add_field(name="🏆 Top 3 Recrutadores", value=top_text, inline=False)
        
        await ctx.send(embed=embed)
        await ctx.message.delete()
    
    @commands.command(name="rec_reset")
    @commands.has_permissions(administrator=True)
    async def rec_reset(self, ctx):
        """🔄 Reseta todos os contadores (apenas admin)"""
        
        embed_confirm = discord.Embed(
            title="⚠️ **CONFIRMAÇÃO NECESSÁRIA**",
            description="Tem certeza que deseja resetar TODOS os contadores de recrutamento?\n\nEssa ação não pode ser desfeita!",
            color=discord.Color.red()
        )
        
        view = ConfirmaResetView(self, ctx)
        await ctx.send(embed=embed_confirm, view=view)

# ========== VIEWS DE CONFIRMAÇÃO ==========
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
        
        # Remover painel antigo
        if str(self.ctx.guild.id) in self.cog.paineis_ativos:
            del self.cog.paineis_ativos[str(self.ctx.guild.id)]
            self.cog.salvar_paineis()
        
        # Criar novo
        await self.cog.criar_novo_painel(self.ctx)
        
        # Apagar mensagem de confirmação
        await interaction.message.delete()
    
    @ui.button(label="❌ Não, cancelar", style=ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

class ConfirmaResetView(ui.View):
    """View para confirmar reset dos contadores"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="✅ SIM, RESETAR TUDO", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Resetar dados
        self.cog.gerenciador.recrutadores = {}
        self.cog.gerenciador.salvar_dados()
        
        # Atualizar painéis
        await self.cog.atualizar_todos_paineis()
        
        await interaction.message.delete()
        await self.ctx.send("✅ **Todos os contadores foram resetados!**", delete_after=5)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(PainelRecCog(bot))
    print("✅ Sistema de Painel de Recrutadores configurado!")
