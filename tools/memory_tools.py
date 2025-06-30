from models.database import db_manager

def salvar_dados(chave, valor, categoria="geral", session_id=None):
    """Salva dados na memória da IA - COM ISOLAMENTO POR SESSÃO"""
    if not session_id:
        return {"status": "erro", "mensagem": "session_id é obrigatório para isolamento"}
    
    return db_manager.salvar_dados(chave, valor, categoria, session_id=session_id)

def buscar_dados(chave=None, categoria=None, session_id=None):
    """Busca dados salvos na memória da IA - COM ISOLAMENTO POR SESSÃO"""
    if not session_id:
        return {"status": "erro", "mensagem": "session_id é obrigatório para isolamento"}
    
    return db_manager.buscar_dados(chave, categoria, session_id=session_id)

def deletar_dados(chave, session_id=None):
    """Remove dados salvos da memória da IA - COM ISOLAMENTO POR SESSÃO"""
    if not session_id:
        return {"status": "erro", "mensagem": "session_id é obrigatório para isolamento"}
    
    # 🔧 CORREÇÃO: A função JÁ está implementada!
    return db_manager.deletar_dados(chave, session_id=session_id)

def listar_categorias(session_id=None):
    """Lista todas as categorias de dados salvos - COM ISOLAMENTO POR SESSÃO"""
    if not session_id:
        return {"status": "erro", "mensagem": "session_id é obrigatório para isolamento"}
    
    # 🔧 CORREÇÃO: A função JÁ está implementada!
    return db_manager.listar_categorias(session_id=session_id)