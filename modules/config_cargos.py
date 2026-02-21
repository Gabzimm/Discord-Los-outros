# modules/config_cargos.py
import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class CargosManager:
    """Gerenciador central de cargos do servidor"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cargos_cache = {}  # Cache: {guild_id: {cargo_nome: cargo_obj}}
        self.cargos_por_id = {}  # Cache: {guild_id: {cargo_id: cargo_obj}}
        self.hierarquia_cache = {}  # Cache: {guild_id: [cargos_ordenados]}
        self.arquivo_config = "cargos_config.json"
        self.carregar_config()
    
    def carregar_config(self):
        """Carrega configurações salvas"""
        try:
            if os.path.exists(self.arquivo_config):
                with open(self.arquivo_config, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except:
            self.config = {}
    
    def salvar_config(self):
        """Salva configurações"""
        try:
            with open(self.arquivo_config, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass
    
    async def atualizar_cache_guild(self, guild: discord.Guild):
        """Atualiza o cache de cargos de um servidor"""
        # Cache por nome
        self.cargos_cache[guild.id] = {role.name: role for role in guild.roles}
        
        # Cache por ID
        self.cargos_por_id[guild.id] = {role.id: role for role in guild.roles}
        
        # Hierarquia (do maior para o menor)
        self.hierarquia_cache[guild.id] = sorted(
            guild.roles, 
            key=lambda r: r.position, 
            reverse=True
        )
        
        print(f"✅ Cache de cargos atualizado para {guild.name} - {len(guild.roles)} cargos")
    
    async def atualizar_todos_servidores(self):
        """Atualiza cache de todos os servidores"""
        for guild in self.bot.guilds:
            await self.atualizar_cache_guild(guild)
    
    def get_cargo_por_nome(self, guild_id: int, nome: str) -> discord.Role:
        """Busca cargo por nome (case insensitive)"""
        if guild_id in self.cargos_cache:
            # Busca exata
            if nome in self.cargos_cache[guild_id]:
                return self.cargos_cache[guild_id][nome]
            
            # Busca case insensitive
            nome_lower = nome.lower()
            for cargo_nome, cargo in self.cargos_cache[guild_id].items():
                if cargo_nome.lower() == nome_lower:
                    return cargo
        return None
    
    def get_cargo_por_id(self, guild_id: int, cargo_id: int) -> discord.Role:
        """Busca cargo por ID"""
        if guild_id in self.cargos_por_id:
            return self.cargos_por_id[guild_id].get(cargo_id)
        return None
    
    def get_cargos_por_categoria(self, guild_id: int, palavras_chave: list) -> list:
        """Busca cargos que contenham palavras-chave"""
        if guild_id not in self.cargos_cache:
            return []
        
        resultados = []
        for cargo_nome, cargo in self.cargos_cache[guild_id].items():
            for palavra in palavras_chave:
                if palavra.lower() in cargo_nome.lower():
                    resultados.append(cargo)
                    break
        return resultados
    
    def get_cargos_staff(self, guild_id: int) -> list:
        """Retorna cargos de staff (baseado em palavras comuns)"""
        palavras_staff = ['owner', 'adm', 'gerente', 'lider', 'mod', 'staff', 
                         '👑', '🔑', '🛡️', 'responsável', 'resp']
        return self.get_cargos_por_categoria(guild_id, palavras_staff)
    
    def get_hierarquia(self, guild_id: int) -> list:
        """Retorna lista de cargos em ordem hierárquica"""
        return self.hierarquia_cache.get(guild_id, [])
    
    def cargo_e_maior_que(self, guild_id: int, cargo1: discord.Role, cargo2: discord.Role) -> bool:
        """Verifica se cargo1 é maior que cargo2 na hierarquia"""
        hierarquia = self.get_hierarquia(guild_id)
        if not hierarquia:
            return False
        
        try:
            pos1 = hierarquia.index(cargo1)
            pos2 = hierarquia.index(cargo2)
            return pos1 < pos2  # Menor índice = maior posição
        except:
            return False

class CargosManagerCog(commands.Cog):
    """Cog para gerenciar o sistema de cargos centralizado"""
    
    def __init__(self, bot):
        self.bot = bot
        self.manager = CargosManager(bot)
        print("✅ Gerenciador Central de Cargos carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Quando o bot inicia, atualiza cache de todos servidores"""
        await self.manager.atualizar_todos_servidores()
        print("✅ Cache de cargos inicializado!")
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Quando um cargo é CRIADO"""
        await self.manager.atualizar_cache_guild(role.guild)
        print(f"🆕 Novo cargo criado: {role.name} - Cache atualizado!")
        
        # Disparar evento personalizado para outros sistemas
        self.bot.dispatch('cargos_atualizados', role.guild, 'create', role)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Quando um cargo é DELETADO"""
        await self.manager.atualizar_cache_guild(role.guild)
        print(f"🗑️ Cargo deletado: {role.name} - Cache atualizado!")
        
        # Disparar evento personalizado
        self.bot.dispatch('cargos_atualizados', role.guild, 'delete', role)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Quando um cargo é ATUALIZADO (nome, permissões, etc)"""
        if before.name != after.name or before.position != after.position:
            await self.manager.atualizar_cache_guild(after.guild)
            print(f"✏️ Cargo atualizado: {after.name} - Cache atualizado!")
            
            # Disparar evento personalizado
            self.bot.dispatch('cargos_atualizados', after.guild, 'update', after)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Quando o servidor é atualizado (pode afetar hierarquia)"""
        await self.manager.atualizar_cache_guild(after)
        print(f"🔄 Servidor atualizado: {after.name} - Cache recarregado!")
        
        # Disparar evento personalizado
        self.bot.dispatch('cargos_atualizados', after, 'guild_update', None)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def cargos_cache(self, ctx):
        """Mostra estatísticas do cache de cargos"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.manager.cargos_cache:
            await ctx.send("❌ Cache não inicializado!")
            return
        
        cargos = self.manager.cargos_cache[guild_id]
        hierarquia = self.manager.get_hierarquia(guild_id)
        staff = self.manager.get_cargos_staff(guild_id)
        
        embed = discord.Embed(
            title="📊 Cache de Cargos",
            description=f"Servidor: **{ctx.guild.name}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📦 Total de Cargos",
            value=f"`{len(cargos)}` cargos",
            inline=True
        )
        
        embed.add_field(
            name="👑 Cargos Staff",
            value=f"`{len(staff)}` cargos detectados",
            inline=True
        )
        
        # Top 5 cargos
        top5 = hierarquia[:5]
        if top5:
            embed.add_field(
                name="🏆 Top 5 Cargos",
                value="\n".join([f"{i+1}. {r.mention}" for i, r in enumerate(top5)]),
                inline=False
            )
        
        embed.set_footer(text=f"Cache atualizado em tempo real • {len(cargos)} cargos")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def recarregar_cache(self, ctx):
        """Recarrega manualmente o cache de cargos"""
        await self.manager.atualizar_cache_guild(ctx.guild)
        await ctx.send(f"✅ Cache recarregado! {len(self.manager.cargos_cache[ctx.guild.id])} cargos encontrados.")
    
    @commands.command()
    async def buscar_cargo(self, ctx, *, nome: str):
        """Busca um cargo pelo nome"""
        cargo = self.manager.get_cargo_por_nome(ctx.guild.id, nome)
        
        if cargo:
            embed = discord.Embed(
                title="✅ Cargo Encontrado",
                description=(
                    f"**Cargo:** {cargo.mention}\n"
                    f"**ID:** `{cargo.id}`\n"
                    f"**Cor:** {cargo.color}\n"
                    f"**Posição:** {cargo.position}\n"
                    f"**Membros:** {len(cargo.members)}"
                ),
                color=cargo.color
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Cargo '{nome}' não encontrado!")

async def setup(bot):
    await bot.add_cog(CargosManagerCog(bot))
