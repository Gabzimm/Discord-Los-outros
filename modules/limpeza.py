import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
# Nomes dos cargos que podem usar comandos de limpeza
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

# ========== FUNÇÕES AUXILIARES ==========
def usuario_pode_limpar(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar comandos de limpeza baseado nos cargos"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo de staff
    for role in member.roles:
        if role.name in STAFF_ROLES:
            return True
    
    return False

# ========== VIEW DE CONFIRMAÇÃO (APENAS PARA MENU) ==========
class ConfirmarLimpezaView(ui.View):
    """View para confirmar limpeza (usada apenas pelo menu !limpar)"""
    
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

# ========== MODAL DE LIMPEZA ==========
class LimpezaQuantidadeModal(ui.Modal, title="🧹 Limpar por Quantidade"):
    """Modal para limpar por quantidade"""
    
    quantidade = ui.TextInput(
        label="Quantidade de mensagens:",
        placeholder="Ex: 50 (máximo 999)",
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
        if qtd < 1 or qtd > 999:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 999!", ephemeral=True)
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

# ========== VIEW PRINCIPAL ==========
class LimpezaView(ui.View):
    """View principal com apenas o botão de limpeza por quantidade"""
    
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
    
    @commands.group(name="limpar", aliases=["clean", "clear"], invoke_without_command=True)
    async def limpar(self, ctx):
        """🧹 Comandos de limpeza de canais"""
        
        if not usuario_pode_limpar(ctx.author):
            await ctx.send("❌ Você não tem permissão para usar este comando!", delete_after=5)
            return
        
        embed = discord.Embed(
            title="🧹 Sistema de Limpeza",
            description="Clique no botão abaixo para limpar mensagens:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📌 Comandos Rápidos",
            value=(
                "`!limpar 10` - Apaga 10 mensagens (SEM CONFIRMAÇÃO)\n"
                "`!limpar 50` - Apaga 50 mensagens (SEM CONFIRMAÇÃO)\n"
                "`!limpar 100` - Apaga 100 mensagens (SEM CONFIRMAÇÃO)\n"
                "`!limpar canal #canal 20` - Apaga em outro canal (SEM CONFIRMAÇÃO)"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use !limpar [quantidade] para limpeza direta • Clique no botão para opções avançadas")
        
        view = LimpezaView(self, ctx)
        await ctx.send(embed=embed, view=view)
    
    @limpar.command(name="rapido")
    async def limpar_rapido(self, ctx, quantidade: int, canal: discord.TextChannel = None):
        """Limpeza rápida por quantidade - SEM CONFIRMAÇÃO"""
        
        if not usuario_pode_limpar(ctx.author):
            await ctx.send("❌ Você não tem permissão!", delete_after=5)
            return
        
        if quantidade < 1 or quantidade > 999:
            await ctx.send("❌ Quantidade deve ser entre 1 e 999!", delete_after=5)
            return
        
        canal_alvo = canal or ctx.channel
        
        # LIMPEZA DIRETA - SEM CONFIRMAÇÃO
        await self.realizar_limpeza(ctx, quantidade, canal_alvo)
    
    @limpar.command(name="canal")
    async def limpar_canal(self, ctx, canal: discord.TextChannel, quantidade: int):
        """Limpa mensagens em um canal específico - SEM CONFIRMAÇÃO"""
        await self.limpar_rapido(ctx, quantidade, canal)
    
    # Handler para chamadas diretas como !limpar 10
    @limpar.error
    async def limpar_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            # Se não conseguir converter para int, mostra o menu
            pass

# Handler para comandos diretos (ex: !limpar 10)
@commands.command(name="limpar_direto", aliases=["limpar"])
async def limpar_direto(ctx, quantidade: int, canal: discord.TextChannel = None):
    """Comando direto para limpeza rápida"""
    
    # Verificar permissão
    if not usuario_pode_limpar(ctx.author):
        await ctx.send("❌ Você não tem permissão!", delete_after=5)
        return
    
    # Verificar quantidade
    if quantidade < 1 or quantidade > 999:
        await ctx.send("❌ Quantidade deve ser entre 1 e 999!", delete_after=5)
        return
    
    # Buscar o cog
    cog = ctx.bot.get_cog("LimpezaCog")
    if not cog:
        await ctx.send("❌ Erro no sistema de limpeza!", delete_after=5)
        return
    
    canal_alvo = canal or ctx.channel
    
    # Limpeza direta - SEM CONFIRMAÇÃO
    await cog.realizar_limpeza(ctx, quantidade, canal_alvo)

# ========== SETUP ==========
async def setup(bot):
    # Adicionar o comando direto
    bot.add_command(limpar_direto)
    # Adicionar o cog
    await bot.add_cog(LimpezaCog(bot))
    print("✅ Sistema de Limpeza configurado!")
