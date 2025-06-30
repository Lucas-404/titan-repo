# web_search_fixed.py
import requests
import json
import re
from urllib.parse import quote
import time
from html import unescape

def clean_text(text):
    """Limpa e formata texto de forma eficiente"""
    if not text:
        return ""
    
    # Remover HTML e entidades
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    
    # Limpar caracteres especiais
    text = re.sub(r'[^\w\s\.,!?()-áéíóúàèìòùâêîôûãõçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limitar tamanho
    if len(text) > 300:
        sentences = text[:300].split('.')
        if len(sentences) > 1:
            text = '.'.join(sentences[:-1]) + '.'
        else:
            text = text[:300] + "..."
    
    return text

def search_duckduckgo_working(query):
    """✅ DuckDuckGo usando biblioteca que FUNCIONA"""
    try:
        print(f"🦆 DuckDuckGo (biblioteca): '{query}'")
        
        # Tentar importar a biblioteca
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {
                "status": "erro", 
                "mensagem": "Biblioteca duckduckgo-search não instalada. Execute: pip install duckduckgo-search"
            }
        
        # Fazer a busca
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=5, safesearch='moderate'))
        
        for item in search_results:
            titulo = clean_text(item.get('title', ''))
            conteudo = clean_text(item.get('body', ''))
            url = item.get('href', '')
            
            if titulo and conteudo:
                results.append({
                    'titulo': titulo,
                    'conteudo': conteudo,
                    'fonte': 'DuckDuckGo',
                    'url': url,
                    'tipo': 'busca_web',
                    'relevancia': 'alta'
                })
        
        if results:
            print(f"✅ DuckDuckGo: {len(results)} resultados")
            return {"status": "sucesso", "resultados": results}
        else:
            return {"status": "erro", "mensagem": "Sem resultados no DuckDuckGo"}
            
    except Exception as e:
        print(f"❌ DuckDuckGo: {str(e)}")
        return {"status": "erro", "mensagem": f"Erro DuckDuckGo: {str(e)}"}

def search_wikipedia_working(query):
    """✅ Wikipedia API - 100% funcional e confiável"""
    try:
        print(f"📚 Wikipedia: '{query}'")
        
        # API da Wikimedia (oficial e gratuita)
        url = "https://api.wikimedia.org/core/v1/wikipedia/pt/search/page"
        params = {
            'q': query,
            'limit': 5
        }
        headers = {
            'User-Agent': 'TitanBot/1.0 (contato@exemplo.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        results = []
        for page in data.get('pages', []):
            titulo = clean_text(page.get('title', ''))
            descricao = page.get('description') or page.get('excerpt', 'Artigo da Wikipedia')
            conteudo = clean_text(descricao)
            key = page.get('key', '')
            
            if titulo:
                results.append({
                    'titulo': titulo,
                    'conteudo': conteudo,
                    'fonte': 'Wikipedia',
                    'url': f"https://pt.wikipedia.org/wiki/{key}",
                    'tipo': 'conhecimento',
                    'relevancia': 'alta'
                })
        
        # Tentar em inglês se não achou em português
        if not results:
            print("🔄 Tentando Wikipedia em inglês...")
            url = "https://api.wikimedia.org/core/v1/wikipedia/en/search/page"
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            for page in data.get('pages', []):
                titulo = clean_text(page.get('title', ''))
                descricao = page.get('description') or page.get('excerpt', 'Wikipedia article')
                conteudo = clean_text(descricao)
                key = page.get('key', '')
                
                if titulo:
                    results.append({
                        'titulo': titulo,
                        'conteudo': conteudo,
                        'fonte': 'Wikipedia (EN)',
                        'url': f"https://en.wikipedia.org/wiki/{key}",
                        'tipo': 'conhecimento',
                        'relevancia': 'alta'
                    })
        
        if results:
            print(f"✅ Wikipedia: {len(results)} resultados")
            return {"status": "sucesso", "resultados": results}
        else:
            return {"status": "erro", "mensagem": "Sem resultados na Wikipedia"}
            
    except Exception as e:
        print(f"❌ Wikipedia: {str(e)}")
        return {"status": "erro", "mensagem": f"Erro Wikipedia: {str(e)}"}

def search_web_comprehensive(query):
    """🌐 BUSCA ROBUSTA - Combinando fontes que REALMENTE funcionam"""
    try:
        print(f"\n🔍 BUSCA INICIADA: '{query}'")
        print("=" * 60)
        
        todos_resultados = []
        fontes_usadas = []
        fontes_com_erro = []
        
        # === ESTRATÉGIA: Fontes que funcionam ===
        
        # 1. DuckDuckGo via biblioteca (melhor opção)
        try:
            ddg_result = search_duckduckgo_working(query)
            if ddg_result['status'] == 'sucesso':
                todos_resultados.extend(ddg_result['resultados'])
                fontes_usadas.append('DuckDuckGo')
            else:
                fontes_com_erro.append("DuckDuckGo: " + ddg_result.get('mensagem', 'Falha'))
        except Exception as e:
            fontes_com_erro.append(f"DuckDuckGo: {str(e)}")
        
        # 2. Wikipedia (sempre funciona)
        try:
            wiki_result = search_wikipedia_working(query)
            if wiki_result['status'] == 'sucesso':
                todos_resultados.extend(wiki_result['resultados'])
                fontes_usadas.append('Wikipedia')
            else:
                fontes_com_erro.append("Wikipedia: " + wiki_result.get('mensagem', 'Falha'))
        except Exception as e:
            fontes_com_erro.append(f"Wikipedia: {str(e)}")
        
        # === PROCESSAR RESULTADOS ===
        
        if todos_resultados:
            # Remover duplicatas
            resultados_limpos = []
            titulos_vistos = set()
            
            for resultado in todos_resultados:
                titulo = resultado.get('titulo', '').lower().strip()
                if titulo and titulo not in titulos_vistos and len(titulo) > 5:
                    titulos_vistos.add(titulo)
                    resultados_limpos.append(resultado)
                    
                    # Limitar a 6 resultados
                    if len(resultados_limpos) >= 6:
                        break
            
            print(f"\n✅ BUSCA CONCLUÍDA COM SUCESSO:")
            print(f"   📊 {len(resultados_limpos)} resultados úteis")
            print(f"   🎯 {len(fontes_usadas)} fontes: {', '.join(fontes_usadas)}")
            print("=" * 60)
            
            return {
                "status": "sucesso",
                "query": query,
                "total_resultados": len(resultados_limpos),
                "fontes_usadas": fontes_usadas,
                "resultados": resultados_limpos,
                "resumo": f"Encontrei {len(resultados_limpos)} resultados de {len(fontes_usadas)} fontes confiáveis"
            }
        else:
            print(f"\n❌ BUSCA SEM RESULTADOS:")
            print(f"   🔍 Query: {query}")
            print(f"   📊 Fontes com erro: {fontes_com_erro}")
            print("=" * 60)
            
            return {
                "status": "erro",
                "query": query,
                "mensagem": f"Não consegui encontrar resultados para '{query}'",
                "sugestao": "Tente usar termos mais específicos ou diferentes",
                "fontes_com_erro": fontes_com_erro
            }
        
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO na busca: {str(e)}")
        print("=" * 60)
        
        return {
            "status": "erro",
            "query": query,
            "mensagem": f"Erro crítico: {str(e)}"
        }

def format_search_results(search_data):
    """📋 Formata resultados para exibição com avisos de prioridade"""
    if search_data['status'] != 'sucesso':
        error_msg = f"❌ **Busca falhou:** {search_data.get('mensagem', 'Erro desconhecido')}"
        if search_data.get('sugestao'):
            error_msg += f"\n\n💡 **Sugestão:** {search_data['sugestao']}"
        return error_msg
    
    resultados = search_data.get('resultados', [])
    if not resultados:
        return "🔍 Nenhum resultado encontrado"
    
    # ✅ NOVO: Cabeçalho com aviso de prioridade
    formatted = f"🌐 **INFORMAÇÕES ATUAIS DA INTERNET** (priorizar sobre conhecimento interno)\n"
    formatted += f"📊 **Busca:** {search_data['query']}\n"
    formatted += f"✅ **{search_data['resumo']}**\n\n"
    
    # Aviso especial para questões temporais
    query_lower = search_data['query'].lower()
    if any(word in query_lower for word in ['primeiro', 'último', 'quando', 'data', 'ano', 'antes', 'depois', 'após']):
        formatted += "⚠️ **ATENÇÃO CRONOLÓGICA:** Verifique cuidadosamente datas e sequências temporais!\n\n"
    
    # Resultados organizados
    emoji_map = {
        'conhecimento': '📚', 'busca_web': '🔍', 'tech_news': '📰', 'discussao': '💬'
    }
    
    for i, resultado in enumerate(resultados, 1):
        emoji = emoji_map.get(resultado.get('tipo', ''), '📄')
        
        formatted += f"**{i}. {emoji} {resultado.get('titulo', 'Sem título')}**\n"
        formatted += f"*Fonte: {resultado.get('fonte', 'Desconhecida')}*\n"
        formatted += f"{resultado.get('conteudo', 'Sem descrição')}\n"
        
        if resultado.get('url'):
            formatted += f"🔗 {resultado['url']}\n"
        
        formatted += "\n"
    
    # ✅ NOVO: Rodapé com lembrete
    formatted += "🎯 **LEMBRETE:** Use SEMPRE estas informações atuais da web, não conhecimento pré-treinado! Use os dados pegos para formular a sua resposta!\n"
    
    return formatted

# Função para testar
def test_search():
    """Função para testar a busca"""
    query = "último álbum da Sabrina Carpenter"
    result = search_web_comprehensive(query)
    print(format_search_results(result))

if __name__ == "__main__":
    test_search()