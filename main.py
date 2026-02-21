from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import aiohttp
from aiohttp import web
import socket

# ==================== VERIFICAÇÃO DE INSTÂNCIA ÚNICA ====================
def verificar_instancia_unica():
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind('\0bot_jugadores_unico')
        return True
    except socket.error:
        print("❌ ERRO: Já existe uma instância do bot rodando!")
        print("   Execute: pkill -f python")
        print("   Depois: python main.py")
        return False

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== KEEP-ALIVE ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
    
    async def start_simple(self):
        try:
            self.app = web.Application()
            
            async def handle(request):
                return web.Response(text="🤖 Bot Discord Online - Jugadores")
            
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat()
                })
            
            self.app.router.add_get('/', handle)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', 8080)
            await self.site.start()
            
            print(f"🌐 Keep-alive iniciado na porta 8080")
            
        except Exception as e:
            print(f"⚠️ Erro no keep-alive: {e}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

# ==================== BOT DISCORD ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
keep_alive = KeepAliveServer()

# Dicionário global de canais (compartilhado entre módulos)
canais_aprovacao = {}

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print(f'✅ Bot logado como: {bot.user}')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📡 Ping: {round(bot.latency * 1000)}ms')
    print(f'🏠 Servidores: {len(bot.guilds)}')
    print('🚀 Bot pronto!')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Jugadores | !help"
        )
    )
    
    print("✅ Sistema de persistência ativo!")

# ==================== HELP PERSONALIZADO ====================
@bot.command(name="help")
async def custom_help(ctx, *, comando: str = None):
    if comando:
        cmd = bot.get_command(comando)
        if not cmd:
            await ctx.send(f"❌ Comando `{comando}` não encontrado!")
            return
        
        embed = discord.Embed(
            title=f"📖 Ajuda: !{cmd.name}",
            description=cmd.help or "Sem descrição",
            color=discord.Color.blue()
        )
        
        if cmd.aliases:
            embed.add_field(name="📌 Aliases", value=", ".join([f"`!{a}`" for a in cmd.aliases]), inline=False)
        
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🤖 Comandos do Bot",
        description="Lista de todos os comandos:",
        color=discord.Color.purple()
    )
    
    # Comandos Gerais
    embed.add_field(
        name="📌 **Gerais**",
        value="`!ping` `!status` `!help`",
        inline=False
    )
    
    # Comandos de Sets
    embed.add_field(
        name="🎮 **Sets**",
        value="`!setup_set` `!aprovamento` `!check_id` `!sets_pendentes`",
        inline=False
    )
    
    # Comandos de Tickets
    embed.add_field(
        name="🎫 **Tickets**",
        value="`!setup_tickets`",
        inline=False
    )
    
    embed.set_footer(text=f"Total de comandos: {len(bot.commands)}")
    
    await ctx.send(embed=embed)

# ==================== COMANDOS GERAIS ====================
@bot.command(name="ping")
async def ping(ctx):
    """Mostra a latência do bot"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latência: **{latency}ms**")

@bot.command(name="status")
async def status(ctx):
    """Mostra o status do bot"""
    embed = discord.Embed(
        title="🤖 Status do Bot",
        color=discord.Color.green()
    )
    
    embed.add_field(name="🏷️ Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    # Mostrar módulos carregados
    cogs = list(bot.cogs.keys())
    if cogs:
        embed.add_field(name="📦 Módulos Ativos", value="\n".join(cogs), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="reload")
@commands.has_permissions(administrator=True)
async def reload_cogs(ctx):
    """Recarrega todos os módulos (apenas admin)"""
    await load_cogs()
    await ctx.send("✅ Módulos recarregados!")

# ==================== CARREGAR MÓDULOS ====================
async def load_cogs():
    print("=" * 50)
    print("🔄 CARREGANDO MÓDULOS...")
    
    cogs = [
        'modules.sets',
        'modules.tickets',
        'modules.config_cargos',
    ]
    
    carregados = 0
    for cog in cogs:
        print(f"\n🔍 Tentando: {cog}")
        try:
            await bot.load_extension(cog)
            print(f"✅ '{cog}' carregado!")
            carregados += 1
        except commands.ExtensionAlreadyLoaded:
            print(f"⚠️ '{cog}' já estava carregado")
            carregados += 1
        except Exception as e:
            print(f"❌ Erro: {type(e).__name__}: {e}")
    
    print(f"\n📊 {carregados}/{len(cogs)} módulos carregados")
    print("=" * 50)
    return carregados > 0

# ==================== TRATAMENTO DE ERROS ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignorar comandos não encontrados (sem resposta)
        pass
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sem permissão!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando! Use `!help {ctx.command.name}`", delete_after=5)
    else:
        print(f"❌ Erro: {error}")

# ==================== INICIALIZAÇÃO ====================
async def main():
    print("🚀 Iniciando bot Discord...")
    print("=" * 50)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        print("Configure no Render: Environment → DISCORD_TOKEN")
        sys.exit(1)
    
    try:
        print("🌐 Iniciando servidor keep-alive...")
        await keep_alive.start_simple()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    await load_cogs()
    
    print("🔗 Conectando ao Discord...")
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado pelo usuário")
    finally:
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
