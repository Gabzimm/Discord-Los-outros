from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import aiohttp
from aiohttp import web
import socket
import time
import traceback

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

# ==================== CONTROLE DE REINICIALIZAÇÃO ====================
ULTIMA_REINICIALIZACAO = time.time()
MIN_INTERVALO_REINICIALIZACAO = 60

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

# Dicionário global de canais
canais_aprovacao = {}

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print(f'✅ Bot logado como: {bot.user}')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📡 Ping: {round(bot.latency * 1000)}ms')
    print(f'🏠 Servidores: {len(bot.guilds)}')
    
    # Listar todos os comandos carregados
    print("\n📋 COMANDOS CARREGADOS:")
    for cmd in bot.commands:
        print(f"   • !{cmd.name} (cog: {cmd.cog_name or 'Sem cog'})")
    print("=" * 50)
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Jugadores | !help"
        )
    )
    
    print("✅ Bot pronto!")

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
    
    # Agrupar comandos por cog
    cogs = {}
    for cmd in bot.commands:
        cog_name = cmd.cog_name or "Sem Categoria"
        if cog_name not in cogs:
            cogs[cog_name] = []
        cogs[cog_name].append(cmd)
    
    embed = discord.Embed(
        title="🤖 Comandos do Bot",
        description="Lista de todos os comandos:",
        color=discord.Color.purple()
    )
    
    for cog_name, commands_list in cogs.items():
        cmd_list = [f"`!{cmd.name}`" for cmd in sorted(commands_list, key=lambda x: x.name)]
        embed.add_field(
            name=f"📌 **{cog_name}**",
            value=" ".join(cmd_list) or "Nenhum comando",
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
    
    # Mostrar comandos por módulo
    for cog_name in cogs:
        cog = bot.get_cog(cog_name)
        if cog:
            commands_list = [f"!{cmd.name}" for cmd in cog.get_commands()]
            if commands_list:
                embed.add_field(
                    name=f"🔧 Comandos de {cog_name}",
                    value=", ".join(commands_list[:5]) + ("..." if len(commands_list) > 5 else ""),
                    inline=False
                )
    
    await ctx.send(embed=embed)

@bot.command(name="reload")
@commands.has_permissions(administrator=True)
async def reload_cogs(ctx):
    """Recarrega todos os módulos"""
    await ctx.send("🔄 Recarregando módulos...")
    success = await load_cogs()
    if success:
        await ctx.send("✅ Módulos recarregados!")
    else:
        await ctx.send("❌ Erro ao recarregar módulos! Verifique os logs.")

@bot.command(name="debug")
@commands.has_permissions(administrator=True)
async def debug_cogs(ctx):
    """Mostra informações de debug dos módulos"""
    embed = discord.Embed(title="🔍 Debug Info", color=discord.Color.blue())
    
    # Módulos carregados
    cogs = list(bot.cogs.keys())
    embed.add_field(name="📦 Cogs Carregados", value="\n".join(cogs) or "Nenhum", inline=False)
    
    # Comandos totais
    embed.add_field(name="📋 Total de Comandos", value=str(len(bot.commands)), inline=True)
    
    # Comandos por categoria
    commands_by_cog = {}
    for cmd in bot.commands:
        cog_name = cmd.cog_name or "main"
        if cog_name not in commands_by_cog:
            commands_by_cog[cog_name] = []
        commands_by_cog[cog_name].append(cmd.name)
    
    for cog, cmds in commands_by_cog.items():
        embed.add_field(name=f"Comandos em {cog}", value=", ".join(cmds[:10]), inline=False)
    
    await ctx.send(embed=embed)

# ==================== CARREGAR MÓDULOS ====================
async def load_cogs():
    global ULTIMA_REINICIALIZACAO
    
    agora = time.time()
    if agora - ULTIMA_REINICIALIZACAO < MIN_INTERVALO_REINICIALIZACAO:
        print(f"⚠️ Ignorando recarga rápida ({(agora - ULTIMA_REINICIALIZACAO):.1f}s)")
        return True
    
    ULTIMA_REINICIALIZACAO = agora
    
    print("=" * 50)
    print("🔄 CARREGANDO MÓDULOS...")
    print(f"📁 Diretório atual: {os.getcwd()}")
    print(f"📁 Pastas disponíveis: {os.listdir('.')}")
    
    # Verificar se pasta modules existe
    if 'modules' not in os.listdir('.'):
        print("❌ Pasta 'modules' não encontrada!")
        print("   Criando pasta modules...")
        os.makedirs('modules', exist_ok=True)
        
        # Criar __init__.py
        with open('modules/__init__.py', 'w') as f:
            f.write('# Módulos do bot\n')
    
    cogs = [
        'modules.sets',
        'modules.tickets',
        'modules.config_cargos',
    ]
    
    carregados = 0
    for cog in cogs:
        print(f"\n🔍 Tentando: {cog}")
        try:
            # Descarregar se já estiver carregado
            try:
                await bot.unload_extension(cog)
                print(f"⏪ '{cog}' descarregado")
            except Exception as e:
                print(f"   Não estava carregado: {e}")
            
            # Carregar
            await bot.load_extension(cog)
            print(f"✅ '{cog}' carregado com sucesso!")
            carregados += 1
            
        except FileNotFoundError:
            print(f"❌ Arquivo não encontrado: modules/{cog.split('.')[-1]}.py")
            print(f"   Certifique-se que o arquivo existe em: modules/{cog.split('.')[-1]}.py")
        except Exception as e:
            print(f"❌ Erro ao carregar {cog}:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Erro: {str(e)}")
            traceback.print_exc()
    
    print(f"\n📊 RESULTADO: {carregados}/{len(cogs)} módulos carregados")
    print("=" * 50)
    return carregados > 0

# ==================== TRATAMENTO DE ERROS ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Comando não encontrado - enviar sugestão
        cmd = ctx.message.content.split()[0][1:]  # Remove o !
        sugestoes = []
        for command in bot.commands:
            if cmd in command.name or any(cmd in alias for alias in command.aliases):
                sugestoes.append(f"!{command.name}")
        
        if sugestoes:
            await ctx.send(f"❌ Comando `!{cmd}` não encontrado. Você quis dizer: {', '.join(sugestoes)}?")
        else:
            # Silenciosamente ignorar comandos desconhecidos
            pass
            
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando! Use `!help {ctx.command.name}`", delete_after=5)
    else:
        print(f"❌ Erro não tratado: {error}")
        traceback.print_exc()

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
    
    # Carregar módulos
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
        traceback.print_exc()
