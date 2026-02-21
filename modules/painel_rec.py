import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os

# ========== CONFIGURAÇÃO ==========
ARQUIVO_RECRUTADORES = "recrutadores.json"
ARQUIVO_RECRUTAS = "recrutas.json"
CARGO_PERMITIDO_ID = 1393998691354018094

class GerenciadorRecrutadores:
    """Gerencia os dados de recrutadores e recrutas"""
    
    def __init__(self):
        self.recrutadores = {}  # {recrutador_id: {"nome": nome, "total": 0}}
        self.recrutas = {}  # {recruta_id: {"nome": nome, "recrutador_id": id, "pago": false, "data": ""}}
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados do arquivo JSON"""
        try:
            if os.path.exists(ARQUIVO_RECRUTADORES):
                with open(ARQUIVO_RECRUTADORES, 'r', encoding='utf-8') as f:
                    self.recrutadores = json.load(f)
                print(f"✅ Dados de recrutadores carregados: {len(self.recrutadores)} recrutadores")
            else:
                self.recrutadores = {}
            
            if os.path.exists(ARQUIVO_RECRUTAS):
                with open(ARQUIVO_RECRUTAS, 'r', encoding='utf-8') as f:
                    self.recrutas = json.load(f)
                print(f"✅ Dados de recrutas carregados: {len(self.recrutas)} recrutas")
            else:
                self.recrutas = {}
        except Exception as e:
            print(f"❌ Erro ao carregar dados: {e}")
            self.recrutadores = {}
            self.recrutas = {}
    
    def salvar_dados(self):
        """Salva dados no arquivo JSON"""
        try:
            with open(ARQUIVO_RECRUTADORES, 'w', encoding='utf-8') as f:
                json.dump(self.recrutadores, f, indent=4, ensure_ascii=False)
            
            with open(ARQUIVO_RECRUTAS, 'w', encoding='utf-8') as f:
                json.dump(self.recrutas, f, indent=4, ensure_ascii=False)
                
            print("✅ Dados salvos com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome, recruta_id, recruta_nome):
        """Adiciona um novo recruta e atualiza o contador do recrutador"""
        recrutador_id = str(recrutador_id)
        recruta_id = str(recruta_id)
        
        # Verificar se recruta já existe
        if recruta_id in self.recrutas:
            print(f"⚠️ Recruta {recruta_nome} já existe!")
            return False
        
        # Adicionar/atualizar recrutador
        if recrutador_id not in self.recrutadores:
            self.recrutadores[recrutador_id] = {
                "nome": recrutador_nome,
                "total": 0
            }
        
        # Adicionar recruta
        self.recrutas[recruta_id] = {
            "nome": recruta_nome,
            "recrutador_id": recrutador_id,
            "pago": False,
            "data": datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Incrementar total do recrutador
        self.recrutadores[recrutador_id]["total"] += 1
        self.recrutadores[recrutador_id]["nome"] = recrutador_nome  # Atualiza nome
        
        self.salvar_dados()
        print(f"✅ Recruta {recruta_nome} adicionado a {recrutador_nome}")
        return True
    
    def marcar_como_pago(self, recruta_id):
        """Marca um recruta como pago"""
        recruta_id = str(recruta_id)
        if recruta_id in self.recrutas:
            self.recrutas[recruta_id]["pago"] = True
            self.salvar_dados()
            return True
        return False
    
    def get_recrutas_por_recrutador(self, recrutador_id):
        """Retorna lista de recrutas de um recrutador específico"""
        recrutador_id = str(recrutador_id)
        recrutas_lista = []
        
        for r_id, dados in self.recrutas.items():
            if dados["recrutador_id"] == recrutador_id:
                recrutas_lista.append({
                    "id": r_id,
                    "nome": dados["nome"],
                    "pago": dados["pago"],
                    "data": dados["data"]
                })
        
        # Ordenar por data (mais recente primeiro)
        recrutas_lista.sort(key=lambda x: x["data"], reverse=True)
        return recrutas_lista
    
    def get_top_recrutadores(self, limite=10):
        """Retorna os top recrutadores"""
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
        return len(self.recrutas)
    
    def get_total_recrutadores(self):
        """Retorna número de recrutadores ativos"""
        return len(self.recrutadores)

# ========== VIEW DO PAINEL DE RECRUTAS ==========
class RecrutasPagosView(ui.View):
    """View para mostrar e gerenciar recrutas de um recrutador"""
    
    def __init__(self, gerenciador, recrutador_id, recrutador_nome, recrutador_member=None):
        super().__init__(timeout=120)  # 2 minutos de timeout
        self.gerenciador = gerenciador
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
        self.recrutador_member = recrutador_member
        self.pagina = 0
        self.recrutas_por_pagina = 5
    
    def criar_embed(self):
        """Cria o embed com a lista de recrutas"""
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        
        if not recrutas:
            # Título com menção se possível
            if self.recrutador_member:
                titulo = f"📋 Recrutas de {self.recrutador_member.mention}"
            else:
                titulo = f"📋 Recrutas de {self.recrutador_nome}"
            
            embed = discord.Embed(
                title=titulo,
                description="Este recrutador ainda não tem recrutas.",
                color=discord.Color.blue()
            )
            return embed
        
        # Calcular página
        inicio = self.pagina * self.recrutas_por_pagina
        fim = inicio + self.recrutas_por_pagina
        recrutas_pagina = recrutas[inicio:fim]
        
        # Contar pagos
        total_pagos = sum(1 for r in recrutas if r["pago"])
        total_recrutas = len(recrutas)
        
        # Título com menção se possível
        if self.recrutador_member:
            titulo = f"📋 Recrutas de {self.recrutador_member.mention}"
        else:
            titulo = f"📋 Recrutas de {self.recrutador_nome}"
        
        embed = discord.Embed(
            title=titulo,
            description=f"Total: **{total_recrutas}** recrutas | Pagos: **{total_pagos}**",
            color=discord.Color.blue()
        )
        
        for recruta in recrutas_pagina:
            status = "✅ PAGO" if recruta["pago"] else "⏳ PAGAR"
            
            # Tentar buscar o membro para mencionar (se for no mesmo servidor)
            recruta_mention = recruta["nome"]
            if self.recrutador_member and self.recrutador_member.guild:
                membro = self.recrutador_member.guild.get_member(int(recruta["id"]))
                if membro:
                    recruta_mention = membro.mention
            
            embed.add_field(
                name=recruta_mention,
                value=f"Status: {status}\nData: {recruta['data']}",
                inline=False
            )
        
        # Informação de página
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        embed.set_footer(text=f"Página {self.pagina + 1} de {total_paginas}")
        
        return embed
    
    @ui.button(label="◀ Anterior", style=ButtonStyle.secondary, custom_id="recrutas_anterior")
    async def anterior(self, interaction: discord.Interaction, button: ui.Button):
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        
        if self.pagina > 0:
            self.pagina -= 1
            await interaction.response.edit_message(embed=self.criar_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Você já está na primeira página!", ephemeral=True)
    
    @ui.button(label="Próxima ▶", style=ButtonStyle.secondary, custom_id="recrutas_proxima")
    async def proxima(self, interaction: discord.Interaction, button: ui.Button):
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        
        if self.pagina < total_paginas - 1:
            self.pagina += 1
            await interaction.response.edit_message(embed=self.criar_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Você já está na última página!", ephemeral=True)
    
    @ui.button(label="✅ Marcar como Pago", style=ButtonStyle.success, custom_id="recrutas_marcar_pago")
    async def marcar_pago(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar cargo
        if not any(role.id == CARGO_PERMITIDO_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão para marcar recrutas como pagos!", ephemeral=True)
            return
        
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        recrutas_pagina = recrutas[self.pagina * self.recrutas_por_pagina:(self.pagina + 1) * self.recrutas_por_pagina]
        
        # Criar select menu para escolher recruta
        select = RecrutaSelect(self.gerenciador, recrutas_pagina, self, interaction.guild)
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message(
            "**Selecione o recruta para marcar como PAGO:**",
            view=view,
            ephemeral=True
        )

class RecrutaSelect(ui.Select):
    """Select menu para escolher recruta"""
    
    def __init__(self, gerenciador, recrutas, view_principal, guild):
        self.gerenciador = gerenciador
        self.view_principal = view_principal
        self.guild = guild
        
        options = []
        for recruta in recrutas:
            if not recruta["pago"]:  # Só mostrar não pagos
                # Tentar usar menção no label
                label = recruta["nome"][:100]
                membro = guild.get_member(int(recruta["id"]))
                if membro:
                    label = membro.display_name[:100]
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=recruta["id"],
                        description=f"Recrutado em {recruta['data']}"
                    )
                )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="Nenhum recruta para marcar",
                    value="none",
                    description="Todos já estão pagos!"
                )
            )
        
        super().__init__(
            placeholder="Escolha um recruta...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Não há recrutas para marcar como pagos!", ephemeral=True)
            return
        
        # Marcar como pago
        recruta_id = self.values[0]
        self.gerenciador.marcar_como_pago(recruta_id)
        
        # Atualizar view principal
        await self.view_principal.atualizar_view(interaction)
        
        await interaction.response.send_message("✅ Recruta marcado como PAGO com sucesso!", ephemeral=True)
    
    async def atualizar_view(self, interaction):
        """Atualiza a view principal"""
        await interaction.edit_original_response(
            embed=self.view_principal.criar_embed(),
            view=self.view_principal
        )

# ========== VIEW DO PAINEL PRINCIPAL ==========
class PainelRecView(ui.View):
    """View com botões para o painel principal"""
    
    def __init__(self, gerenciador):
        super().__init__(timeout=None)
        self.gerenciador = gerenciador
    
    @ui.button(label="💰 RCs Pagos", style=ButtonStyle.success, custom_id="painel_rec_pagos", row=0)
    async def rcs_pagos(self, interaction: discord.Interaction, button: ui.Button):
        """Abre o painel de gerenciamento de RCs pagos"""
        
        # Verificar se tem o cargo permitido
        if not any(role.id == CARGO_PERMITIDO_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ Você não tem permissão para acessar este painel!", ephemeral=True)
            return
        
        # Criar select com todos os recrutadores
        top_recrutadores = self.gerenciador.get_top_recrutadores(25)  # Mostrar até 25
        
        if not top_recrutadores:
            await interaction.response.send_message("❌ Nenhum recrutador encontrado!", ephemeral=True)
            return
        
        options = []
        for rec in top_recrutadores:
            # Tentar buscar o membro para ter a menção no label
            label = f"{rec['nome']} - {rec['total']} recrutas"
            membro = interaction.guild.get_member(int(rec['id']))
            if membro:
                label = f"{membro.display_name} - {rec['total']} recrutas"
            
            options.append(
                discord.SelectOption(
                    label=label,
                    value=rec['id'],
                    description=f"Total: {rec['total']} recrutas"
                )
            )
        
        select = RecrutadorSelect(self.gerenciador, options, interaction.guild)
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message(
            "**Selecione um recrutador para ver seus recrutas:**",
            view=view,
            ephemeral=True
        )

class RecrutadorSelect(ui.Select):
    """Select menu para escolher recrutador"""
    
    def __init__(self, gerenciador, options, guild):
        self.gerenciador = gerenciador
        self.guild = guild
        super().__init__(
            placeholder="Escolha um recrutador...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        recrutador_id = self.values[0]
        
        # Buscar o membro pelo ID para ter a menção
        recrutador_member = self.guild.get_member(int(recrutador_id))
        
        # Buscar nome do recrutador
        recrutador_nome = "Desconhecido"
        if recrutador_id in self.gerenciador.recrutadores:
            recrutador_nome = self.gerenciador.recrutadores[recrutador_id]["nome"]
        
        # Criar view de recrutas (passando o member para ter a menção)
        view_recrutas = RecrutasPagosView(self.gerenciador, recrutador_id, recrutador_nome, recrutador_member)
        embed = view_recrutas.criar_embed()
        
        await interaction.response.edit_message(
            embed=embed,
            view=view_recrutas
        )

# ========== COG PRINCIPAL ==========
class PainelRecCog(commands.Cog, name="PainelRec"):
    """Sistema de Painel de Recrutadores"""
    
    def __init__(self, bot):
        self.bot = bot
        self.gerenciador = GerenciadorRecrutadores()
        self.paineis_ativos = {}  # {guild_id: {"canal_id": canal_id, "mensagem_id": mensagem_id}}
        print("✅ Módulo PainelRec carregado!")
    
    def criar_embed_painel(self, guild):
        """Cria o embed do painel principal"""
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
                # Tentar buscar o membro para menção
                display_nome = rec['nome']
                membro = guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                
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
                    value=f"{display_nome}\n{cor} `{rec['total']}` recruta(s)",
                    inline=False
                )
            
            # Demais posições (4º em diante)
            if len(top) > 3:
                outros = ""
                for i, rec in enumerate(top[3:], 4):
                    display_nome = rec['nome']
                    membro = guild.get_member(int(rec['id']))
                    if membro:
                        display_nome = membro.mention
                    outros += f"`{i}º` {display_nome} — `{rec['total']}` recruta(s)\n"
                
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
                            self.bot.add_view(PainelRecView(self.gerenciador), message_id=mensagem.id)
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
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome, recruta_id, recruta_nome):
        """Método público para outros módulos adicionarem recrutamentos"""
        resultado = self.gerenciador.adicionar_recrutamento(recrutador_id, recrutador_nome, recruta_id, recruta_nome)
        
        if resultado:
            # Atualizar todos os painéis ativos
            asyncio.create_task(self.atualizar_todos_paineis())
        
        return resultado
    
    async def atualizar_todos_paineis(self):
        """Atualiza todos os painéis ativos"""
        print("🔄 Atualizando todos os painéis...")
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
                    print(f"  ✅ Painel atualizado em #{canal.name}")
                except Exception as e:
                    print(f"  ❌ Erro ao atualizar painel: {e}")
                    # Mensagem não existe mais, remover
                    del self.paineis_ativos[guild_id]
                    self.salvar_paineis()
            except Exception as e:
                print(f"  ❌ Erro geral: {e}")
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
        view = PainelRecView(self.gerenciador)
        
        mensagem = await ctx.send(embed=embed, view=view)
        
        # Salvar painel
        self.paineis_ativos[str(ctx.guild.id)] = {
            "canal_id": ctx.channel.id,
            "mensagem_id": mensagem.id
        }
        self.salvar_paineis()
        
        # Registrar view para persistência
        self.bot.add_view(PainelRecView(self.gerenciador), message_id=mensagem.id)
        
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
                display_nome = rec['nome']
                membro = ctx.guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                top_text += f"`{i}º` {display_nome} — `{rec['total']}` recruta(s)\n"
            
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
        self.cog.gerenciador.recrutas = {}
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
