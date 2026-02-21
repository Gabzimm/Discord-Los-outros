import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime, timedelta
import re

# ========== CONFIGURAÇÃO ==========
# IDs dos cargos que podem usar comandos de limpeza
CARGOS_PERMITIDOS = [
    1474880677827579935,  # 👑 Lider 00
    1474880748803723294,  # 💎 Lider 01
    1474880750909128874,  # 👮 Lider 02
    1474880752566014156,  # 🎖️ Lider 03
    1474880754214371539,  # 🎖️ Gerente Geral
    1474880755078533241,  # 🎖️ Gerente De Farm
    1474880756026179825,  # 🎖️ Gerente De Pista
    1474880756433162353,  # 🎖️ Gerente de Recrutamento
    1474880757385134130,  # 🎖️ Supervisor
    1474880757984923708,  # 🎖️ Recrutador
    1474881051569688656,  # 🎖️ Ceo Elite
    1474881053108731945,  # 🎖️ Sub Elite
]

# ========== FUNÇÕES AUXILIARES ==========
def usuario_pode_limpar(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar comandos de limpeza"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo permitido
    for role in member.roles:
        if role.id in CARGOS_PERMITIDOS:
            return True
    
    return False

def formatar_tempo(segundos: int) -> str:
    """Formata segundos em texto legível"""
    if segundos < 60:
        return f"{segundos} segundos"
    elif segundos < 3600:
        minutos = segundos // 60
        return f"{minutos} minuto(s)"
    else:
        horas = segundos // 3600
        return f"{horas} hora(s)"

# ========== VIEW DE CONFIRMAÇÃO ==========
class ConfirmarLimpezaView(ui.View):
    """View para confirmar limpeza"""
    
    def __init__(self, cog, ctx, quantidade: int, canal: discord.TextChannel = None):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
        self.quantidade = quantidade
        self.canal = canal or ctx.channel
    
    @ui.button(label="✅ Confirmar", style=ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Deletar mensagens
        await self.cog.realizar_limpeza(self.ctx, self.quantidade, self.canal)
        
        # Apagar mensagem de confirmação
        await interaction.message.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Limpeza cancelada.", delete_after=5)

class LimpezaAvancadaView(ui.View):
    """View para limpeza avançada"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="🧹 Limpar por Quantidade", style=ButtonStyle.primary, emoji="🔢", row=0)
    async def limpar_quantidade(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        modal = LimpezaQuantidadeModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⏰ Limpar por Tempo", style=ButtonStyle.primary, emoji="🕐", row=0)
    async def limpar_tempo(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        modal = LimpezaTempoModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="👤 Limpar de Usuário", style=ButtonStyle.primary, emoji="👤", row=1)
    async def limpar_usuario(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        modal = LimpezaUsuarioModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🔍 Limpar por Palavra", style=ButtonStyle.primary, emoji="🔍", row=1)
    async def limpar_palavra(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        modal = LimpezaPalavraModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="📌 Fixar/Desfixar", style=ButtonStyle.secondary, emoji="📌", row=2)
    async def fixar_mensagem(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await self.cog.gerenciar_fixados(interaction)

# ========== MODAIS ==========
class LimpezaQuantidadeModal(ui.Modal, title="🧹 Limpar por Quantidade"):
    """Modal para limpar por quantidade"""
    
    quantidade = ui.TextInput(
        label="Quantidade de mensagens:",
        placeholder="Ex: 50 (máximo 100)",
        required=True,
        max_length=3
    )
    
    canal_id = ui.TextInput(
        label="ID do canal (opcional):",
        placeholder="Deixe vazio para o canal atual",
        required=False,
        max_length=20
    )
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validar quantidade
        if not self.quantidade.value.isdigit():
            await interaction.followup.send("❌ Quantidade deve ser um número!", ephemeral=True)
            return
        
        qtd = int(self.quantidade.value)
        if qtd < 1 or qtd > 100:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 100!", ephemeral=True)
            return
        
        # Validar canal
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        # Mostrar confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Limpeza",
            description=(
                f"**Canal:** {canal.mention}\n"
                f"**Quantidade:** {qtd} mensagens\n\n"
                "Tem certeza que deseja continuar?"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmarLimpezaView(self.cog, self.ctx, qtd, canal)
        await interaction.followup.send(embed=embed, view=view)

class LimpezaTempoModal(ui.Modal, title="⏰ Limpar por Tempo"):
    """Modal para limpar por tempo"""
    
    horas = ui.TextInput(
        label="Horas:",
        placeholder="Ex: 24",
        required=False,
        max_length=2
    )
    
    minutos = ui.TextInput(
        label="Minutos:",
        placeholder="Ex: 30",
        required=False,
        max_length=2
    )
    
    canal_id = ui.TextInput(
        label="ID do canal (opcional):",
        placeholder="Deixe vazio para o canal atual",
        required=False,
        max_length=20
    )
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Calcular tempo total em minutos
        total_minutos = 0
        
        if self.horas.value and self.horas.value.strip():
            if not self.horas.value.isdigit():
                await interaction.followup.send("❌ Horas deve ser um número!", ephemeral=True)
                return
            total_minutos += int(self.horas.value) * 60
        
        if self.minutos.value and self.minutos.value.strip():
            if not self.minutos.value.isdigit():
                await interaction.followup.send("❌ Minutos deve ser um número!", ephemeral=True)
                return
            total_minutos += int(self.minutos.value)
        
        if total_minutos == 0:
            await interaction.followup.send("❌ Especifique pelo menos horas ou minutos!", ephemeral=True)
            return
        
        if total_minutos > 1440:  # Máximo 24 horas
            await interaction.followup.send("❌ Tempo máximo é 24 horas!", ephemeral=True)
            return
        
        # Validar canal
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        # Mostrar confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Limpeza",
            description=(
                f"**Canal:** {canal.mention}\n"
                f"**Tempo:** {total_minutos} minutos\n\n"
                "Tem certeza que deseja continuar?"
            ),
            color=discord.Color.orange()
        )
        
        # Calcular quantidade aproximada (não usaremos para confirmação, apenas para execução)
        view = ConfirmarLimpezaView(self.cog, self.ctx, total_minutos, canal)
        await interaction.followup.send(embed=embed, view=view)

class LimpezaUsuarioModal(ui.Modal, title="👤 Limpar por Usuário"):
    """Modal para limpar mensagens de um usuário específico"""
    
    usuario = ui.TextInput(
        label="ID do usuário ou @menção:",
        placeholder="Ex: @João ou 123456789",
        required=True
    )
    
    quantidade = ui.TextInput(
        label="Quantidade (máx 100):",
        placeholder="Ex: 50",
        required=True,
        max_length=3
    )
    
    canal_id = ui.TextInput(
        label="ID do canal (opcional):",
        placeholder="Deixe vazio para o canal atual",
        required=False,
        max_length=20
    )
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validar quantidade
        if not self.quantidade.value.isdigit():
            await interaction.followup.send("❌ Quantidade deve ser um número!", ephemeral=True)
            return
        
        qtd = int(self.quantidade.value)
        if qtd < 1 or qtd > 100:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 100!", ephemeral=True)
            return
        
        # Encontrar usuário
        member = None
        input_text = self.usuario.value
        
        if "<@" in input_text:
            user_id = input_text.replace("<@", "").replace(">", "").replace("!", "")
            member = interaction.guild.get_member(int(user_id))
        elif input_text.isdigit():
            member = interaction.guild.get_member(int(input_text))
        else:
            # Buscar por nome
            for m in interaction.guild.members:
                if input_text.lower() in m.name.lower() or (m.nick and input_text.lower() in m.nick.lower()):
                    member = m
                    break
        
        if not member:
            await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
            return
        
        # Validar canal
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        # Executar limpeza
        await self.cog.realizar_limpeza_usuario(interaction, canal, member, qtd)

class LimpezaPalavraModal(ui.Modal, title="🔍 Limpar por Palavra"):
    """Modal para limpar mensagens que contenham palavra específica"""
    
    palavra = ui.TextInput(
        label="Palavra ou frase:",
        placeholder="Ex: !anuncio",
        required=True
    )
    
    quantidade = ui.TextInput(
        label="Quantidade (máx 100):",
        placeholder="Ex: 50",
        required=True,
        max_length=3
    )
    
    canal_id = ui.TextInput(
        label="ID do canal (opcional):",
        placeholder="Deixe vazio para o canal atual",
        required=False,
        max_length=20
    )
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validar quantidade
        if not self.quantidade.value.isdigit():
            await interaction.followup.send("❌ Quantidade deve ser um número!", ephemeral=True)
            return
        
        qtd = int(self.quantidade.value)
        if qtd < 1 or qtd > 100:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 100!", ephemeral=True)
            return
        
        # Validar canal
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        # Executar limpeza
        await self.cog.realizar_limpeza_palavra(interaction, canal, self.palavra.value, qtd)

# ========== COG PRINCIPAL ==========
class LimpezaCog(commands.Cog):
    """Sistema de Limpeza de Canais"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Limpeza carregado!")
    
    async def realizar_limpeza(self, ctx, quantidade: int, canal: discord.TextChannel):
        """Realiza a limpeza de mensagens"""
        try:
            # Deletar mensagens
            deleted = await canal.purge(limit=quantidade + 1)  # +1 para incluir o comando
            
            # Mensagem de confirmação
            embed = discord.Embed(
                title="🧹 Limpeza Concluída",
                description=(
                    f"**Canal:** {canal.mention}\n"
                    f"**Mensagens apagadas:** {len(deleted) - 1}\n"
                    f"**Responsável:** {ctx.author.mention}\n"
                    f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ),
                color=discord.Color.green()
            )
            
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
            
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para apagar mensagens neste canal!", delete_after=5)
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}", delete_after=5)
    
    async def realizar_limpeza_usuario(self, interaction, canal: discord.TextChannel, member: discord.Member, quantidade: int):
        """Limpa mensagens de um usuário específico"""
        try:
            def check(msg):
                return msg.author == member
            
            deleted = await canal.purge(limit=quantidade, check=check)
            
            embed = discord.Embed(
                title="🧹 Limpeza por Usuário",
                description=(
                    f"**Canal:** {canal.mention}\n"
                    f"**Usuário:** {member.mention}\n"
                    f"**Mensagens apagadas:** {len(deleted)}\n"
                    f"**Responsável:** {interaction.user.mention}"
                ),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    async def realizar_limpeza_palavra(self, interaction, canal: discord.TextChannel, palavra: str, quantidade: int):
        """Limpa mensagens que contenham uma palavra específica"""
        try:
            def check(msg):
                return palavra.lower() in msg.content.lower()
            
            deleted = await canal.purge(limit=quantidade, check=check)
            
            embed = discord.Embed(
                title="🧹 Limpeza por Palavra",
                description=(
                    f"**Canal:** {canal.mention}\n"
                    f"**Palavra:** `{palavra}`\n"
                    f"**Mensagens apagadas:** {len(deleted)}\n"
                    f"**Responsável:** {interaction.user.mention}"
                ),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    async def gerenciar_fixados(self, interaction):
        """Gerencia mensagens fixadas no canal"""
        canal = interaction.channel
        
        # Buscar mensagens fixadas
        pins = await canal.pins()
        
        if not pins:
            await interaction.response.send_message("📌 Este canal não tem mensagens fixadas.", ephemeral=True)
            return
        
        # Criar select com as fixadas
        options = []
        for i, msg in enumerate(pins[:10]):  # Máximo 10 opções
            autor = msg.author.display_name
            conteudo = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            options.append(
                discord.SelectOption(
                    label=f"{i+1}. {autor}",
                    description=conteudo,
                    value=str(msg.id)
                )
            )
        
        select = ui.Select(
            placeholder="Selecione uma mensagem para desfixar...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(select_interaction):
            msg_id = int(select.values[0])
            msg = await canal.fetch_message(msg_id)
            await msg.unpin()
            await select_interaction.response.send_message(f"✅ Mensagem desfixada!", ephemeral=True)
        
        select.callback = select_callback
        
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message("📌 **Mensagens Fixadas:**", view=view, ephemeral=True)
    
    @commands.group(name="limpar", aliases=["clean", "clear"], invoke_without_command=True)
    async def limpar(self, ctx):
        """🧹 Comandos de limpeza de canais"""
        
        if not usuario_pode_limpar(ctx.author):
            await ctx.send("❌ Você não tem permissão para usar este comando!", delete_after=5)
            return
        
        embed = discord.Embed(
            title="🧹 Sistema de Limpeza",
            description="Escolha uma opção abaixo:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📌 Comandos Rápidos",
            value=(
                "`!limpar 10` - Apaga 10 mensagens\n"
                "`!limpar 50` - Apaga 50 mensagens\n"
                "`!limpar 100` - Apaga 100 mensagens\n"
                "`!limpar canal #canal 20` - Apaga em outro canal"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Opções Avançadas",
            value=(
                "• **Limpar por tempo** - Mensagens antigas\n"
                "• **Limpar por usuário** - Mensagens de alguém\n"
                "• **Limpar por palavra** - Mensagens com texto\n"
                "• **Gerenciar fixadas** - Desfixar mensagens"
            ),
            inline=False
        )
        
        embed.set_footer(text="Clique nos botões para opções avançadas")
        
        view = LimpezaAvancadaView(self, ctx)
        await ctx.send(embed=embed, view=view)
    
    @limpar.command(name="rapido")
    async def limpar_rapido(self, ctx, quantidade: int, canal: discord.TextChannel = None):
        """Limpeza rápida por quantidade"""
        
        if not usuario_pode_limpar(ctx.author):
            await ctx.send("❌ Você não tem permissão!", delete_after=5)
            return
        
        if quantidade < 1 or quantidade > 100:
            await ctx.send("❌ Quantidade deve ser entre 1 e 100!", delete_after=5)
            return
        
        canal_alvo = canal or ctx.channel
        
        embed = discord.Embed(
            title="⚠️ Confirmar Limpeza",
            description=(
                f"**Canal:** {canal_alvo.mention}\n"
                f"**Quantidade:** {quantidade} mensagens\n\n"
                "Tem certeza que deseja continuar?"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmarLimpezaView(self, ctx, quantidade, canal_alvo)
        await ctx.send(embed=embed, view=view)
    
    @limpar.command(name="canal")
    async def limpar_canal(self, ctx, canal: discord.TextChannel, quantidade: int):
        """Limpa mensagens em um canal específico"""
        await self.limpar_rapido(ctx, quantidade, canal)
    
    @limpar.command(name="tudo")
    @commands.has_permissions(administrator=True)
    async def limpar_tudo(self, ctx, canal: discord.TextChannel = None):
        """⚠️ APAGA TODAS as mensagens do canal (apenas admin)"""
        
        canal_alvo = canal or ctx.channel
        
        embed = discord.Embed(
            title="⚠️ **PERIGO!** ⚠️",
            description=(
                f"Você está prestes a apagar **TODAS** as mensagens de {canal_alvo.mention}!\n\n"
                "**Esta ação não pode ser desfeita!**\n\n"
                "Para confirmar, digite: `!limpar confirmar_tudo`"
            ),
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @limpar.command(name="confirmar_tudo")
    @commands.has_permissions(administrator=True)
    async def confirmar_tudo(self, ctx, canal: discord.TextChannel = None):
        """Confirma a limpeza total do canal"""
        
        canal_alvo = canal or ctx.channel
        
        try:
            # Criar canal novo com mesmo nome e categoria
            novo_canal = await canal_alvo.clone()
            await canal_alvo.delete()
            
            embed = discord.Embed(
                title="🧹 Limpeza Total Concluída",
                description=(
                    f"**Canal antigo deletado:** #{canal_alvo.name}\n"
                    f"**Novo canal criado:** {novo_canal.mention}\n"
                    f"**Responsável:** {ctx.author.mention}"
                ),
                color=discord.Color.green()
            )
            
            await novo_canal.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}", delete_after=5)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(LimpezaCog(bot))
    print("✅ Sistema de Limpeza configurado!")
