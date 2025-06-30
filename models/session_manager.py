import threading
import time
import uuid
from datetime import datetime
from collections import defaultdict
import queue
from config import MAX_USUARIOS_SIMULTANEOS, TIMEOUT_SESSAO, CLEANUP_INTERVAL, TEMPO_RESPOSTA_ESTIMADO

class SessionManager:
    def __init__(self):
        self.sessoes_ativas = {}
        self.fila_espera = queue.Queue()
        self.lock = threading.Lock()
        self.stats = {
            'total_requests': 0,
            'requests_rejeitados': 0,
            'tempo_medio_resposta': 0,
            'usuarios_unicos_hoje': []
        }
        self.inicio = time.time()
        
        print("Inicializando gerenciador de sessões...")
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessoes, daemon=True)
        self.cleanup_thread.start()
        print(f"Limite: {MAX_USUARIOS_SIMULTANEOS} usuários")
    
    def pode_entrar(self):
        """Verifica se há vagas disponíveis"""
        with self.lock:
            return len(self.sessoes_ativas) < MAX_USUARIOS_SIMULTANEOS
    
    def criar_sessao(self, user_ip):
        """Cria nova sessão se houver vaga"""
        with self.lock:
            if len(self.sessoes_ativas) < MAX_USUARIOS_SIMULTANEOS:
                session_id = str(uuid.uuid4())
                self.sessoes_ativas[session_id] = {
                    'ip': user_ip,
                    'inicio': time.time(),
                    'ultima_atividade': time.time(),
                    'requests_count': 0,
                    'chat_history': []
                }
                if user_ip not in self.stats['usuarios_unicos_hoje']:
                    self.stats['usuarios_unicos_hoje'].append(user_ip)
                print(f" Nova sessão criada: {session_id[:8]}... (IP: {user_ip})")
                print(f"👥 Ativos: {len(self.sessoes_ativas)}/{MAX_USUARIOS_SIMULTANEOS}")
                return session_id
            else:
                print(f" Sistema ocupado: {len(self.sessoes_ativas)}/{MAX_USUARIOS_SIMULTANEOS}")
                return None
    
    def atualizar_atividade(self, session_id):
        """Atualiza timestamp da última atividade"""
        with self.lock:
            if session_id in self.sessoes_ativas:
                self.sessoes_ativas[session_id]['ultima_atividade'] = time.time()
                self.sessoes_ativas[session_id]['requests_count'] += 1
                return True
            return False
    
    def get_session_data(self, session_id):
        """Retorna dados da sessão com logs detalhados"""
        if not session_id:
            print(f" [SESSION] session_id é None ou vazio")
            return None
            
        with self.lock:
            if session_id in self.sessoes_ativas:
                self.sessoes_ativas[session_id]['ultima_atividade'] = time.time()
                print(f" [SESSION] Sessão encontrada e atividade atualizada: {session_id[:8]}...")
                return self.sessoes_ativas[session_id]
            else:
                print(f" [SESSION] Sessão não encontrada: {session_id[:8]}...")
                print(f" [SESSION] Sessões disponíveis: {[sid[:8] + '...' for sid in self.sessoes_ativas.keys()]}")
                return None
    
    def debug_sessoes_ativas(self):
        """Debug das sessões ativas"""
        with self.lock:
            print(f"[DEBUG] === SESSÕES ATIVAS ({len(self.sessoes_ativas)}) ===")
            if not self.sessoes_ativas:
                print(f"[DEBUG] Nenhuma sessão ativa")
            else:
                for sid, dados in self.sessoes_ativas.items():
                    tempo_inativo = time.time() - dados['ultima_atividade']
                    print(f"[DEBUG] {sid[:8]}... IP:{dados['ip']} Inativo:{tempo_inativo:.1f}s Requests:{dados['requests_count']}")
            print(f"[DEBUG] ===============================")
    
    def get_chat_history(self, session_id):
        """Retorna histórico de chat da sessão"""
        with self.lock:
            if session_id in self.sessoes_ativas:
                return self.sessoes_ativas[session_id].get('chat_history', [])
            return []
    
    def update_chat_history(self, session_id, history):
        """Atualiza histórico de chat da sessão"""
        with self.lock:
            if session_id in self.sessoes_ativas:
                self.sessoes_ativas[session_id]['chat_history'] = history[-20:]
                self.sessoes_ativas[session_id]['ultima_atividade'] = time.time()
                print(f" [SESSION] Histórico atualizado para {session_id[:8]}...: {len(history)} mensagens")
                return True
            else:
                print(f" [SESSION] Tentativa de atualizar histórico de sessão inexistente: {session_id[:8]}...")
                return False
    
    def remover_sessao(self, session_id, motivo="manual"):
        """Remove sessão específica"""
        with self.lock:
            if session_id in self.sessoes_ativas:
                ip = self.sessoes_ativas[session_id]['ip']
                del self.sessoes_ativas[session_id]
                print(f" Sessão removida: {session_id[:8]}... - {motivo} (IP: {ip})")
                print(f"👥 Ativos: {len(self.sessoes_ativas)}/{MAX_USUARIOS_SIMULTANEOS}")
                return True
            return False
    
    def get_status(self):
        """Status do sistema"""
        with self.lock:
            return {
                'usuarios_ativos': len(self.sessoes_ativas),
                'maximo_usuarios': MAX_USUARIOS_SIMULTANEOS,
                'fila_espera': self.fila_espera.qsize(),
                'sessoes_ativas': list(self.sessoes_ativas.keys()),
                'uptime': time.time() - self.inicio,
                'stats': {
                    'total_requests': self.stats['total_requests'],
                    'requests_rejeitados': self.stats['requests_rejeitados'],
                    'tempo_medio_resposta': self.stats['tempo_medio_resposta'],
                    'usuarios_unicos_hoje': len(self.stats['usuarios_unicos_hoje'])
                }
            }
    
    def get_posicao_fila(self, user_ip):
        """Posição na fila"""
        posicao = self.fila_espera.qsize() + 1
        tempo_estimado = posicao * TEMPO_RESPOSTA_ESTIMADO
        
        return {
            'posicao': posicao,
            'tempo_estimado': tempo_estimado,
            'tempo_estimado_str': f"{tempo_estimado}s" if tempo_estimado < 60 else f"{tempo_estimado//60}m{tempo_estimado%60}s"
        }
    
    def _cleanup_sessoes(self):
        """Thread de limpeza automática - MELHORADA"""
        print(" Thread de limpeza iniciada")
        
        while True:
            try:
                agora = time.time()
                sessoes_expiradas = []
                
                with self.lock:
                    for sid, dados in list(self.sessoes_ativas.items()):
                        tempo_inativo = agora - dados['ultima_atividade']
                        if tempo_inativo > TIMEOUT_SESSAO:
                            sessoes_expiradas.append((sid, dados['ip'], tempo_inativo))
                
                for sid, ip, tempo_inativo in sessoes_expiradas:
                    self.remover_sessao(sid, f"timeout ({tempo_inativo:.0f}s)")
                
                if sessoes_expiradas:
                    print(f" {len(sessoes_expiradas)} sessões expiradas removidas")
                elif len(self.sessoes_ativas) > 0:
                    if int(agora) % 300 == 0:
                        print(f" {len(self.sessoes_ativas)} sessões ativas mantidas")
                
                time.sleep(CLEANUP_INTERVAL)
                
            except Exception as e:
                print(f" Erro na limpeza: {e}")
                time.sleep(CLEANUP_INTERVAL)

session_manager = SessionManager()