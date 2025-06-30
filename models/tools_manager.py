import json
from tools.system_tools import obter_data_hora
from tools.web_search import search_web_comprehensive

class ToolsManager:
    def __init__(self):
        self._tools_cache = None
        self.functions = self._load_functions()
        print(" ToolsManager inicializado - ferramentas otimizadas")
    
    def _load_tools_definitions(self):
        """Definições das ferramentas - SEM INSTRUÇÕES CONFLITANTES"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "obter_data_hora",
                    "description": "Obtém a data e hora atual do sistema, incluindo dia da semana",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "salvar_dados",
                    "description": "Salva informações mencionadas pelo usuário na memória da sessão",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chave": {
                                "type": "string",
                                "description": "Identificador único para o dado (ex: 'nome', 'idade', 'preferencia_musical')"
                            },
                            "valor": {
                                "type": "string",
                                "description": "Informação a ser salva"
                            },
                            "categoria": {
                                "type": "string",
                                "description": "Categoria para organizar (ex: 'pessoal', 'preferencias', 'trabalho')",
                                "default": "geral"
                            }
                        },
                        "required": ["chave", "valor"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "buscar_dados",
                    "description": "Busca informações previamente salvas na memória da sessão",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chave": {
                                "type": "string",
                                "description": "Chave específica para buscar (opcional - se não informada, lista todos)"
                            },
                            "categoria": {
                                "type": "string",
                                "description": "Filtrar por categoria específica (opcional)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "deletar_dados",
                    "description": "Remove informação específica da memória da sessão",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "chave": {
                                "type": "string",
                                "description": "Chave do dado a ser removido"
                            }
                        },
                        "required": ["chave"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "listar_categorias",
                    "description": "Lista todas as categorias de dados salvos na sessão",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web_comprehensive",
                    "description": "Busca informações atuais na internet usando múltiplas fontes confiáveis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Consulta de busca clara e específica. Exemplos: 'preços iPhone 15 Brasil', 'notícias IA 2025', 'como funciona React', 'melhores restaurantes São Paulo'"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def _load_functions(self):
        """Mapeamento das ferramentas com wrappers otimizados"""
        return {
            "obter_data_hora": obter_data_hora,
            "salvar_dados": self._wrapper_salvar_dados,
            "buscar_dados": self._wrapper_buscar_dados,
            "deletar_dados": self._wrapper_deletar_dados,
            "listar_categorias": self._wrapper_listar_categorias,
            "search_web_comprehensive": self._wrapper_search_web
        }
    
    def _wrapper_salvar_dados(self, **argumentos):
        """Wrapper otimizado para salvar_dados"""
        session_id = argumentos.pop('session_id', None)
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}
        
        chave = argumentos.get('chave')
        valor = argumentos.get('valor')
        categoria = argumentos.get('categoria', 'geral')
        
        if not chave or not valor:
            return {"status": "erro", "mensagem": "chave e valor são obrigatórios"}
        
        try:
            from models.database import db_manager
            
            resultado = db_manager.salvar_dados(chave, valor, categoria, session_id)
            
            if resultado['status'] == 'sucesso':
                try:
                    from models.cache_manager import context_cache
                    context_cache.invalidate_context(session_id)
                    print(f"Cache invalidado para session {session_id[:8]}...")
                except ImportError:
                    pass
            
            return resultado
        except Exception as e:
            return {"status": "erro", "mensagem": f"Erro ao salvar: {str(e)}"}
    
    def _wrapper_buscar_dados(self, **argumentos):
        """Wrapper otimizado para buscar_dados"""
        session_id = argumentos.pop('session_id', None)
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}
        
        try:
            from models.database import db_manager
            return db_manager.buscar_dados(
                argumentos.get('chave'), 
                argumentos.get('categoria'), 
                session_id
            )
        except Exception as e:
            return {"status": "erro", "mensagem": f"Erro ao buscar: {str(e)}"}
    
    def _wrapper_deletar_dados(self, **argumentos):
        """Wrapper otimizado para deletar_dados"""
        session_id = argumentos.pop('session_id', None)
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}
        
        chave = argumentos.get('chave')
        if not chave:
            return {"status": "erro", "mensagem": "chave é obrigatória"}
        
        try:
            from models.database import db_manager
            resultado = db_manager.deletar_dados(chave, session_id)
            
            if resultado['status'] == 'sucesso':
                try:
                    from models.cache_manager import context_cache
                    context_cache.invalidate_context(session_id)
                    print(f"Cache invalidado para session {session_id[:8]}...")
                except ImportError:
                    pass
            
            return resultado
        except Exception as e:
            return {"status": "erro", "mensagem": f"Erro ao deletar: {str(e)}"}
    
    def _wrapper_listar_categorias(self, **argumentos):
        """Wrapper otimizado para listar_categorias"""
        session_id = argumentos.pop('session_id', None)
        if not session_id:
            return {"status": "erro", "mensagem": "session_id é obrigatório"}
        
        try:
            from models.database import db_manager
            return db_manager.listar_categorias(session_id)
        except Exception as e:
            return {"status": "erro", "mensagem": f"Erro ao listar: {str(e)}"}
    
    def _wrapper_search_web(self, **argumentos):
        """Wrapper otimizado para busca web com feedback melhorado"""
        query = argumentos.get('query')
        if not query:
            return {"status": "erro", "mensagem": "query é obrigatória"}
        
        try:
            print(f" Iniciando busca na internet: '{query}'")
            resultado = search_web_comprehensive(query)
            
            if resultado['status'] == 'sucesso':
                total = resultado.get('total_resultados', 0)
                fontes = len(resultado.get('fontes_usadas', []))
                print(f" Busca concluída: {total} resultados de {fontes} fontes")
                from tools.web_search import format_search_results
                resultado['resultados_formatados'] = format_search_results(resultado)
                
                resultado['aviso_prioridade'] = "ATENÇÃO: Estas são informações ATUAIS da internet. Priorize sempre estes dados sobre conhecimento pré-treinado."
                
                return resultado
            else:
                print(f" Busca falhou: {resultado.get('mensagem', 'Erro desconhecido')}")
                return resultado
                
        except Exception as e:
            print(f" Erro na busca web: {str(e)}")
            return {
                "status": "erro", 
                "mensagem": f"Erro na busca: {str(e)}",
                "query": query
            }
    
    def get_tools_for_ai(self):
        """Retorna definições das ferramentas com cache"""
        if self._tools_cache is None:
            self._tools_cache = self._load_tools_definitions()
            print(f" Tools cached: {len(self._tools_cache)} ferramentas essenciais")
        return self._tools_cache
    
    def execute_tool(self, nome_ferramenta, argumentos):
        """Executa uma ferramenta específica com logs melhorados"""
        if nome_ferramenta not in self.functions:
            return {"status": "erro", "mensagem": f"Ferramenta '{nome_ferramenta}' não encontrada"}
        
        try:
            if nome_ferramenta == "search_web_comprehensive":
                query = argumentos.get('query', '')
                print(f" Executando busca: '{query}'")
            elif nome_ferramenta == "salvar_dados":
                chave = argumentos.get('chave', '')
                print(f"Salvando dado: '{chave}'")
            elif nome_ferramenta == "buscar_dados":
                chave = argumentos.get('chave', 'todos')
                print(f"Buscando dado: '{chave}'")
            else:
                print(f" Executando: {nome_ferramenta}")
            
            resultado = self.functions[nome_ferramenta](**argumentos)
            
            if resultado.get('status') == 'sucesso':
                print(f" {nome_ferramenta}: Sucesso")
            else:
                print(f" {nome_ferramenta}: {resultado.get('mensagem', 'Erro')}")
            
            return resultado
            
        except Exception as e:
            print(f" {nome_ferramenta}: Erro - {str(e)}")
            return {"status": "erro", "mensagem": f"Erro na execução: {str(e)}"}

tools_manager = ToolsManager()