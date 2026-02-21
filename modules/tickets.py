import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re
from typing import List, Dict
import json
import os

# ========== CONFIGURAÇÃO ==========
# ID do cargo base (deste para cima NÃO PODEM ver o painel)
CARGO_BASE_ID = 1393998691354018094

# ========== FUNÇÕES AUXILIARES ==========
def usuario_e_staff(member: discord.Member) -> bool:
    """Verifica se o usuário TEM cargo >= cargo base (NÃO PODE ver painel)"""
    if not member:
        return False
    
    if member.guild_permissions.administrator:
        return True
    
    cargo_base = member.guild.get_role(CARGO_BASE_ID)
    if not cargo_base:
        print(f"⚠️ Cargo base ID {CARGO_BASE_ID} não encontrado!")
        return False
    
    for role in member.roles:
        if role.position >= cargo_base.position:
            return True
    
    return False

def get_cargos_staff(guild: discord.Guild) -> list:
    """Retorna lista de cargos com posição >= cargo base (staff)"""
    cargo_base = guild.get_role(CARGO_BASE_ID)
    if not cargo_base:
        return []
    
    cargos_staff = []
    for role in guild.roles:
        if role.position >= cargo_base.position:
            cargos_staff.append(role)
    
    return sorted(cargos_staff, key=lambda r: r.position, reverse=True)

class TicketLogger:
    """Gerencia o salvamento e transcrição de tickets"""
    
    def __init__(self):
        self.pasta_transcricoes = "transcricoes_tickets"
        os.makedirs(self.pasta_transcricoes, exist_ok=True)
    
    async def salvar_transcricao(self, channel: discord.TextChannel, fechado_por: discord.Member) -> str:
        """Salva todas as mensagens do ticket em um arquivo HTML"""
        try:
            # Coletar todas as mensagens
            mensagens = []
            async for message in channel.history(limit=None, oldest_first=True):
                mensagens.append({
                    'autor': str(message.author),
                    'autor_id': message.author.id,
                    'autor_avatar': str(message.author.avatar.url) if message.author.avatar else None,
                    'conteudo': message.content,
                    'data': message.created_at.strftime('%d/%m/%Y %H:%M:%S'),
                    'anexos': [att.url for att in message.attachments],
                    'embeds': [embed.to_dict() for embed in message.embeds]
                })
            
            # Criar arquivo HTML
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{self.pasta_transcricoes}/ticket_{channel.name}_{timestamp}.html"
            
            # Informações do ticket
            ticket_info = {
                'canal': channel.name,
                'criado_em': channel.created_at.strftime('%d/%m/%Y %H:%M:%S'),
                'fechado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'fechado_por': str(fechado_por),
                'fechado_por_id': fechado_por.id,
                'topic': channel.topic or "Sem descrição",
                'total_mensagens': len(mensagens)
            }
            
            # Extrair ID do dono do ticket do topic
            dono_id = None
            if channel.topic and "ID:" in channel.topic:
                try:
                    dono_id = int(channel.topic.split("ID:")[1].strip())
                except:
                    pass
            
            ticket_info['dono_id'] = dono_id
            
            # Gerar HTML
            html_content = self._gerar_html(ticket_info, mensagens)
            
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return nome_arquivo
            
        except Exception as e:
            print(f"[ERRO] ao salvar transcrição: {e}")
            return None
    
    def _gerar_html(self, ticket_info: dict, mensagens: List[dict]) -> str:
        """Gera o HTML da transcrição"""
        
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcrição do Ticket - {ticket_info['canal']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .ticket-name {{
            font-size: 20px;
            opacity: 0.9;
            margin-bottom: 20px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        
        .info-item {{
            text-align: left;
        }}
        
        .info-item .label {{
            font-size: 12px;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .info-item .value {{
            font-size: 16px;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-around;
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat .number {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat .label {{
            font-size: 14px;
            color: #6c757d;
            margin-top: 5px;
        }}
        
        .messages {{
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
            background: #f8f9fa;
        }}
        
        .message {{
            display: flex;
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message-avatar {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            margin-right: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 20px;
            flex-shrink: 0;
        }}
        
        .message-avatar img {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
        }}
        
        .message-content {{
            flex: 1;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .message-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .message-author {{
            font-weight: bold;
            color: #333;
        }}
        
        .message-time {{
            color: #999;
        }}
        
        .message-text {{
            font-size: 15px;
            line-height: 1.5;
            color: #444;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .message-attachments {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e9ecef;
        }}
        
        .attachment-link {{
            display: inline-block;
            margin-right: 10px;
            padding: 5px 10px;
            background: #e9ecef;
            border-radius: 5px;
            color: #667eea;
            text-decoration: none;
            font-size: 13px;
        }}
        
        .attachment-link:hover {{
            background: #dee2e6;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
            font-size: 14px;
        }}
        
        .system-message {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                border-radius: 10px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .info-grid {{
                grid-template-columns: 1fr;
            }}
            
            .message {{
                flex-direction: column;
            }}
            
            .message-avatar {{
                margin-bottom: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Transcrição do Ticket</h1>
            <div class="ticket-name">#{ticket_info['canal']}</div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="label">📅 Criado em</div>
                    <div class="value">{ticket_info['criado_em']}</div>
                </div>
                <div class="info-item">
                    <div class="label">🔒 Fechado em</div>
                    <div class="value">{ticket_info['fechado_em']}</div>
                </div>
                <div class="info-item">
                    <div class="label">👑 Fechado por</div>
                    <div class="value">{ticket_info['fechado_por']}</div>
                </div>
                <div class="info-item">
                    <div class="label">📝 Tópico</div>
                    <div class="value">{ticket_info['topic']}</div>
                </div>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="number">{ticket_info['total_mensagens']}</div>
                <div class="label">Mensagens</div>
            </div>
            <div class="stat">
                <div class="number">{len(set(m['autor_id'] for m in mensagens))}</div>
                <div class="label">Participantes</div>
            </div>
            <div class="stat">
                <div class="number">{sum(1 for m in mensagens if m['anexos'])}</div>
                <div class="label">Anexos</div>
            </div>
        </div>
        
        <div class="messages">
"""
        
        for msg in mensagens:
            # Pular mensagens de sistema (se quiser)
            if msg['autor'] == "Sistema":
                html += f"""
            <div class="system-message">
                <strong>🔧 Sistema</strong> - {msg['data']}<br>
                {msg['conteudo']}
            </div>
"""
            else:
                avatar_html = ""
                if msg['autor_avatar']:
                    avatar_html = f'<img src="{msg["autor_avatar"]}" alt="Avatar">'
                else:
                    # Usar iniciais se não tiver avatar
                    iniciais = ''.join([p[0] for p in msg['autor'].split() if p][:2]).upper()
                    avatar_html = f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;">{iniciais}</div>'
                
                html += f"""
            <div class="message">
                <div class="message-avatar">
                    {avatar_html}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-author">{msg['autor']}</span>
                        <span class="message-time">{msg['data']}</span>
                    </div>
                    <div class="message-text">
                        {msg['conteudo'].replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>') if msg['conteudo'] else '<em>Sem conteúdo</em>'}
                    </div>
"""
                
                if msg['anexos']:
                    html += f"""
                    <div class="message-attachments">
                        <strong>📎 Anexos:</strong><br>
"""
                    for anexo in msg['anexos']:
                        html += f'                        <a href="{anexo}" class="attachment-link" target="_blank">📷 Ver anexo</a>\n'
                    html += "                    </div>\n"
                
                html += "                </div>\n            </div>\n"
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>📌 Transcrição gerada automaticamente pelo sistema de tickets • {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p style="font-size: 12px; margin-top: 10px;">Total de {ticket_info['total_mensagens']} mensagens • ID do Ticket: {ticket_info['canal']}</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html

# Instância global do logger
ticket_logger = TicketLogger()

# ========== CLASSES PRINCIPAIS ==========

class TicketFinalizadoView(ui.View):
    """View após ticket fechado - USUÁRIO NÃO PODE FAZER NADA"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Bloquear qualquer interação de usuário"""
        if not usuario_e_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Você não pode interagir com tickets fechados! Aguarde a staff.",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="✅ Reabrir Ticket (Staff)", style=ButtonStyle.green, custom_id="staff_reabrir_ticket")
    async def reabrir_ticket_staff(self, interaction: discord.Interaction, button: ui.Button):
        """Apenas staff pode reabrir"""
        await interaction.response.defer()
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = True
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        if self.ticket_channel.name.startswith("🔒-"):
            novo_nome = f"🎫-{self.ticket_channel.name[2:]}"
            await self.ticket_channel.edit(name=novo_nome)
        
        embed_reaberto = discord.Embed(
            title="🔄 Ticket Reaberto",
            description=f"Ticket reaberto por {interaction.user.mention}",
            color=discord.Color.blue()
        )
        
        # Criar views novamente
        staff_view = TicketStaffView(self.ticket_owner_id, self.ticket_channel)
        user_view = TicketUserView(self.ticket_owner_id, self.ticket_channel)
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        await self.ticket_channel.send(embed=embed_reaberto)
        await self.ticket_channel.send("**🔧 Painel da Staff:**", view=staff_view)
        await self.ticket_channel.send("**👤 Painel do Usuário:**", view=user_view)

class TicketUserView(ui.View):
    """View do usuário - APENAS FECHAR TICKET"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se é o dono do ticket"""
        if interaction.user.id != self.ticket_owner_id:
            await interaction.response.send_message(
                "❌ Apenas quem abriu o ticket pode usar este painel!",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", custom_id="user_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        """Usuário pode fechar o próprio ticket"""
        await interaction.response.defer()
        
        # Salvar transcrição antes de fechar
        arquivo_transcricao = await ticket_logger.salvar_transcricao(self.ticket_channel, interaction.user)
        
        # Enviar transcrição para o usuário
        if arquivo_transcricao and os.path.exists(arquivo_transcricao):
            try:
                with open(arquivo_transcricao, 'rb') as f:
                    await interaction.user.send(
                        "📋 **Transcrição do seu ticket**\n"
                        "Aqui está o histórico completo do seu ticket:",
                        file=discord.File(f, f"transcricao_ticket.html")
                    )
            except:
                try:
                    await interaction.user.send("✅ Seu ticket foi fechado, mas não foi possível enviar a transcrição (DM fechada).")
                except:
                    pass
        
        # Fechar o ticket
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.ticket_channel.edit(overwrites=overwrites)
        if not self.ticket_channel.name.startswith("🔒-"):
            await self.ticket_channel.edit(name=f"🔒-{self.ticket_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            user_info = f"{user.mention}\nID: `{user.id}`"
        except:
            user_info = f"ID: `{self.ticket_owner_id}`"
        
        embed_fechado = discord.Embed(
            title="📋 Ticket Fechado",
            description=(
                f"**👤 Usuário:** {user_info}\n"
                f"**👑 Fechado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.ticket_channel.send(embed=embed_fechado)
        
        # Enviar painel da staff para reabrir
        await self.ticket_channel.send(
            "**🔧 Painel da Staff (reabrir ticket):**", 
            view=TicketFinalizadoView(self.ticket_owner_id, self.ticket_channel)
        )

class TicketStaffView(ui.View):
    """View da staff - FECHAR E DELETAR"""
    def __init__(self, ticket_owner_id, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se é staff"""
        if not usuario_e_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Este painel é apenas para a staff!",
                ephemeral=True
            )
            return False
        return True
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", custom_id="staff_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        """Staff pode fechar o ticket"""
        await interaction.response.defer()
        
        # Salvar transcrição
        arquivo_transcricao = await ticket_logger.salvar_transcricao(self.ticket_channel, interaction.user)
        
        # Enviar transcrição para o dono do ticket
        if arquivo_transcricao and os.path.exists(arquivo_transcricao):
            try:
                dono = await interaction.client.fetch_user(self.ticket_owner_id)
                with open(arquivo_transcricao, 'rb') as f:
                    await dono.send(
                        "📋 **Transcrição do seu ticket**\n"
                        "Seu ticket foi fechado pela staff. Aqui está o histórico completo:",
                        file=discord.File(f, f"transcricao_ticket.html")
                    )
            except:
                pass
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = False
        
        await self.ticket_channel.edit(overwrites=overwrites)
        if not self.ticket_channel.name.startswith("🔒-"):
            await self.ticket_channel.edit(name=f"🔒-{self.ticket_channel.name}")
        
        self.clear_items()
        await interaction.message.edit(view=self)
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            user_info = f"{user.mention}\nID: `{user.id}`"
        except:
            user_info = f"ID: `{self.ticket_owner_id}`"
        
        embed_fechado = discord.Embed(
            title="📋 Ticket Fechado",
            description=(
                f"**👤 Usuário:** {user_info}\n"
                f"**👑 Fechado por:** {interaction.user.mention}\n"
                f"**📅 Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ),
            color=discord.Color.orange()
        )
        
        await self.ticket_channel.send(embed=embed_fechado)
        await self.ticket_channel.send("**🔧 Painel da Staff (reabrir):**", view=TicketFinalizadoView(self.ticket_owner_id, self.ticket_channel))
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", custom_id="staff_delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: ui.Button):
        """Staff pode deletar o ticket"""
        await interaction.response.defer()
        
        # Salvar transcrição antes de deletar
        arquivo_transcricao = await ticket_logger.salvar_transcricao(self.ticket_channel, interaction.user)
        
        # Enviar transcrição para o dono
        if arquivo_transcricao and os.path.exists(arquivo_transcricao):
            try:
                dono = await interaction.client.fetch_user(self.ticket_owner_id)
                with open(arquivo_transcricao, 'rb') as f:
                    await dono.send(
                        "🗑️ **Seu ticket foi deletado**\n"
                        "Aqui está a transcrição completa do ticket antes da deleção:",
                        file=discord.File(f, f"transcricao_ticket.html")
                    )
            except:
                pass
        
        embed = discord.Embed(
            title="🗑️ Ticket Deletado",
            description=f"Ticket deletado por {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await self.ticket_channel.send(embed=embed)
        
        await asyncio.sleep(3)
        await self.ticket_channel.delete()

class TicketOpenView(ui.View):
    """View inicial - apenas botão para abrir ticket"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Abrir Ticket", style=ButtonStyle.primary, emoji="🎫", custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        print(f"[TICKET] Iniciando criação de ticket para {interaction.user.name}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 1. VERIFICAÇÃO DO CANAL BASE
            canal_ticket_base = None
            
            for channel in interaction.guild.text_channels:
                channel_lower = channel.name.lower()
                if "ticket" in channel_lower or "𝐓𝐢𝐜𝐤𝐞𝐭" in channel.name:
                    canal_ticket_base = channel
                    print(f"[TICKET] Canal base encontrado: {channel.name}")
                    break
            
            if not canal_ticket_base:
                print("[TICKET] Nenhum canal com 'ticket' encontrado")
                await interaction.followup.send(
                    "❌ Nenhum canal com 'ticket' no nome foi encontrado!",
                    ephemeral=True
                )
                return
            
            # 2. VERIFICAR CATEGORIA
            categoria = canal_ticket_base.category
            
            if not categoria:
                categoria = interaction.channel.category
            
            if not categoria:
                print("[TICKET] Nenhuma categoria disponível")
                await interaction.followup.send(
                    "❌ Não foi possível determinar a categoria para o ticket!",
                    ephemeral=True
                )
                return
            
            print(f"[TICKET] Categoria: {categoria.name}")
            
            # 3. VERIFICAR TICKETS EXISTENTES
            tickets_abertos = []
            for channel in categoria.channels:
                if isinstance(channel, discord.TextChannel):
                    if channel.topic and str(interaction.user.id) in channel.topic:
                        tickets_abertos.append(channel)
                        print(f"[TICKET] Ticket já aberto: {channel.name}")
            
            if tickets_abertos:
                await interaction.followup.send(
                    f"❌ Você já tem um ticket aberto: {tickets_abertos[0].mention}",
                    ephemeral=True
                )
                return
            
            # 4. CONFIGURAR PERMISSÕES
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False
                ),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
            
            # 5. ADICIONAR CARGOS STAFF
            cargos_staff = get_cargos_staff(interaction.guild)
            for role in cargos_staff:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True
                )
                print(f"[TICKET] Cargo staff adicionado: {role.name} (posição: {role.position})")
            
            # 6. CRIAR CANAL
            nome_usuario = interaction.user.display_name
            nome_limpo = ''.join(c for c in nome_usuario if c.isalnum() or c in [' ', '-', '_'])
            nome_limpo = nome_limpo.strip()
            
            if not nome_limpo:
                nome_limpo = f"user{interaction.user.id}"
            
            nome_canal = f"🎫-{nome_limpo[:20]}"
            print(f"[TICKET] Criando canal: {nome_canal}")
            
            ticket_channel = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user.name} | ID: {interaction.user.id}",
                reason=f"Ticket criado por {interaction.user.name}"
            )
            
            print(f"[TICKET] Canal criado: {ticket_channel.name}")
            
            # 7. ENVIAR MENSAGENS NO TICKET
            embed = discord.Embed(
                title=f"🎫 Ticket de {interaction.user.display_name}",
                description=(
                    f"**👤 Aberto por:** {interaction.user.mention}\n"
                    f"**🆔 ID:** `{interaction.user.id}`\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    "**📝 Descreva seu problema ou dúvida abaixo:**"
                ),
                color=discord.Color.purple()
            )
            
            # Criar as views
            staff_view = TicketStaffView(interaction.user.id, ticket_channel)
            user_view = TicketUserView(interaction.user.id, ticket_channel)
            
            await ticket_channel.send(
                content=f"## 👋 Olá {interaction.user.mention}!\nSeu ticket foi criado com sucesso.",
                embed=embed
            )
            
            # Enviar painéis
            await ticket_channel.send("**🔧 Painel da Staff:**", view=staff_view)
            await ticket_channel.send("**👤 Painel do Usuário:**", view=user_view)
            
            # 8. CONFIRMAR PARA O USUÁRIO
            await interaction.followup.send(
                f"✅ **Ticket criado com sucesso!**\nAcesse: {ticket_channel.mention}",
                ephemeral=True
            )
            
            print(f"[TICKET] Ticket criado com SUCESSO para {interaction.user.name}")
            
        except discord.Forbidden:
            print("[ERRO] Permissão negada")
            await interaction.followup.send(
                "❌ **Erro de permissão!**",
                ephemeral=True
            )
            
        except discord.HTTPException as e:
            print(f"[ERRO] HTTP {e.status}")
            await interaction.followup.send(
                f"❌ **Erro do Discord:** Tente novamente.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"[ERRO] {type(e).__name__}: {e}")
            await interaction.followup.send(
                f"❌ **Erro:** `{type(e).__name__}`",
                ephemeral=True
            )

# ========== COMANDOS ==========

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Tickets carregado!")
    
    @commands.command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Configura o painel de tickets"""
        print(f"[SETUP] Configurando painel por {ctx.author.name}")
        
        # Verificar se o cargo base existe
        cargo_base = ctx.guild.get_role(CARGO_BASE_ID)
        if not cargo_base:
            await ctx.send(f"⚠️ **Cargo base não encontrado!**\nID: `{CARGO_BASE_ID}`\nVerifique se o ID está correto.")
            return
        
        embed_info = discord.Embed(
            title="🎫 **SISTEMA DE TICKETS**",
            description=(
                "**Clique no botão abaixo para abrir um ticket**\n\n"
                "Escolha esta opção se você precisa de ajuda com:\n"
                "• Dúvidas privadas\n"
                "• Entrega de farm\n"
                "• Reportar jogadores\n"
                "• Outras questões importantes"
            ),
            color=discord.Color.purple()
        )
        
        embed_info.set_image(url="")
        embed_info.set_footer(text="Sistema de ticket • WaveX")
        
        view = TicketOpenView()
        
        await ctx.send(embed=embed_info, view=view)
        await ctx.message.delete()
        
        print(f"[SETUP] Painel configurado em #{ctx.channel.name}")
    
    @commands.command(name="verificar_acesso")
    @commands.has_permissions(administrator=True)
    async def verificar_acesso(self, ctx, member: discord.Member = None):
        """Verifica se um membro pode ver o painel"""
        if member is None:
            member = ctx.author
        
        e_staff = usuario_e_staff(member)
        
        cargo_base = ctx.guild.get_role(CARGO_BASE_ID)
        
        embed = discord.Embed(
            title="🔍 Verificação de Acesso",
            color=discord.Color.green() if not e_staff else discord.Color.red()
        )
        
        embed.add_field(name="👤 Usuário", value=member.mention, inline=True)
        embed.add_field(name="👑 É Staff?", value="SIM" if e_staff else "NÃO", inline=True)
        
        if cargo_base:
            embed.add_field(name="🎯 Cargo Base", value=f"{cargo_base.mention}\nPosição: {cargo_base.position}", inline=True)
            
            # Listar cargos do usuário
            cargos_staff = []
            for role in member.roles:
                if role.position >= cargo_base.position and role.name != "@everyone":
                    cargos_staff.append(f"{role.name} (pos: {role.position})")
            
            if cargos_staff:
                embed.add_field(
                    name="📋 Cargos de Staff",
                    value="\n".join(cargos_staff[:5]),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="transcricao")
    @commands.has_permissions(administrator=True)
    async def transcricao_manual(self, ctx, channel: discord.TextChannel = None):
        """Gera transcrição manual de um ticket"""
        if channel is None:
            channel = ctx.channel
        
        await ctx.send("📋 Gerando transcrição...")
        
        arquivo = await ticket_logger.salvar_transcricao(channel, ctx.author)
        
        if arquivo and os.path.exists(arquivo):
            with open(arquivo, 'rb') as f:
                await ctx.send(
                    "✅ **Transcrição gerada com sucesso!**",
                    file=discord.File(f, f"transcricao_{channel.name}.html")
                )
        else:
            await ctx.send("❌ Erro ao gerar transcrição!")

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    bot.add_view(TicketOpenView())
    print("✅ Sistema de Tickets configurado com views persistentes!")
