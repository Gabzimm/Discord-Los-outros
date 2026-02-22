import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime

# ========== CONFIGURAÇÃO ==========
# Cargos que podem usar o comando (staff)
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

# ========== PRESETS DE MENSAGENS ==========
PRESETS = {
    "rec": {
        "titulo": "🏆 **PRÊMIO DE RECRUTAMENTO** 🏆",
        "descricao": "VOCÊ GANHOU O PRÊMIO DE RECRUTAMENTO DESTE MÊS!",
        "cor": 0xFFD700,  # Dourado
        "emoji": "🤝",
        "imagem": "https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png"
    },
    "farm": {
        "titulo": "🌾 **PRÊMIO DE FARM** 🌾",
        "descricao": "VOCÊ GANHOU O PRÊMIO DE FARM DESTE MÊS!",
        "cor": 0x32CD32,  # Verde lima
        "emoji": "🚜",
        "imagem": "https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png"
    },
    "pista": {
        "titulo": "🏁 **PRÊMIO DE PISTA** 🏁",
        "descricao": "VOCÊ GANHOU O PRÊMIO DE PISTA DESTE MÊS!",
        "cor": 0x1E90FF,  # Azul
        "emoji": "🏎️",
        "imagem": "https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png"
    }
}

# ========== FUNÇÕES AUXILIARES ==========
def usuario_pode_usar_premio(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar o comando !premio"""
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

# ========== CLASSES ==========
class PremioConfirmView(ui.View):
    """View de confirmação antes de enviar o prêmio"""
    def __init__(self, target_member, premio_tipo, staff_member):
        super().__init__(timeout=60)
        self.target_member = target_member
        self.premio_tipo = premio_tipo
        self.staff_member = staff_member
        self.preset = PRESETS[premio_tipo]
    
    @ui.button(label="✅ Confirmar Envio", style=ButtonStyle.green, custom_id="confirmar_premio")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar se quem confirmou é o mesmo que usou o comando
        if interaction.user.id != self.staff_member.id:
            await interaction.response.send_message("❌ Apenas quem usou o comando pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Criar embed do prêmio
            embed = discord.Embed(
                title=self.preset["titulo"],
                description=(
                    f"{self.preset['emoji']} {self.preset['descricao']} {self.preset['emoji']}\n\n"
                    f"**Parabéns {self.target_member.mention}!**\n"
                    f"Continue assim e conquiste ainda mais! 🎉"
                ),
                color=self.preset["cor"]
            )
            
            embed.add_field(
                name="📊 Detalhes",
                value=(
                    f"**Tipo:** {self.premio_tipo.upper()}\n"
                    f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n"
                    f"**Entregue por:** {self.staff_member.mention}"
                ),
                inline=False
            )
            
            embed.set_image(url=self.preset["imagem"])
            embed.set_footer(text="Parabéns! Continue assim!")
            
            # Enviar no canal onde o comando foi usado
            await interaction.channel.send(
                content=f"🎉 {self.target_member.mention}",
                embed=embed
            )
            
            # Tentar enviar DM também
            try:
                dm_embed = discord.Embed(
                    title=self.preset["titulo"],
                    description=(
                        f"{self.preset['emoji']} {self.preset['descricao']} {self.preset['emoji']}\n\n"
                        f"Parabéns! Você ganhou o prêmio de **{self.premio_tipo}** deste mês!"
                    ),
                    color=self.preset["cor"]
                )
                await self.target_member.send(embed=dm_embed)
            except:
                pass
            
            # Mensagem de confirmação
            confirm_msg = await interaction.followup.send("✅ Prêmio enviado com sucesso!", ephemeral=True)
            await asyncio.sleep(3)
            await confirm_msg.delete()
            
            # Desabilitar botões
            self.clear_items()
            await interaction.message.edit(view=self)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao enviar prêmio: {e}", ephemeral=True)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.red, custom_id="cancelar_premio")
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.staff_member.id:
            await interaction.response.send_message("❌ Apenas quem usou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        self.clear_items()
        await interaction.message.edit(content="❌ Envio de prêmio cancelado.", view=self)
        await interaction.followup.send("✅ Cancelado!", ephemeral=True)

class PremioSelectView(ui.View):
    """View para selecionar o tipo de prêmio"""
    def __init__(self, target_member, staff_member):
        super().__init__(timeout=60)
        self.target_member = target_member
        self.staff_member = staff_member
        self.add_item(PremioSelect(target_member, staff_member))

class PremioSelect(ui.Select):
    def __init__(self, target_member, staff_member):
        self.target_member = target_member
        self.staff_member = staff_member
        
        options = [
            discord.SelectOption(
                label="Recrutamento",
                description="Prêmio de recrutamento do mês",
                emoji="🤝",
                value="rec"
            ),
            discord.SelectOption(
                label="Farm",
                description="Prêmio de farm do mês",
                emoji="🚜",
                value="farm"
            ),
            discord.SelectOption(
                label="Pista",
                description="Prêmio de pista do mês",
                emoji="🏎️",
                value="pista"
            )
        ]
        
        super().__init__(
            placeholder="🎯 Selecione o tipo de prêmio...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.staff_member.id:
            await interaction.response.send_message("❌ Apenas quem usou o comando pode selecionar!", ephemeral=True)
            return
        
        premio_tipo = self.values[0]
        preset = PRESETS[premio_tipo]
        
        # Embed de confirmação
        embed = discord.Embed(
            title="📋 Confirmar Envio de Prêmio",
            description=(
                f"**Destinatário:** {self.target_member.mention}\n"
                f"**Tipo:** {premio_tipo.upper()}\n"
                f"**Mensagem:**\n{preset['descricao']}\n\n"
                "Clique em **Confirmar** para enviar ou **Cancelar** para voltar."
            ),
            color=preset["cor"]
        )
        
        view = PremioConfirmView(self.target_member, premio_tipo, self.staff_member)
        
        await interaction.response.edit_message(embed=embed, view=view)

# ========== COG PRINCIPAL ==========
class PremiosCog(commands.Cog, name="Prêmios"):
    """Sistema de prêmios com presets"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo de Prêmios carregado!")
    
    @commands.command(name="premio")
    async def premio(self, ctx, member: discord.Member = None, tipo: str = None):
        """
        Envia um prêmio para um membro
        Uso: !premio @usuario [rec/farm/pista]
        Exemplos:
        !premio @João rec
        !premio @Maria farm
        !premio @Pedro pista
        """
        
        # Verificar permissão
        if not usuario_pode_usar_premio(ctx.author):
            await ctx.send("❌ Você não tem permissão para usar este comando!", delete_after=5)
            return
        
        # Verificar se mencionou alguém
        if not member:
            embed_erro = discord.Embed(
                title="❌ Membro não especificado",
                description="Use: `!premio @usuario [rec/farm/pista]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_erro, delete_after=5)
            return
        
        # Se não especificou o tipo, mostrar menu de seleção
        if not tipo or tipo.lower() not in PRESETS:
            embed = discord.Embed(
                title="🎯 Escolha o Tipo de Prêmio",
                description=f"Selecione abaixo o tipo de prêmio para {member.mention}",
                color=discord.Color.blue()
            )
            
            view = PremioSelectView(member, ctx.author)
            await ctx.send(embed=embed, view=view)
            return
        
        # Se especificou o tipo, ir direto para confirmação
        tipo = tipo.lower()
        if tipo not in PRESETS:
            await ctx.send(f"❌ Tipo inválido! Use: rec, farm ou pista", delete_after=5)
            return
        
        preset = PRESETS[tipo]
        
        embed = discord.Embed(
            title="📋 Confirmar Envio de Prêmio",
            description=(
                f"**Destinatário:** {member.mention}\n"
                f"**Tipo:** {tipo.upper()}\n"
                f"**Mensagem:**\n{preset['descricao']}\n\n"
                "Clique em **Confirmar** para enviar ou **Cancelar** para voltar."
            ),
            color=preset["cor"]
        )
        
        view = PremioConfirmView(member, tipo, ctx.author)
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="premios", aliases=["listpremios"])
    async def listar_premios(self, ctx):
        """Lista todos os tipos de prêmios disponíveis"""
        
        embed = discord.Embed(
            title="🏆 Tipos de Prêmios Disponíveis",
            description="Use `!premio @usuario [tipo]` para enviar",
            color=discord.Color.gold()
        )
        
        for tipo, preset in PRESETS.items():
            embed.add_field(
                name=f"{preset['emoji']} {tipo.upper()}",
                value=preset['descricao'],
                inline=False
            )
        
        embed.set_footer(text="Apenas staff pode usar o comando !premio")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="addpremio")
    @commands.has_permissions(administrator=True)
    async def adicionar_premio(self, ctx):
        """[ADMIN] Adiciona um novo tipo de prêmio (em desenvolvimento)"""
        await ctx.send("⚙️ Sistema de adição de prêmios em desenvolvimento!")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(PremiosCog(bot))
    print("✅ Sistema de Prêmios configurado!")
