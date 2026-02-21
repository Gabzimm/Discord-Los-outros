from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import aiohttp
from aiohttp import web

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
                return web.Response(text="🤖 Bot Discord Online")
            
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

bot = commands.Bot(command_prefix='!', intents=intents)
keep_alive = KeepAliveServer()

# ==================== DICIONÁRIO GLOBAL DE CANAIS ====================
# Isso será compartilhado entre todos os módulos
canais_aprovacao = {}  # {guild_id: channel_id}

# ==================== CARREGAR MÓDULOS ====================
async def load_cogs():
    print("=" * 50)
    print("🔄 CARREGANDO MÓDULOS...")
    
    # Lista de módulos para carregar
    cogs = [
        'config_cargos.py',
        'modules.tickets',
        'modules.sets',
        'modules.cargos',  
    ]
    
    carregados = 0
    for cog in cogs:
        print(f"\n🔍 Tentando: {cog}")
        try:
            await bot.load_extension(cog)
            print(f"✅ '{cog}' carregado!")
            carregados += 1
        except Exception as e:
            print(f"❌ Erro: {type(e).__name__}: {e}")
    
    print(f"\n📊 {carregados}/{len(cogs)} módulos carregados")
    print("=" * 50)

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
            name=f"{len(bot.guilds)} servidor(es) | !help"
        )
    )
    
    # NÃO registre views aqui! Cada cog registra as suas próprias
    print("✅ Sistema de persistência ativo!")

# ==================== COMANDOS ====================
@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latência: **{latency}ms**")

@bot.command()
async def status(ctx):
    embed = discord.Embed(title="🤖 Status do Bot", color=discord.Color.green())
    embed.add_field(name="🏷️ Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    # Mostrar módulos carregados
    cogs = list(bot.cogs.keys())
    embed.add_field(name="📦 Módulos", value="\n".join(cogs) if cogs else "Nenhum", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def reload(ctx):
    await load_cogs()
    await ctx.send("✅ Módulos recarregados!")

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
    
    for cog_name, cog in bot.cogs.items():
        comandos = [cmd for cmd in cog.get_commands() if not cmd.hidden]
        if comandos:
            valor = " ".join([f"`!{cmd.name}`" for cmd in sorted(comandos, key=lambda x: x.name)])
            embed.add_field(name=f"**{cog_name}**", value=valor, inline=False)
    
    await ctx.send(embed=embed)

# ==================== TRATAMENTO DE ERROS ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Comando não encontrado. Use `!help`", delete_after=5)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sem permissão!", delete_after=5)
    else:
        print(f"Erro: {error}")

# ==================== INICIALIZAÇÃO ====================
async def main():
    print("🚀 Iniciando bot Discord...")
    print("=" * 50)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    try:
        await keep_alive.start_simple()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    await load_cogs()
    
    try:
        await bot.start(TOKEN)
    finally:
        await keep_alive.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
