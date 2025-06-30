# Visão Geral do Projeto

Este projeto é uma aplicação web construída com Flask. Ele é projetado com foco em segurança e modularidade.

## Tecnologias Principais

*   **Backend:** Python com Flask
*   **Segurança:**
    *   `Flask-Talisman` para headers de segurança.
    *   `Flask-Limiter` para limitação de taxa de requisições.
    *   `Flask-WTF` para proteção contra CSRF.
    *   `Flask-Cors` para gerenciamento de Cross-Origin Resource Sharing.

## Estrutura do Projeto

O código é organizado da seguinte forma:

*   `app.py`: Ponto de entrada da aplicação. Configura o app Flask, extensões de segurança e registra os blueprints.
*   `config.py`: Contém as configurações da aplicação (chaves secretas, configurações de debug, etc.).
*   `routes/`: Contém os blueprints do Flask para as diferentes partes da aplicação (ex: `main_routes.py`, `auth_routes.py`).
*   `models/`: Contém a lógica de negócio e interação com dados (ex: `cache_manager.py`, `session_manager.py`).
*   `templates/`: Contém os templates HTML para o frontend.
*   `static/`: Contém os arquivos estáticos (CSS, JavaScript, imagens).
*   `middleware/`: Contém os middlewares da aplicação.

## Como Executar

Para iniciar o servidor de desenvolvimento, execute o seguinte comando:

```bash
python app.py
```

O servidor estará disponível em `http://<HOST>:<PORT>`, conforme definido em `config.py`.

## Convenções

*   As rotas são definidas usando Blueprints do Flask.
*   A lógica de negócio é separada da lógica de roteamento.
*   As configurações são centralizadas no arquivo `config.py`.

## Atualizações Recentes

### 27 de Junho de 2025

*   **Correção de CORS:** Ajustada a configuração do `Flask-Cors` em `app.py` para permitir requisições de todas as origens (`origins='*'`). Isso resolveu os problemas de "Cross-Origin Resource Sharing" que bloqueavam as requisições do frontend.
*   **Remoção de Headers CORS Duplicados:** Removidos headers CORS redundantes do `@app.after_request` em `app.py`, pois o `Flask-Cors` já gerencia essas configurações.
*   **Simplificação da Chave Secreta:** Simplificada a atribuição da `SECRET_KEY` em `app.py` para maior clareza.
*   **Correção de Importação:** Corrigido um `ImportError` em `models/chat_manager.py` removendo a importação incorreta de `PLAN_LIMITS` do módulo `flask`. `PLAN_LIMITS` agora é importado exclusivamente de `config.py`.
*   **Remoção de Caracteres Unicode:** Removidos caracteres Unicode (emojis) de strings de impressão (`print`) em `app.py` e `models/chat_manager.py` para evitar `UnicodeEncodeError` em ambientes de console que não suportam UTF-8.

### 27 de Junho de 2025 - Problema Atual: Erro 400 (Bad Request) no /chat-stream devido a CSRF

**Problema:** Após as correções iniciais, o endpoint `/chat-stream` continua retornando um erro HTTP 400 (Bad Request). A análise dos logs e do comportamento indica que o problema está relacionado à validação do token CSRF (Cross-Site Request Forgery). O frontend (`script.js`) está enviando um token `null` ou inválido, fazendo com que o backend (Flask-WTF) rejeite a requisição.

**Causa Raiz Suspeita:** O `csrfToken` no frontend (`script.js`) está se tornando `null` antes de ser enviado na requisição `sendMessageToServer`, mesmo após ser carregado inicialmente da meta tag HTML. Isso pode ser devido a problemas de escopo de variável, re-inicialização indevida ou ordem de execução das funções no JavaScript.

**Passos de Depuração Atuais:**

1.  **Reativar CSRF para `/chat-stream`:** O decorador `@csrf.exempt` foi removido da rota `/chat-stream` em `routes/main_routes.py` para reativar a proteção CSRF.
2.  **Adicionar Log de CSRF no Frontend:** Um `console.log` foi adicionado na função `sendMessageToServer` em `titan_frontend/static/script.js` para verificar o valor do `csrfToken` antes de cada requisição.
3.  **Investigar `csrfToken` `null`:** O foco atual é entender por que o `csrfToken` está `null` no frontend no momento da requisição, apesar de ser carregado na inicialização. Isso envolve verificar o escopo da variável `csrfToken` e a ordem de execução das funções JavaScript.
