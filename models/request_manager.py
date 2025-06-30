import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass
import uuid

@dataclass
class ActiveRequest:
    id: str
    session_id: str
    timestamp: float
    cancelled: bool = False
    thread_id: Optional[int] = None

class RequestManager:
    def __init__(self):
        self.active_requests: Dict[str, ActiveRequest] = {}
        self.lock = threading.Lock()
        print(" RequestManager inicializado")
    
    def start_request(self, session_id: str) -> str:
        """Inicia uma nova request e cancela as anteriores da sessão"""
        request_id = str(uuid.uuid4())
    
        with self.lock:
            active_requests = [r for r in self.active_requests.values() 
                          if r.session_id == session_id and not r.cancelled]
        
        if active_requests:
            print(f" Sessão {session_id[:8]}... já tem {len(active_requests)} request(s) ativa(s)")
            self.cancel_session_requests(session_id)
            print(f" Todas as requests anteriores da sessão {session_id[:8]}... foram canceladas")
        
        request = ActiveRequest(
            id=request_id,
            session_id=session_id,
            timestamp=time.time(),
            thread_id=threading.current_thread().ident
        )
        
        self.active_requests[request_id] = request
        print(f"Request {request_id[:8]}... iniciada para sessão {session_id[:8]}...")
        
        return request_id
    
    def finish_request(self, request_id: str):
        """Marca request como finalizada"""
        with self.lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
                print(f" Request {request_id[:8]}... finalizada")
    
    def cancel_request(self, request_id: str):
        """Cancela request específica"""
        with self.lock:
            if request_id in self.active_requests:
                self.active_requests[request_id].cancelled = True
                print(f" Request {request_id[:8]}... cancelada")
                return True
        return False
    
    def cancel_session_requests(self, session_id: str):
        """Cancela todas as requests de uma sessão"""
        cancelled_count = 0
        for request in self.active_requests.values():
            if request.session_id == session_id and not request.cancelled:
                request.cancelled = True
                cancelled_count += 1
                print(f" Request {request.id[:8]}... da sessão {session_id[:8]}... cancelada")
        
        if cancelled_count > 0:
            print(f" Total: {cancelled_count} requests canceladas da sessão {session_id[:8]}...")
    
    def is_cancelled(self, request_id: str) -> bool:
        """Verifica se request foi cancelada"""
        with self.lock:
            request = self.active_requests.get(request_id)
            return request.cancelled if request else True
    
    def get_active_count(self) -> int:
        """Retorna número de requests ativas"""
        with self.lock:
            return len([r for r in self.active_requests.values() if not r.cancelled])
    
    def cleanup_old_requests(self):
        """Limpa requests antigas (mais de 5 minutos)"""
        cutoff_time = time.time() - 300
        
        with self.lock:
            to_remove = []
            for request_id, request in self.active_requests.items():
                if request.timestamp < cutoff_time:
                    to_remove.append(request_id)
            
            for request_id in to_remove:
                del self.active_requests[request_id]
                print(f" Request antiga {request_id[:8]}... removida")

request_manager = RequestManager()

def cleanup_thread():
    while True:
        time.sleep(60)
        request_manager.cleanup_old_requests()

cleanup_thread = threading.Thread(target=cleanup_thread, daemon=True)
cleanup_thread.start()