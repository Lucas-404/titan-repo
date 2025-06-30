import json
import shutil
import os
import re
from datetime import datetime
from pathlib import Path
from config import CHAT_HISTORY_FILE, BACKUPS_DIR, EXPORTS_DIR, MAX_BACKUPS, PLAN_LIMITS
from flask import g
from flask import g

class ChatManager:
    def __init__(self):
        self.base_history_dir = Path(CHAT_HISTORY_FILE).parent / "sessions"
        self.base_history_dir.mkdir(exist_ok=True)
        
        # SEGURANÇA: Diretório base absoluto para validação
        self.safe_base_path = self.base_history_dir.resolve()
        print(f"ChatManager inicializado - Diretório SEGURO: {self.safe_base_path}")
    
    def _validate_session_id(self, session_id):
        """CRÍTICO: Validação rigorosa de session_id"""
        if not session_id:
            raise ValueError("session_id é obrigatório")
        
        # 1. Verificar tipo
        if not isinstance(session_id, str):
            raise ValueError("session_id deve ser string")
        
        # 2. Verificar tamanho (UUIDs têm ~36 chars)
        if len(session_id) < 10 or len(session_id) > 50:
            raise ValueError("session_id com tamanho inválido")
        
        # 3. CRÍTICO: Bloquear caracteres de path traversal
        dangerous_chars = ['..', '/', '\\', '\0', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in session_id:
                raise ValueError(f"session_id contém caractere proibido: {char}")
        
        # 4. Apenas alphanúmerico, hífens e underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValueError("session_id contém caracteres inválidos")
        
        # 5. Não pode começar com pontos
        if session_id.startswith('.'):
            raise ValueError("session_id não pode começar com ponto")
        
        return session_id
    
    def _get_safe_session_dir(self, session_id):
        """CRÍTICO: Criação segura de diretório de sessão"""
        # 1. Validar session_id primeiro
        safe_session_id = self._validate_session_id(session_id)
        
        # 2. Usar apenas os primeiros 8 caracteres (mais seguro)
        safe_prefix = safe_session_id[:8]
        
        # 3. Construir caminho de forma segura
        session_dir = self.safe_base_path / safe_prefix
        
        # 4. CRÍTICO: Resolver o caminho e verificar se está dentro do base
        resolved_session_dir = session_dir.resolve()
        
        # 5. Verificar se o caminho final está dentro do diretório seguro
        try:
            resolved_session_dir.relative_to(self.safe_base_path)
        except ValueError:
            raise ValueError(f"Tentativa de path traversal detectada: {session_id}")
        
        # 6. Criar diretório se não existir
        resolved_session_dir.mkdir(exist_ok=True)
        
        print(f"Diretório seguro criado: {resolved_session_dir}")
        return resolved_session_dir
    
    def _get_session_file(self, session_id):
        """BLINDADO: Retorna arquivo específico da sessão"""
        try:
            # 1. Obter diretório seguro
            session_dir = self._get_safe_session_dir(session_id)
            
            # 2. Nome do arquivo fixo (não baseado em input do usuário)
            safe_filename = "chats.json"
            
            # 3. Construir caminho final
            session_file = session_dir / safe_filename
            
            # 4. Validação final de segurança
            resolved_file = session_file.resolve()
            
            # 5. Verificar se o arquivo está dentro do diretório da sessão
            try:
                resolved_file.relative_to(session_dir)
            except ValueError:
                raise ValueError("Tentativa de escapar do diretório da sessão")
            
            return resolved_file
            
        except Exception as e:
            print(f"🚨 SECURITY ALERT: Tentativa de acesso inseguro - session_id: {session_id[:20]}...")
            print(f"🚨 Erro: {str(e)}")
            raise ValueError("Acesso negado por motivos de segurança")
    
    def _sanitize_filename(self, filename):
        """Sanitização de nomes de arquivo"""
        if not filename or not isinstance(filename, str):
            return "arquivo_seguro"
        
        # Remover caracteres perigosos
        filename = re.sub(r'[^\w\s\-_\.]', '', filename)
        
        # Limitar tamanho
        filename = filename[:50]
        
        # Garantir que não está vazio
        if not filename.strip():
            filename = "arquivo_seguro"
        
        # Não pode começar com ponto
        if filename.startswith('.'):
            filename = "arquivo_" + filename[1:]
        
        return filename
    
    def load_history(self, session_id=None):
        """SEGURO: Carregar histórico APENAS da sessão específica"""
        if not session_id:
            return []
        
        try:
            session_file = self._get_session_file(session_id)
            
            if session_file.exists():
                # Verificar tamanho do arquivo (proteção DoS)
                file_size = session_file.stat().st_size
                if file_size > 50 * 1024 * 1024:  # 50MB máximo
                    print(f" Arquivo muito grande: {file_size} bytes")
                    return []
                
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validar estrutura dos dados
                if not isinstance(data, list):
                    print(f" Estrutura inválida do arquivo")
                    return []
                
                # Limitar número de conversas (proteção memória)
                if len(data) > 1000:
                    print(f" Muitas conversas, limitando a 1000")
                    data = data[:1000]
                
                print(f"📂 Histórico carregado SEGURAMENTE da sessão {session_id[:8]}...: {len(data)} conversas")
                return data
            
            print(f"📂 Nenhum histórico para sessão {session_id[:8]}... - criando novo")
            return []
            
        except Exception as e:
            print(f" Erro SEGURO ao carregar histórico da sessão {session_id[:8]}...: {str(e)[:100]}")
            return []
    
    def save_history(self, chat_history, session_id=None):
        if not session_id:
            print(" session_id é obrigatório para salvar histórico")
            return False

        # Verificar limite de mensagens para usuários anônimos
        if not g.user:
            user_messages = 0
            for chat in chat_history:
                if isinstance(chat, dict) and 'messages' in chat:
                    for message in chat['messages']:
                        if message.get('role') == 'user':
                            user_messages += 1
            
            limit = PLAN_LIMITS['free']['messages_per_day']
            if user_messages > limit:
                raise PermissionError(f"Limite de {limit} mensagens atingido para usuários anônimos.")

        if not isinstance(chat_history, list):
            print(" chat_history deve ser uma lista")
            return False
        
        if len(chat_history) > 1000:
            print(" Muitas conversas, limitando a 1000")
            chat_history = chat_history[:1000]
        
        try:
            session_file = self._get_session_file(session_id)
        
            if session_file.exists():
                self._create_backup(session_id)
        
            session_dir = session_file.parent
            session_dir.mkdir(parents=True, exist_ok=True)
        
        # Adicionar thinking ao chat_history se presente
            updated_history = []
            for chat in chat_history:
                if isinstance(chat, dict) and 'messages' in chat:
                    last_message = chat['messages'][-1] if chat['messages'] else {}
                    if last_message.get('role') == 'assistant' and 'thinking' in last_message:
                        chat['thinking'] = last_message['thinking']
                updated_history.append(chat)
        
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(updated_history, f, ensure_ascii=False, indent=2)
        
            os.chmod(session_file, 0o600)
        
            print(f"💾 Histórico salvo SEGURAMENTE para sessão {session_id[:8]}...: {len(updated_history)} conversas")
            return True
        
        except Exception as e:
            print(f" Erro SEGURO ao salvar histórico da sessão {session_id[:8]}...: {str(e)[:100]}")
            return False
    
    def _get_safe_backup_dir(self, session_id):
        """Diretório seguro para backups"""
        safe_session_id = self._validate_session_id(session_id)
        backup_base = Path(BACKUPS_DIR).resolve()
        backup_dir = backup_base / safe_session_id[:8]
        
        # Verificar se está dentro do diretório de backup
        resolved_backup = backup_dir.resolve()
        try:
            resolved_backup.relative_to(backup_base)
        except ValueError:
            raise ValueError("Tentativa de path traversal em backup")
        
        resolved_backup.mkdir(parents=True, exist_ok=True)
        return resolved_backup
    
    def _create_backup(self, session_id):
        """SEGURO: Criar backup automático da sessão"""
        try:
            session_file = self._get_session_file(session_id)
            if not session_file.exists():
                return
            
            # Gerar timestamp seguro
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Sanitizar timestamp (paranoia)
            timestamp = re.sub(r'[^\w]', '_', timestamp)
            
            backup_dir = self._get_safe_backup_dir(session_id)
            backup_filename = f'backup_{timestamp}.json'
            backup_file = backup_dir / backup_filename
            
            # Verificar se backup file está seguro
            resolved_backup_file = backup_file.resolve()
            try:
                resolved_backup_file.relative_to(backup_dir)
            except ValueError:
                raise ValueError("Tentativa de escapar diretório de backup")
            
            shutil.copy2(session_file, resolved_backup_file)
            
            # Permissões seguras
            os.chmod(resolved_backup_file, 0o600)
            
            # Limpar backups antigos da sessão
            self._cleanup_old_backups(session_id)
            print(f"Backup SEGURO criado para sessão {session_id[:8]}...: {backup_file.name}")
            
        except Exception as e:
            print(f" Erro SEGURO ao criar backup da sessão {session_id[:8]}...: {str(e)[:100]}")
    
    def _cleanup_old_backups(self, session_id):
        """SEGURO: Manter apenas os últimos backups da sessão"""
        try:
            backup_dir = self._get_safe_backup_dir(session_id)
            
            # Listar apenas arquivos .json que começam com 'backup_'
            backups = []
            for file in backup_dir.iterdir():
                if (file.is_file() and 
                    file.name.startswith('backup_') and 
                    file.name.endswith('.json') and
                    len(file.name) < 50):  # Limitar tamanho do nome
                    backups.append(file)
            
            # Ordenar por data de modificação
            backups.sort(key=lambda x: x.stat().st_mtime)
            
            # Remover backups antigos
            while len(backups) > MAX_BACKUPS:
                oldest = backups.pop(0)
                # Verificação final antes de deletar
                if oldest.parent == backup_dir:
                    oldest.unlink()
                    print(f" Backup antigo removido SEGURAMENTE da sessão {session_id[:8]}...: {oldest.name}")
                
        except Exception as e:
            print(f" Erro SEGURO ao limpar backups da sessão {session_id[:8]}...: {str(e)[:100]}")
    
    def get_chat_by_id(self, chat_id, session_id=None):
        """SEGURO: Buscar chat por ID APENAS na sessão específica"""
        if not session_id:
            print(" session_id é obrigatório para buscar chat")
            return None
        
        if not chat_id or not isinstance(chat_id, str):
            print(" chat_id inválido")
            return None
        
        # Limitar tamanho do chat_id
        if len(chat_id) > 100:
            print(" chat_id muito longo")
            return None
        
        history = self.load_history(session_id=session_id)
        
        for chat in history:
            if not isinstance(chat, dict):
                continue
                
            if chat.get('id') == chat_id:
                # Verificação DUPLA de segurança
                if chat.get('session_id') != session_id:
                    print(f" ALERTA DE SEGURANÇA: Chat {chat_id[:20]} com session_id inconsistente!")
                    return None
                return chat
        
        print(f" Chat {chat_id[:20]} não encontrado na sessão {session_id[:8]}...")
        return None
    
    def save_chat(self, chat_data):
        """SEGURO: Salvar conversa específica NA SESSÃO CORRETA"""
        session_id = chat_data.get('session_id') if isinstance(chat_data, dict) else None
        
        if not session_id:
            print(" session_id é obrigatório no chat_data")
            return {'status': 'erro', 'message': 'session_id é obrigatório'}
        
        # Validar estrutura do chat_data
        if not isinstance(chat_data, dict):
            return {'status': 'erro', 'message': 'chat_data deve ser um dicionário'}
        
        # Validar campos obrigatórios
        required_fields = ['id', 'title', 'messages']
        for field in required_fields:
            if field not in chat_data:
                return {'status': 'erro', 'message': f'Campo obrigatório ausente: {field}'}
        
        # Sanitizar dados
        chat_data['title'] = self._sanitize_filename(str(chat_data.get('title', 'Sem título')))
        
        # Limitar tamanho das mensagens
        if isinstance(chat_data.get('messages'), list):
            if len(chat_data['messages']) > 500:
                chat_data['messages'] = chat_data['messages'][:500]
        
        # Carregar histórico APENAS da sessão
        history = self.load_history(session_id=session_id)
        chat_id = chat_data.get('id')
        
        # Verificar se é atualização ou nova conversa
        existing_index = next((i for i, chat in enumerate(history) 
                              if isinstance(chat, dict) and chat.get('id') == chat_id), -1)
        
        if existing_index >= 0:
            # Atualizar conversa existente
            history[existing_index] = chat_data
            action = 'atualizada'
            print(f"Conversa atualizada SEGURAMENTE na sessão {session_id[:8]}...: {chat_data.get('title', 'Sem título')[:30]}")
        else:
            # Nova conversa
            history.insert(0, chat_data)
            action = 'criada'
            print(f"🆕 Nova conversa criada SEGURAMENTE na sessão {session_id[:8]}...: {chat_data.get('title', 'Sem título')[:30]}")
        
        # Salvar SEM backup automático
        try:
            session_file = self._get_session_file(session_id)
            
            # Criar backup manual antes de salvar
            if session_file.exists():
                backup_content = session_file.read_text(encoding='utf-8')
                backup_file = session_file.with_suffix('.json.backup')
                backup_file.write_text(backup_content, encoding='utf-8')
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # Permissões seguras
            os.chmod(session_file, 0o600)
            
            print(f"💾 Histórico salvo SEGURAMENTE para sessão {session_id[:8]}... SEM backup: {len(history)} conversas")
            return {'status': 'sucesso', 'action': action, 'chat_id': chat_id}
        
        except Exception as e:
            print(f" Erro SEGURO ao salvar histórico da sessão {session_id[:8]}...: {str(e)[:100]}")
            return {'status': 'erro', 'message': 'Erro ao salvar'}
    
    def delete_chat(self, chat_id, session_id=None):
        """SEGURO: Excluir chat APENAS da sessão específica"""
        if not session_id:
            print(" session_id é obrigatório para deletar chat")
            return {'status': 'erro', 'message': 'session_id é obrigatório'}
        
        if not chat_id or not isinstance(chat_id, str) or len(chat_id) > 100:
            print(" chat_id inválido")
            return {'status': 'erro', 'message': 'chat_id inválido'}
        
        # Carregar histórico APENAS da sessão
        history = self.load_history(session_id=session_id)
        
        # Encontrar e remover o chat com validação DUPLA
        chat_to_delete = None
        history_filtered = []
        
        for chat in history:
            if not isinstance(chat, dict):
                continue
                
            if chat.get('id') == chat_id:
                # Verificação DUPLA de segurança
                if chat.get('session_id') != session_id:
                    print(f" ALERTA DE SEGURANÇA: Tentativa de deletar chat de outra sessão!")
                    return {'status': 'erro', 'message': 'Chat não encontrado ou sem permissão'}
                chat_to_delete = chat
            else:
                history_filtered.append(chat)
        
        if chat_to_delete:
            if self.save_history(history_filtered, session_id=session_id):
                print(f" Conversa excluída SEGURAMENTE da sessão {session_id[:8]}...: {chat_to_delete.get('title', 'Sem título')[:30]}")
                return {'status': 'sucesso', 'message': 'Conversa excluída'}
            return {'status': 'erro', 'message': 'Falha ao salvar após exclusão'}
        
        return {'status': 'erro', 'message': 'Conversa não encontrada'}
    
# Instância global SEGURA
chat_manager = ChatManager()