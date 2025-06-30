// =================== VARIÁVEIS GLOBAIS ===================
const mainInput = document.getElementById('mainInput');
const sendBtn = document.getElementById('sendBtn');
const welcomeContainer = document.querySelector('.welcome-container');
const chatContainer = document.getElementById('chatContainer');
const thinking = document.getElementById('thinking');
const thinkingText = document.getElementById('thinkingText');

let currentThinkingMode = false;
let isInChatMode = false;
let systemStatus = 'connecting';
let settingsTabVisible = false;

// Variáveis de sessão
let sessionId = null;
let conversationHistory = [];
let isNewSession = true;

// Variáveis de controle
let currentRequest = null; // AbortController para cancelar requests
let userMessageCount = 0; // Contador de mensagens do usuário
let feedbackShown = false; // Se já mostrou o feedback
let isGenerating = false; // Estado de geração ativa

// CSRF Token
let csrfToken = null;

// ===================  FUNÇÕES DE SEGURANÇA ===================
function escapeHtml(text) {
    /**
     *  ESCAPE ULTRA SEGURO - Previne XSS
     */
    if (!text || typeof text !== 'string') {
        return '';
    }

    // ADICIONAR O CÓDIGO QUE FALTAVA:
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function sanitizeAttribute(attr) {
    /**
     *  SANITIZAÇÃO DE ATRIBUTOS
     */
    if (!attr || typeof attr !== 'string') {
        return '';
    }

    // Escapar e limitar tamanho
    return escapeHtml(attr.substring(0, 200));
}

function validateInput(input) {
    /**
     *  VALIDAÇÃO DE INPUT DO USUÁRIO
     */
    if (!input || typeof input !== 'string') {
        return false;
    }

    // Limites de segurança
    if (input.length > 2000) {
        showToast('Mensagem muito longa (máximo 2000 caracteres)', 'error');
        return false;
    }

    // Detectar tentativas de injection
    const dangerousPatterns = [
        /<script/i,
        /javascript:/i,
        /data:text\/html/i,
        /vbscript:/i,
        /on\w+\s*=/i,
        /<iframe/i,
        /<object/i,
        /<embed/i
    ];

    for (const pattern of dangerousPatterns) {
        if (pattern.test(input)) {
            return false;
        }
    }

    return true;
}

function formatMessage(content) {
    /**
     *  FORMATAÇÃO SEGURA DE MENSAGEM
     */
    if (!content || typeof content !== 'string') {
        return '';
    }

    // 1. PRIMEIRO: Escapar TUDO
    let safeContent = escapeHtml(content);

    // 2. DEPOIS: Aplicar formatação CONTROLADA
    // Bold (**texto**)
    safeContent = safeContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic (*texto*)
    safeContent = safeContent.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code (`código`)
    safeContent = safeContent.replace(/`(.*?)`/g, '<code>$1</code>');

    // Line breaks
    safeContent = safeContent.replace(/\n/g, '<br>');

    return safeContent;
}

// ===================  CSRF TOKEN MANAGEMENT ===================
function initializeCsrfToken() {
    /**
     *  Inicializar CSRF token
     */
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        csrfToken = csrfMeta.getAttribute('content');
        console.log(' CSRF token carregado');
    } else {
        console.log('CSRF token não encontrado - continuando sem');
    }
}

function getHeaders() {
    /**
     *  Headers seguros para requests
     */
    const headers = {
        'Content-Type': 'application/json'
    };

    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    return headers;
}

// =================== FUNÇÃO UTILITÁRIA CONSOLIDADA ===================
function addThinkingCommand(message) {
    const finalMessage = message.trim();
    const hasManualCommand = finalMessage.includes('/think') || finalMessage.includes('/no_think');

    if (!hasManualCommand) {
        if (currentThinkingMode) {
            console.log(' [COMANDO] Adicionado /think automaticamente');
            return finalMessage + ' /think';
        } else {
            console.log('🔴 [COMANDO] Adicionado /no_think automaticamente');
            return finalMessage + ' /no_think';
        }
    } else {
        console.log('[COMANDO] Comando manual detectado, mantendo original');
    }

    return finalMessage;
}

// =================== INICIALIZAÇÃO ===================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Titan Chat - Sistema carregado!');

    // INICIALIZAR CSRF TOKEN PRIMEIRO
    initializeCsrfToken();

    clearCurrentSession();
    initializeCleanWelcome();
    createParticles();
    setupEventListeners();
    initializeOriginalSystem();
    initializeThinkingMode();
    setupThinkingModeClickOutside();
    initializeFeedbackSystem();

    if (mainInput) {
        mainInput.focus();
    }

    console.log('✨ Sistema inicializado!');
});

// =================== WELCOME LIMPO ===================
function initializeCleanWelcome() {
    isInChatMode = false;

    if (welcomeContainer) {
        welcomeContainer.style.display = 'flex';
        welcomeContainer.style.opacity = '1';
        welcomeContainer.classList.remove('hidden');
    }

    if (chatContainer) {
        chatContainer.style.display = 'none';
        chatContainer.style.opacity = '0';
        chatContainer.classList.remove('active');
    }

    console.log('Welcome inicializado');
}

// =================== SISTEMA ORIGINAL ===================
async function initializeOriginalSystem() {
    try {
        await updateSystemStatus();
        console.log('🔗 Sistema integrado');
    } catch (error) {
        console.warn('Erro ao inicializar sistema:', error);
    }
}

async function updateSystemStatus() {
    try {
        const response = await fetchAPI('/status');
        const data = await response.json();
        const { usuarios_ativos, maximo_usuarios, disponivel } = data;

        const statusIndicator = document.querySelector('.status-indicator span');
        if (statusIndicator) {
            if (disponivel) {
                statusIndicator.textContent = `Online • ${usuarios_ativos}/${maximo_usuarios}`;
                systemStatus = 'online';
            } else {
                statusIndicator.textContent = `Ocupado • ${usuarios_ativos}/${maximo_usuarios}`;
                systemStatus = 'busy';
            }
        }
    } catch (error) {
        systemStatus = 'offline';
        const statusIndicator = document.querySelector('.status-indicator span');
        if (statusIndicator) {
            statusIndicator.textContent = 'Offline';
        }
    }
}

// ===== FUNÇÃO FALTANTE =====
function initializeThinkingMode() {
    // Inicializar thinking mode
    currentThinkingMode = false;

    // Aplicar tema padrão
    applyTheme(false);

    // Atualizar toggles
    updateThinkingToggleVisual();

    console.log('🧠 Thinking mode inicializado');
}

function applyTheme(thinkingEnabled) {
    if (thinkingEnabled) {
        document.body.classList.add('thinking-theme');
    } else {
        document.body.classList.remove('thinking-theme');
    }
}

function updateThinkingToggleVisual() {
    const toggle = document.getElementById('titanToggle');
    if (toggle) {
        if (currentThinkingMode) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
    }

    updateDropdownThinkingToggle();
    updateDropdownThinkingToggleChat();
}

// =================== PARTÍCULAS ===================
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    if (!particlesContainer) return;

    particlesContainer.innerHTML = '';
    const particleCount = window.innerWidth < 768 ? 5 : 10;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';

        // LIMITAR SPAWN HORIZONTAL (evitar bordas)
        particle.style.left = (Math.random() * 80 + 10) + '%'; // Entre 10% e 90%

        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (Math.random() * 10 + 10) + 's';

        const size = Math.random() * 2 + 1;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.opacity = Math.random() * 0.3 + 0.1;

        particlesContainer.appendChild(particle);
    }
}

// =================== SISTEMA DE STOP/CANCEL ===================
function updateSendButtonState(generating) {
    isGenerating = generating;
    const sendBtn = document.getElementById('sendBtn');
    const chatSendBtn = document.getElementById('chatSendBtn');

    if (generating) {
        // Modo STOP - botão vermelho com ícone de parar
        if (sendBtn) {
            sendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
            `;
            sendBtn.classList.add('stop-mode');
            sendBtn.title = 'Parar geração (ESC)';
        }

        if (chatSendBtn) {
            chatSendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
            `;
            chatSendBtn.classList.add('stop-mode');
            chatSendBtn.title = 'Parar geração (ESC)';
        }

        console.log('🔴 Botões mudaram para modo STOP');
    } else {
        // Modo SEND - botão normal com ícone de enviar
        if (sendBtn) {
            sendBtn.innerHTML = `
                <svg viewBox="0 0 24 24">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
            `;
            sendBtn.classList.remove('stop-mode');
            sendBtn.title = 'Enviar mensagem (Enter)';
        }

        if (chatSendBtn) {
            chatSendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
            `;
            chatSendBtn.classList.remove('stop-mode');
            chatSendBtn.title = 'Enviar mensagem (Enter)';
        }

        console.log(' Botões voltaram para modo SEND');
    }
}

function cancelCurrentRequest() {
    if (currentRequest) {
        console.log('🛑 Cancelando request...');

        // CANCELAR NO FRONTEND PRIMEIRO
        try {
            currentRequest.abort();
        } catch (abortError) {
            console.warn('Erro ao abortar:', abortError);
        }

        currentRequest = null;

        // INFORMAR O BACKEND (sem esperar resposta)
        fetchAPI('/cancel-request', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ action: 'cancel' })
        }).catch(error => {
            // Ignorar erros do cancelamento no backend
            console.warn('Backend cancel falhou:', error);
        });

        // LIMPAR INTERFACE
        if (thinking) {
            thinking.style.display = 'none';
        }

        updateSendButtonState(false);

        // MENSAGEM DE CANCELAMENTO
        addMessageToChat('Geração cancelada', false, {
            modo: 'Sistema',
            tempo_resposta: '0ms'
        });

        console.log('Request cancelado com sucesso');
        return true;
    }

    console.log('Nenhum request ativo para cancelar');
    return false;
}

// =================== EVENT LISTENERS ===================
function setupEventListeners() {
    if (mainInput) {
        mainInput.addEventListener('keydown', handleMainInputKeydown);
        mainInput.addEventListener('focus', handleInputFocus);
        mainInput.addEventListener('blur', handleInputBlur);
        mainInput.addEventListener('input', handleInputResize);
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', handleSendMessage);
    }

    const toggleBtn = document.getElementById('titanToggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleThinkingClean);
    }

    setupChatInputListeners();
    window.addEventListener('resize', handleWindowResize);
    setInterval(updateSystemStatus, 180000);
}

function setupChatInputListeners() {
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');

    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });

        chatInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    }

    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', sendChatMessage);
    }
}

function handleMainInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
}

function handleInputFocus() {
    const container = mainInput.closest('.main-input-container');
    if (container) {
        container.style.borderColor = '#10b981';
        container.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.15), 0 15px 50px rgba(0, 0, 0, 0.4)';
    }
}

function handleInputBlur() {
    const container = mainInput.closest('.main-input-container');
    if (container) {
        container.style.borderColor = '';
        container.style.boxShadow = '';
    }
}

function handleInputResize() {
    mainInput.style.height = 'auto';
    mainInput.style.height = mainInput.scrollHeight + 'px';
}

function handleWindowResize() {
    setTimeout(createParticles, 100);
}

// ===================  STREAMING REAL ===================
async function handleSendMessage() {
    // Se está gerando, cancelar em vez de enviar
    if (isGenerating && currentRequest) {
        cancelCurrentRequest();
        return;
    }

    const message = mainInput?.value?.trim();
    if (!message) return;

    console.log('📤 Enviando mensagem:', message);

    // PROCESSAR COMANDO ANTES DE ENVIAR
    const finalMessage = addThinkingCommand(message);

    if (!isInChatMode) {
        transitionToChat();
        setTimeout(() => {
            addMessageToChat(message, true); // Mostrar original
            sendMessageToServer(finalMessage); // Enviar processada
        }, 350);
    } else {
        addMessageToChat(message, true); // Mostrar original
        await sendMessageToServer(finalMessage); // Enviar processada
    }

    mainInput.value = '';
    mainInput.style.height = 'auto';
}

// Modificar a função sendMessageToServer:
async function sendMessageToServer(message) {
    if (!validateInput(message)) {
        return;
    }

    if (!sessionId) {
        startNewSession();
    }

    const finalMessage = addThinkingCommand(message);
    currentRequest = new AbortController();
    updateSendButtonState(true);

    const streamContainer = createStreamingContainer();

    try {
        const response = await fetchAPI('/chat-stream', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                mensagem: finalMessage,
                thinking_mode: currentThinkingMode
            }),
            signal: currentRequest.signal
        });

        // ✅ VERIFICAR SE É ERRO DE LIMITE
        if (response.status === 429) {
            const errorData = await response.json();

            if (errorData.action_required === 'create_account') {
                // Usuário anônimo atingiu limite
                showCreateAccountModal(errorData);
                streamContainer.remove(); // Remover container vazio
                return;
            } else {
                // Usuário autenticado atingiu limite
                showError(errorData.error);
                streamContainer.remove();
                return;
            }
        }

        if (response.status === 402) {
            // Feature restrita
            const errorData = await response.json();
            showFeatureRestrictedModal(errorData);
            streamContainer.remove();
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // ✅ CONTINUAR COM STREAMING NORMAL
        await processStreamResponse(response, streamContainer);

    } catch (error) {
        if (error.name !== 'AbortError') {
            showError('Falha na comunicação com o servidor');
        }
    } finally {
        currentRequest = null;
        updateSendButtonState(false);
    }
}

// ✅ NOVA FUNÇÃO: Modal de criar conta
function showCreateAccountModal(limitData) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🎯 Limite de Mensagens Atingido!</h3>
            <p>Você usou <strong>${limitData.messages_used}/${limitData.limit}</strong> mensagens gratuitas hoje.</p>
            <p>Crie uma conta <strong>gratuita</strong> para continuar conversando com o Titan!</p>
            
            <div class="modal-benefits">
                <h4>✨ Benefícios da conta gratuita:</h4>
                <ul>
                    <li>✅ Mais mensagens por dia</li>
                    <li>✅ Histórico de conversas</li>
                    <li>✅ Memória personalizada</li>
                </ul>
            </div>
            
            <div class="modal-actions">
                <button onclick="openRegisterForm()" class="btn btn-primary">
                    Criar Conta Grátis
                </button>
                <button onclick="closeCreateAccountModal()" class="btn btn-secondary">
                    Talvez Depois
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function closeCreateAccountModal() {
    const modal = document.querySelector('.modal');
    if (modal) modal.remove();
}

function openRegisterForm() {
    closeCreateAccountModal();
    // Aqui você pode abrir um formulário de registro
    // ou redirecionar para uma página de cadastro
    console.log('Abrir formulário de registro');
}

// ✅ NOVA FUNÇÃO: Modal de feature restrita
function showFeatureRestrictedModal(errorData) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🚀 Feature Premium</h3>
            <p>${errorData.error}</p>
            
            ${errorData.action_required === 'create_account' ? `
                <button onclick="openRegisterForm()" class="btn btn-primary">
                    Criar Conta Grátis
                </button>
            ` : `
                <button onclick="showUpgradeModal()" class="btn btn-primary">
                    Ver Planos Premium
                </button>
            `}
            
            <button onclick="closeFeatureModal()" class="btn btn-secondary">
                Fechar
            </button>
        </div>
    `;

    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function closeFeatureModal() {
    const modal = document.querySelector('.modal');
    if (modal) modal.remove();
}

async function sendChatMessage() {
    // Se está gerando, cancelar em vez de enviar
    if (isGenerating && currentRequest) {
        cancelCurrentRequest();
        return;
    }

    const chatInput = document.getElementById('chatInput');
    const message = chatInput?.value?.trim();
    if (!message) return;

    // PROCESSAR COMANDO ANTES DE ENVIAR
    const finalMessage = addThinkingCommand(message);

    console.log('📤 Enviando do chat:', finalMessage);

    addMessageToChat(message, true); // Mostrar original
    chatInput.value = '';
    chatInput.style.height = 'auto';
    await sendMessageToServer(finalMessage); // Enviar processada
}

async function streamWithFetchStream(message, container) {
    console.log('🎯 STREAM ULTRA SIMPLES para:', message);
    
    try {
        const response = await fetch('https://api.outzapp.com/chat-stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mensagem: message,
                thinking_mode: false
            })
        });

        console.log('📡 Status:', response.status);

        if (!response.ok) {
            throw new Error('Response não OK');
        }

        if (!response.body) {
            throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let finalText = '';

        // Container para mostrar texto
        const contentDiv = container.querySelector('.streaming-content');

        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                console.log('✅ DONE! Texto final:', finalText);
                break;
            }

            const chunk = decoder.decode(value);
            console.log('📦 Chunk recebido:', chunk.substring(0, 50));

            // Procurar por "data: " e extrair JSON
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const json = JSON.parse(line.slice(6));
                        if (json.type === 'content' && json.content) {
                            finalText += json.content;
                            
                            // MOSTRAR NA TELA IMEDIATAMENTE
                            if (contentDiv) {
                                contentDiv.textContent = finalText;
                            }
                        }
                    } catch (e) {
                        // Ignorar erros de JSON
                    }
                }
            }
        }

        return finalText;

    } catch (error) {
        console.error('❌ ERRO:', error);
        const contentDiv = container.querySelector('.streaming-content');
        if (contentDiv) {
            contentDiv.textContent = 'Erro: ' + error.message;
        }
        throw error;
    }
}

// FUNÇÃO PRINCIPAL: PROCESSAR THINKING EM TEMPO REAL
function processThinkingInRealTime(fullContent, container) {
    let insideThinking = false;
    let thinkingContent = '';
    let afterThinkingContent = '';
    let thinkingContainer = null;
    let thinkingScrollElement = null;

    // DETECTAR <think> E </think>
    const thinkStartIndex = fullContent.indexOf('<think>');
    const thinkEndIndex = fullContent.indexOf('</think>');

    if (thinkStartIndex !== -1) {
        // ENCONTROU <think> - CRIAR CONTAINER SE NECESSÁRIO
        if (currentThinkingMode && !container.querySelector('.thinking-container')) {
            thinkingContainer = createThinkingContainerLive(container);
            thinkingScrollElement = thinkingContainer?.querySelector('.thinking-scroll');
            console.log(' Container de thinking criado em tempo real');
        }

        if (thinkEndIndex !== -1) {
            // THINKING COMPLETO - EXTRAIR CONTEÚDO
            thinkingContent = fullContent.substring(thinkStartIndex + 7, thinkEndIndex);
            afterThinkingContent = fullContent.substring(thinkEndIndex + 8).trim();
            insideThinking = false;

            console.log('Thinking completo extraído:', thinkingContent.length, 'chars');
        } else {
            // THINKING EM PROGRESSO - EXTRAIR PARCIAL
            thinkingContent = fullContent.substring(thinkStartIndex + 7);
            afterThinkingContent = '';
            insideThinking = true;

            // console.log(' Thinking em progresso:', thinkingContent.length, 'chars');
        }

        // OBTER ELEMENTOS SE NÃO TIVER
        if (!thinkingContainer) {
            thinkingContainer = container.querySelector('.thinking-container');
        }
        if (!thinkingScrollElement) {
            thinkingScrollElement = thinkingContainer?.querySelector('.thinking-scroll');
        }

    } else {
        // SEM THINKING - CONTEÚDO NORMAL
        afterThinkingContent = fullContent;
        insideThinking = false;
    }

    return {
        insideThinking,
        thinkingContent,
        afterThinkingContent,
        thinkingContainer,
        thinkingScrollElement
    };
}

// CRIAR CONTAINER DE THINKING LIVE - TAMANHO FIXO
function createThinkingContainerLive(messageContainer) {
    const assistantDiv = messageContainer.querySelector('.assistant-message');
    if (!assistantDiv) return null;

    const thinkingHTML = `
        <div class="thinking-container live-thinking">
            <div class="thinking-header" onclick="toggleThinking(this)">
                <span class="thinking-icon"></span>
                <span class="thinking-summary">Pensando em tempo real...</span>
                <span class="thinking-toggle">▼</span>
            </div>
            <div class="thinking-content" style="max-height: 0; overflow: hidden; transition: max-height 0.3s ease;">
                <div class="thinking-scroll" style="height: 200px; overflow-y: auto; padding: 10px; font-size: 13px; line-height: 1.4; color: #e5e7eb; background: rgba(0,0,0,0.2); border-radius: 8px;"></div>
            </div>
        </div>
    `;

    assistantDiv.insertAdjacentHTML('afterbegin', thinkingHTML);
    const thinkingContainer = assistantDiv.querySelector('.thinking-container');

    console.log(' Container de thinking live criado (fechado, tamanho fixo)');
    return thinkingContainer;
}

// SCROLL INSTANTÂNEO
function scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// NOVA FUNÇÃO: Atualizar thinking em tempo real
function updateThinkingContent(thinkingContainer, content) {
    if (!thinkingContainer) return;

    const scroll = thinkingContainer.querySelector('.thinking-scroll');
    if (scroll) {
        scroll.textContent = content;

        // Auto-scroll para o final
        scroll.scrollTop = scroll.scrollHeight;
    }
}

// FUNÇÕES DE STREAMING REAL
function createStreamingContainer() {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message streaming-message';

    messageDiv.innerHTML = `
        <div class="assistant-message">
            <div class="message-content streaming-content"></div>
            <div class="streaming-cursor">|</div>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
}

function updateStreamingContent(container, content) {
    const contentDiv = container.querySelector('.streaming-content');
    if (contentDiv) {
        contentDiv.innerHTML = formatMessage(content);
    }
}

function finalizeStreamingMessage(container, content, thinking = null) {
    container.classList.remove('streaming-message');

    const cursor = container.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();

    const assistantDiv = container.querySelector('.assistant-message');
    if (!assistantDiv) return;

    // ADICIONAR THINKING SE PRESENTE
    if (thinking && thinking.trim() && currentThinkingMode) {
        assistantDiv.innerHTML = `
            <div class="thinking-container">
                <div class="thinking-header" onclick="toggleThinking(this)">
                    <span class="thinking-icon"></span>
                    <span class="thinking-summary">Processo de raciocínio</span>
                    <span class="thinking-toggle">▼</span>
                </div>
                <div class="thinking-content">
                    <div class="thinking-scroll">${escapeHtml(thinking)}</div>
                </div>
            </div>
            <div class="message-content">${formatMessage(content)}</div>
        `;
        console.log(' Thinking adicionado à mensagem!');
    } else {// Mensagem normal sem thinking
        const contentDiv = container.querySelector('.streaming-content');
        if (contentDiv) {
            contentDiv.innerHTML = formatMessage(content);
            contentDiv.classList.remove('streaming-content');
        }
    }

    // ADICIONAR BOTÕES DE AÇÃO AQUI
    setTimeout(() => {
        addMessageActions(container, content, false);
    }, 100);

    scrollToBottom();
}

// =================== TRANSIÇÃO PARA CHAT ===================
function transitionToChat() {
    console.log(' Transicionando para chat...');

    isInChatMode = true;

    if (welcomeContainer) {
        welcomeContainer.style.opacity = '0';
        welcomeContainer.style.transform = 'scale(0.95)';

        setTimeout(() => {
            welcomeContainer.style.display = 'none';
            welcomeContainer.classList.add('hidden');

            if (chatContainer) {
                chatContainer.style.display = 'flex';
                chatContainer.style.opacity = '0';
                chatContainer.classList.add('active');

                setupChatInterface();

                setTimeout(() => {
                    chatContainer.style.opacity = '1';
                }, 50);
            }
        }, 300);
    }
}

function setupChatInterface() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer && messagesContainer.children.length === 0) {
        messagesContainer.innerHTML = '';
    }

    // Mostrar chat input
    const chatInputArea = document.getElementById('chatInputArea');
    if (chatInputArea) {
        chatInputArea.style.display = 'block';

        // Focar no input
        setTimeout(() => {
            const chatInput = document.getElementById('chatInput');
            if (chatInput) chatInput.focus();
        }, 200);
    }

    console.log('🎮 Interface do chat configurada');
}

// =================== VOLTAR PARA WELCOME ===================
function backToWelcome() {
    console.log(' Voltando para Welcome...');

    // Cancelar qualquer request ativo antes de sair
    if (currentRequest) {
        cancelCurrentRequest();
    }

    isInChatMode = false;

    if (chatContainer) {
        chatContainer.style.opacity = '0';
        chatContainer.classList.remove('active');
    }

    setTimeout(() => {
        if (chatContainer) {
            chatContainer.style.display = 'none';
        }

        // Esconder chat input
        const chatInputArea = document.getElementById('chatInputArea');
        if (chatInputArea) {
            chatInputArea.style.display = 'none';
        }

        if (welcomeContainer) {
            welcomeContainer.style.display = 'flex';
            welcomeContainer.style.opacity = '0';
            welcomeContainer.style.transform = 'scale(0.95)';
            welcomeContainer.classList.remove('hidden');

            setTimeout(() => {
                welcomeContainer.style.opacity = '1';
                welcomeContainer.style.transform = 'scale(1)';

                if (mainInput) {
                    mainInput.value = '';
                    mainInput.focus();
                }
            }, 50);
        }
    }, 300);
}

// ===================  GERENCIAMENTO SEGURO DE MENSAGENS ===================
function addMessageToChat(content, isUser, systemInfo = null) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) {
        console.error('Elemento #chatMessages não encontrado no DOM!');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    if (isUser) messageDiv.classList.add('user');

    if (isUser) {
        console.log('Adicionando mensagem do usuário:', content);

        //  CONTEÚDO DO USUÁRIO - ESCAPE TOTAL
        const safeContent = escapeHtml(content);

        messageDiv.innerHTML = `
           <div class="user-message">
               <div class="message-content">${safeContent}</div>
           </div>
       `;
    } else {
        //  MENSAGEM DO ASSISTENTE - FORMATAÇÃO SEGURA
        const mode = systemInfo?.modo || (currentThinkingMode ? 'Raciocínio' : 'Direto');
        const tempoResposta = systemInfo?.tempo_resposta || '';
        const temPensamento = systemInfo?.tem_pensamento || false;
        const pensamento = systemInfo?.pensamento || '';

        let messageContent = '';

        if (currentThinkingMode && temPensamento && pensamento) {
            //  ESCAPE PENSAMENTO TAMBÉM
            const safePensamento = escapeHtml(pensamento);
            const safeContent = formatMessage(content);
            const safeMode = sanitizeAttribute(mode);
            const safeTempoResposta = escapeHtml(tempoResposta);

            messageContent = `
               <div class="assistant-message message-block" data-mode="${safeMode}">
                   <div class="thinking-container">
                       <div class="thinking-header" onclick="toggleThinking(this)">
                           <span class="thinking-icon"></span>
                           <span class="thinking-summary">Pensou por ${safeTempoResposta}</span>
                           <span class="thinking-toggle">▼</span>
                       </div>
                       <div class="thinking-content">
                           <div class="thinking-scroll">${safePensamento}</div>
                       </div>
                   </div>
                   <div class="message-content">${safeContent}</div>
               </div>
           `;
        } else {
            //  RESPOSTA SIMPLES - TAMBÉM SEGURA
            const safeContent = formatMessage(content);
            const safeMode = sanitizeAttribute(mode);
            const safeTempoResposta = escapeHtml(tempoResposta);

            messageContent = `
               <div class="assistant-message" data-mode="${safeMode}">
                   <div class="message-content">${safeContent}</div>
                   ${tempoResposta ? `<div class="response-time">${safeTempoResposta}</div>` : ''}
               </div>
           `;
        }

        messageDiv.innerHTML = messageContent;
    }

    if (!isUser) {
        messageContainer.appendChild(messageDiv)
        setTimeout(() => {
            addMessageActions(messageDive, content, false);
        }, 50)
    } else {
        messagesContainer.appendChild(messageDiv);
    }
    scrollToBottom();
}

function toggleThinking(header) {
    const container = header.parentElement;
    const content = container.querySelector('.thinking-content');
    const toggle = container.querySelector('.thinking-toggle');

    if (!content || !toggle) {
        console.error('Elementos thinking-content ou thinking-toggle não encontrados!');
        return;
    }

    if (container.classList.contains('expanded')) {
        // FECHAR - Container volta para 0
        container.classList.remove('expanded');
        content.style.maxHeight = '0';
        toggle.textContent = '▼';
        console.log(' Thinking fechado');
    } else {
        // ABRIR - Container vai para tamanho fixo (220px = 200px scroll + padding)
        container.classList.add('expanded');
        content.style.maxHeight = '220px'; // Tamanho fixo
        toggle.textContent = '▲';
        console.log(' Thinking aberto');
    }
    scrollToBottom();
}

function showError(message) {
    const safeMessage = escapeHtml(message);
    addMessageToChat(`Erro: ${safeMessage}`, false);
    console.error('Erro no chat:', message);
}

function showQueueMessage(queueInfo) {
    const safeMessage = ` Titan está ocupado. Você é o ${escapeHtml(queueInfo.posicao)}º na fila. ` +
        `Tempo estimado: ${escapeHtml(queueInfo.tempo_estimado_str)}`;
    addMessageToChat(safeMessage, false);

    setTimeout(() => {
        const chatInput = document.getElementById('chatInput');
        const lastMessage = chatInput?.value?.trim();
        if (lastMessage) {
            sendMessageToServer(lastMessage);
        }
    }, queueInfo.tempo_estimado * 1000);
}

// =================== ABA DE FERRAMENTAS ===================
function toggleSettingsTab() {
    const settingsTab = document.getElementById('settingsTab');
    if (!settingsTab) return;

    settingsTabVisible = !settingsTabVisible;

    if (settingsTabVisible) {
        settingsTab.classList.add('active');
        updateSettingsButtonStates();
    } else {
        settingsTab.classList.remove('active');
        updateSettingsButtonStates();
    }
}

function updateSettingsButtonStates() {
    const settingsBtns = document.querySelectorAll('.settings-btn');
    settingsBtns.forEach(btn => {
        if (settingsTabVisible) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// =================== THINKING MODE ===================
async function checkUserPlanAndUpdateUI() {
    try {
        const response = await fetchAPI('/api/user-status');
        const data = await response.json();

        if (data.logged_in) {
            updateThinkingModeAvailability(data.plan);
            updateUsageDisplay(data.usage, data.plan);
            updateUserInfo(data.user, data.plan);
        } else if (data.anonymous) {
            // ✅ USUÁRIO ANÔNIMO - PARAR LOOP AQUI!
            console.log('✅ Usuário anônimo detectado - parando loop');
            updateAnonymousLimits(data.anonymous_limits);
            return; // ← IMPORTANTE: PARAR AQUI!
        } else {
            // SÓ inicializar se realmente necessário
            if (!sessionId) {
                await initializeUserSession();
            }
        }
    } catch (error) {
        console.error('Erro ao verificar plano:', error);
    }
}

async function initializeUserSession() {
    console.log('🔄 Inicializando sessão...');

    try {
        const response = await fetchAPI('/api/init-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('✅ Sessão inicializada:', data);

            // ✅ DEFINIR sessionId AQUI!
            if (data.session_id) {
                sessionId = data.session_id;
            }

            // ✅ NÃO CHAMAR checkUserPlanAndUpdateUI() NOVAMENTE!
            if (data.limits) {
                updateAnonymousLimits(data.limits);
            }

            // PARAR AQUI - NÃO FAZER MAIS LOOPS!

        }
    } catch (error) {
        console.error('Erro ao inicializar sessão:', error);
    }
}

function updateAnonymousLimits(limits) {
    console.log('📊 Limites anônimos:', limits);
    
    // Mostrar na interface os limites do usuário anônimo
    const limitDisplay = document.getElementById('anonymous-limit-display');
    if (limitDisplay) {
        limitDisplay.innerHTML = `
            <div class="anonymous-limits">
                <span>Mensagens restantes: ${limits.remaining}/${limits.limit}</span>
            </div>
        `;
    }
    
    // Atualizar thinking mode para usuários anônimos
    updateThinkingModeForAnonymous();
}


function updateThinkingModeForAnonymous() {
    // Usuários anônimos podem usar thinking mode
    const toggle = document.getElementById('titanToggle');
    if (toggle) {
        toggle.classList.remove('disabled');
    }
    
    const thinkingBtns = document.querySelectorAll('.dropdown-toggle');
    thinkingBtns.forEach(btn => {
        btn.classList.remove('disabled');
        btn.style.opacity = '1';
    });
}

// ✅ CORRIGIR setupKeyboardShortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
        // ESC para cancelar geração
        if (e.key === 'Escape') {
            if (isGenerating && currentRequest) {
                cancelCurrentRequest();
            }
        }

        // Ctrl/Cmd + N para nova conversa
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            startNewChat();
        }

        // Ctrl/Cmd + / para mostrar atalhos
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            showKeyboardShortcuts();
        }
    });

    console.log('⌨️ Atalhos de teclado configurados');
}

function updateThinkingModeAvailability(plan) {

    const toggle = document.getElementById('titanToggle');
    const thinkingBtns = document.querySelectorAll('.dropdown-toggle'); // botões nos dropdowns

    const hasThinkingMode = plan.features.includes('thinking_mode');

    if (!hasThinkingMode) {
        // Usuário gratuito - desabilitar thinking mode
        if (toggle) {
            toggle.classList.add('disabled');
            toggle.title = `Thinking Mode disponível no plano ${plan.is_premium ? 'Premium' : 'Básico'}`;

            // Forçar desligar se estiver ligado
            if (toggle.classList.contains('active')) {
                toggle.classList.remove('active');
                currentThinkingMode = false;
            }
        }

        // Desabilitar nos dropdowns também
        thinkingBtns.forEach(btn => {
            btn.classList.add('disabled');
            btn.style.opacity = '0.5';
        });

        // Mostrar badge de upgrade
        showUpgradeBadge();

    } else {
        // Usuário premium - habilitar thinking mode
        if (toggle) {
            toggle.classList.remove('disabled');
            toggle.title = 'Thinking Mode disponível';
        }

        thinkingBtns.forEach(btn => {
            btn.classList.remove('disabled');
            btn.style.opacity = '1';
        });

        hideUpgradeBadge();
    }
}

function updateUsageDisplay(usage, plan) {

    // Criar ou atualizar display de uso
    let usageDisplay = document.getElementById('usage-display');
    if (!usageDisplay) {
        usageDisplay = createUsageDisplay();
    }

    const hourUsed = usage.hour.messages;
    const hourLimit = plan.messages_per_hour;
    const dayUsed = usage.day.messages;
    const dayLimit = plan.messages_per_day;

    const hourPercent = (hourUsed / hourLimit) * 100;
    const dayPercent = (dayUsed / dayLimit) * 100;

    // Atualizar conteúdo
    usageDisplay.innerHTML = `
        <div class="usage-info">
            <div class="plan-badge">${plan.name}</div>
            <div class="usage-stats">
                <div class="usage-item ${hourPercent > 80 ? 'warning' : ''}">
                    <span>Hora: ${hourUsed}/${hourLimit}</span>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: ${hourPercent}%"></div>
                    </div>
                </div>
                <div class="usage-item ${dayPercent > 80 ? 'warning' : ''}">
                    <span>Hoje: ${dayUsed}/${dayLimit}</span>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: ${dayPercent}%"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Mostrar avisos se necessário
    if (hourPercent > 90) {
        showLimitWarning('Você usou mais de 90% do limite por hora!');
    } else if (dayPercent > 90) {
        showLimitWarning('Você usou mais de 90% do limite diário!');
    }
}

function createUsageDisplay() {
    const display = document.createElement('div');
    display.id = 'usage-display';
    display.className = 'usage-display';

    // Adicionar no topo do chat ou em local visível
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.insertBefore(display, chatContainer.firstChild);
    }

    return display;
}

function showUpgradeBadge() {
    let badge = document.getElementById('upgrade-badge');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'upgrade-badge';
        badge.className = 'upgrade-badge';
        badge.innerHTML = `
            <span>🚀 Upgrade para Premium</span>
            <button onclick="showUpgradeModal()">Ver Planos</button>
        `;

        // Adicionar ao body ou container principal
        document.body.appendChild(badge);
    }
    badge.style.display = 'block';
}

function hideUpgradeBadge() {
    const badge = document.getElementById('upgrade-badge');
    if (badge) {
        badge.style.display = 'none';
    }
}

function showLimitWarning(message) {
    // Criar toast de aviso
    const toast = document.createElement('div');
    toast.className = 'toast toast-warning limit-warning';
    toast.innerHTML = `
        ⚠️ ${message}
        <button onclick="showUpgradeModal()" class="upgrade-btn-small">Fazer Upgrade</button>
    `;

    document.body.appendChild(toast);

    // Auto remover após 5 segundos
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

function showUpgradeModal() {
    // Criar modal de upgrade
    const modal = document.createElement('div');
    modal.className = 'upgrade-modal';
    modal.innerHTML = `
        <div class="upgrade-modal-content">
            <div class="upgrade-modal-header">
                <h3>🚀 Desbloqueie o Thinking Mode</h3>
                <button onclick="closeUpgradeModal()" class="close-btn">×</button>
            </div>
            <div class="upgrade-modal-body">
                <p>O <strong>Thinking Mode</strong> permite que o Titan pense em voz alta por mais tempo para dar respostas mais elaboradas.</p>
                
                <div class="plans-comparison">
                    <div class="plan-card current">
                        <h4>Seu Plano Atual</h4>
                        <div class="plan-price">Gratuito</div>
                        <ul>
                            <li>✅ 10 mensagens/hora</li>
                            <li>✅ 50 mensagens/dia</li>
                            <li>❌ Thinking Mode</li>
                        </ul>
                    </div>
                    
                    <div class="plan-card premium">
                        <h4>Plano Básico</h4>
                        <div class="plan-price">R$ 19,90/mês</div>
                        <ul>
                            <li>✅ 100 mensagens/hora</li>
                            <li>✅ 500 mensagens/dia</li>
                            <li>✅ Thinking Mode Ilimitado</li>
                        </ul>
                        <button onclick="selectPlan('basic')" class="btn-upgrade">Escolher Básico</button>
                    </div>
                    
                    <div class="plan-card pro">
                        <h4>Plano Pro</h4>
                        <div class="plan-price">R$ 49,99/mês</div>
                        <ul>
                            <li>✅ 1000 mensagens/hora</li>
                            <li>✅ 5000 mensagens/dia</li>
                            <li>✅ Thinking Mode + Web Search</li>
                        </ul>
                        <button onclick="selectPlan('pro')" class="btn-upgrade">Escolher Pro</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

function closeUpgradeModal() {
    const modal = document.querySelector('.upgrade-modal');
    if (modal) {
        modal.remove();
    }
}

async function createStripeCheckout(priceId) {
    try {
        const response = await fetchAPI('/auth/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                price_id: priceId
            })
        });

        const data = await response.json();

        if (data.checkout_url) {
            window.location.href = data.checkout_url;
        } else {
            alert('Erro ao criar sessão de checkout');
        }
    } catch (error) {
        alert('Erro: ' + error.message);
    }
}

// =================== FUNÇÕES DE CHECKOUT - ADICIONAR NO FINAL ===================

window.selectPlan = async function (planType) {
    console.log('🛒 Selecionando plano:', planType);

    // Fechar modal
    const modal = document.querySelector('.upgrade-modal');
    if (modal) modal.remove();

    // Price IDs
    const priceIds = {
        'basic': 'price_1Rb8yJI0nP81FHlVezCBt5jT',
        'pro': 'price_1Rb92YI0nP81FHlVGTp9sYKT'
    };

    const priceId = priceIds[planType];
    if (!priceId) {
        alert('Plano inválido: ' + planType);
        return;
    }

    console.log('💳 Price ID:', priceId);

    try {
        const response = await fetchAPI('/auth/create-checkout-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ price_id: priceId })
        });

        console.log('📡 Status:', response.status);

        const data = await response.json();
        console.log('📡 Data:', data);

        if (data.checkout_url) {
            console.log('🚀 Redirecionando...');
            window.location.href = data.checkout_url;
        } else {
            alert('Erro: ' + (data.error || 'Sem URL'));
        }
    } catch (error) {
        console.error('❌ Erro:', error);
        alert('Erro: ' + error.message);
    }
};

console.log('✅ Função selectPlan carregada!');

// ===== INTERCEPTAR TENTATIVAS DE USAR THINKING MODE =====
async function toggleThinkingClean() {
    // Primeiro verificar se usuário tem permissão
    try {
        const response = await fetchAPI('/api/user-status');
        const data = await response.json();

        if (data.logged_in) {
            const hasThinkingMode = data.plan.features.includes('thinking_mode');

            if (!hasThinkingMode && !currentThinkingMode) {
                // Usuário gratuito tentando ativar - mostrar upgrade
                showUpgradePrompt();
                return;
            }
        }
    } catch (error) {
        console.error('Erro ao verificar permissões:', error);
    }

    // Se chegou até aqui, prosseguir normalmente
    const newMode = !currentThinkingMode;
    console.log('🧠 Mudando thinking mode para:', newMode ? 'ATIVADO' : 'DESATIVADO');

    try {
        const response = await fetchAPI('/thinking-mode', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ enabled: newMode })
        });

        const data = await response.json();
        console.log('Resposta do servidor:', data);

        if (data.status === 'sucesso') {
            currentThinkingMode = newMode;
            applyTheme(currentThinkingMode);
            updateThinkingToggleVisual();
            console.log('Thinking mode atualizado:', currentThinkingMode ? 'ATIVADO' : 'DESATIVADO');
        } else {
            console.error('Erro do servidor:', data);
            throw new Error('Falha no servidor');
        }
    } catch (error) {
        console.error('Erro ao alterar thinking mode:', error);
        // Fallback: aplicar localmente mesmo com erro
        currentThinkingMode = newMode;
        applyTheme(currentThinkingMode);
        updateThinkingToggleVisual();
    }
}

function showUpgradePrompt() {
    const modal = document.createElement('div');
    modal.className = 'upgrade-prompt-modal';
    modal.innerHTML = `
        <div class="upgrade-prompt-content">
            <div class="upgrade-prompt-header">
                <h3>🧠 Thinking Mode Premium</h3>
                <button onclick="this.closest('.upgrade-prompt-modal').remove()" class="close-btn">×</button>
            </div>
            <div class="upgrade-prompt-body">
                <p>O <strong>Thinking Mode</strong> permite que o Titan pense por mais tempo em problemas complexos, oferecendo respostas mais elaboradas e detalhadas.</p>
                <div class="feature-comparison">
                    <div class="plan-column current">
                        <h4>Seu Plano Atual</h4>
                        <div class="plan-features">
                            <div class="feature">✅ 10 mensagens/hora</div>
                            <div class="feature">✅ 50 mensagens/dia</div>
                            <div class="feature disabled">❌ Thinking Mode</div>
                        </div>
                    </div>
                    <div class="plan-column premium">
                        <h4>Plano Premium</h4>
                        <div class="plan-features">
                            <div class="feature">✅ 1000 mensagens/hora</div>
                            <div class="feature">✅ 5000 mensagens/dia</div>
                            <div class="feature">✅ Thinking Mode Ilimitado</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="upgrade-prompt-footer">
                <button onclick="this.closest('.upgrade-prompt-modal').remove()" class="btn-secondary">Talvez Depois</button>
                <button onclick="showUpgradeModal()" class="btn-primary">Ver Planos 🚀</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// ===== INICIALIZAR QUANDO PÁGINA CARREGA =====
document.addEventListener('DOMContentLoaded', function () {
    // Código de inicialização existente...

    // ADICIONAR: Verificar plano do usuário
    setTimeout(() => {
        checkUserPlanAndUpdateUI();
    }, 1000);
});

// ===== VERIFICAR APÓS ENVIAR MENSAGEM =====
// Modificar a função sendMessageToServer para atualizar uso
async function sendMessageToServer(message) {
    // ... código existente ...

    // APÓS ENVIAR MENSAGEM, ATUALIZAR USO
    setTimeout(() => {
        checkUserPlanAndUpdateUI();
    }, 2000);
}

// =================== OUTRAS FUNÇÕES ===================
function setQuickExample(example) {
    if (!mainInput) return;

    //  SANITIZAR EXEMPLO ANTES DE USAR
    const safeExample = escapeHtml(example);
    mainInput.value = safeExample;
    mainInput.focus();

    const container = mainInput.closest('.main-input-container');
    if (container) {
        container.style.borderColor = '#f59e0b';
        container.style.boxShadow = '0 0 0 3px rgba(245, 158, 11, 0.15)';

        setTimeout(() => {
            container.style.borderColor = '';
            container.style.boxShadow = '';
        }, 1500);
    }
}

function showKeyboardShortcuts() {
    const modal = document.getElementById('shortcutsModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

function startNewChat() {
    console.log('Nova conversa - RESET COMPLETO');

    // Cancelar requests
    if (currentRequest) {
        cancelCurrentRequest();
    }

    // Limpar tudo
    clearCurrentSession();
    userMessageCount = 0;
    feedbackShown = false;

    // Reset DOM
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }

    const chatInputArea = document.getElementById('chatInputArea');
    if (chatInputArea) {
        chatInputArea.style.display = 'none';
    }

    // FORÇA transição para welcome
    isInChatMode = false;

    if (chatContainer) {
        chatContainer.style.display = 'none';
        chatContainer.style.opacity = '0';
        chatContainer.classList.remove('active');
    }

    if (welcomeContainer) {
        welcomeContainer.style.display = 'flex';
        welcomeContainer.style.opacity = '1';
        welcomeContainer.style.transform = 'scale(1)';
        welcomeContainer.classList.remove('hidden');
    }

    // Focar input
    if (mainInput) {
        mainInput.value = '';
        setTimeout(() => mainInput.focus(), 100);
    }

    console.log('Reset completo para welcome');
}

function focusCurrentInput() {
    const chatInput = document.getElementById('chatInput');
    const mainInput = document.getElementById('mainInput');

    if (isInChatMode && chatInput && chatInput.offsetParent !== null) {
        chatInput.focus();
    } else if (mainInput) {
        mainInput.focus();
    }
}

function refreshMessages() {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) {
        console.log(' Container de mensagens não encontrado');
        return;
    }

    // Re-aplicar estilos baseados no thinking mode atual
    const assistantMessages = messagesContainer.querySelectorAll('.assistant-message');

    if (assistantMessages.length === 0) {
        console.log(' Nenhuma mensagem do assistente para atualizar');
        return;
    }

    // Atualizar cada mensagem do assistente
    assistantMessages.forEach((msg, index) => {
        const mode = currentThinkingMode ? 'Raciocínio' : 'Direto';
        const safeMode = sanitizeAttribute(mode);
        msg.setAttribute('data-mode', safeMode);

        // Se a mensagem tem thinking container, atualizar visibilidade
        const thinkingContainer = msg.querySelector('.thinking-container');
        if (thinkingContainer) {
            if (!currentThinkingMode) {
                thinkingContainer.style.opacity = '0.7';
            } else {
                thinkingContainer.style.opacity = '1';
            }
        }
    });

    console.log(` ${assistantMessages.length} mensagens atualizadas para modo: ${currentThinkingMode ? 'Raciocínio' : 'Direto'}`);
}

// =================== GESTÃO DE SESSÃO ===================
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function startNewSession() {
    sessionId = generateSessionId();
    conversationHistory = [];
    isNewSession = true;

    // Reset contadores para nova sessão
    userMessageCount = 0;
    feedbackShown = false;

    console.log('Nova sessão iniciada:', sessionId);
}

function clearCurrentSession() {
    // Cancelar request ativo antes de limpar
    if (currentRequest) {
        cancelCurrentRequest();
    }

    sessionId = null;
    conversationHistory = [];
    isNewSession = true;

    // Reset contadores
    userMessageCount = 0;
    feedbackShown = false;

    console.log('🧹 Sessão limpa');
}

// =================== FEEDBACK SYSTEM ===================
function initializeFeedbackSystem() {
    // Sistema de feedback será implementado
    console.log(' Sistema de feedback inicializado');
}

function checkForFeedback() {
    // Verificar se deve mostrar feedback
    if (userMessageCount >= 5 && !feedbackShown) {
        // Mostrar feedback após 5 mensagens
        feedbackShown = true;
        console.log(' Momento para feedback chegou');
    }
}

// =================== EVENTOS DE PÁGINA ===================
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        setTimeout(() => {
            const particles = document.getElementById('particles');
            if (particles && particles.children.length === 0) {
                createParticles();
            }
        }, 500);
    }
});

window.addEventListener('beforeunload', (e) => {
    // Cancelar request ativo antes de sair da página
    if (currentRequest) {
        console.log('🚪 Cancelando request antes de sair da página...');
        cancelCurrentRequest();
    }

    // Proteção contra fechamento acidental durante geração
    if (isGenerating && currentRequest) {
        e.preventDefault();
        e.returnValue = 'Há uma geração em andamento. Tem certeza que deseja sair?';
        return e.returnValue;
    }

    if (sessionId) {
        navigator.sendBeacon('/end-session', JSON.stringify({
            session_id: sessionId,
            timestamp: new Date().toISOString()
        }));
    }
});

function debugSessionInfo() {
    console.log(' DEBUG Sessão:', {
        sessionId: sessionId ? sessionId.substring(0, 8) + '...' : 'null',
        isInChatMode: isInChatMode,
        conversationHistory: conversationHistory.length,
        csrfToken: csrfToken ? 'presente' : 'ausente',
        currentThinkingMode: currentThinkingMode
    });
}

// =================== DEBUG FUNCTION ===================
function debugConnection() {
    console.log(' === DEBUG CONEXÃO ===');
    console.log('Estado atual:', {
        currentRequest: !!currentRequest,
        isGenerating: isGenerating,
        sessionId: sessionId,
        currentThinkingMode: currentThinkingMode
    });

    // Testar timeout do navegador
    const testController = new AbortController();
    const startTime = Date.now();

    fetchAPI('/status', {
        signal: testController.signal
    })
        .then(response => {
            console.log('Conexão OK -', Date.now() - startTime, 'ms');
            return response.json();
        })
        .then(data => {
            console.log('📊 Status do servidor:', data);
        })
        .catch(error => {
            console.log('Erro de conexão:', error);
        });

    // Testar streaming básico
    console.log(' Testando stream...');
    fetchAPI('/chat-stream', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
            mensagem: 'teste rápido',
            thinking_mode: false
        })
    })
        .then(response => {
            console.log('📡 Stream response:', response.status, response.headers.get('content-type'));
            if (response.body) {
                console.log('Response body disponível');
            } else {
                console.log('Response body NULL');
            }
        })
        .catch(error => {
            console.log('Erro no stream test:', error);
        });
}

// Exportar para console
window.debugConnection = debugConnection;

// ===== FUNÇÕES DO MENU LATERAL CLAUDE =====

let sidebarOpen = false;
let currentChatId = null;
let recentChats = [];

function toggleClaudeSidebar() {
    sidebarOpen = !sidebarOpen;

    if (sidebarOpen) {
        openClaudeSidebar();
    } else {
        closeClaudeSidebar();
    }
}

function openClaudeSidebar() {
    const sidebar = document.getElementById('claudeSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburgerBtn = document.getElementById('hamburgerBtn');

    if (sidebar && overlay && hamburgerBtn) {
        sidebar.classList.add('open');
        overlay.classList.add('active');
        hamburgerBtn.classList.add('hidden');
        sidebarOpen = true;

        // Carregar conversas recentes
        loadRecentChats();

    }
}

function closeClaudeSidebar() {
    const sidebar = document.getElementById('claudeSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburgerBtn = document.getElementById('hamburgerBtn');

    if (sidebar && overlay && hamburgerBtn) {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
        hamburgerBtn.classList.remove('hidden');
        sidebarOpen = false;
    }
}

function loadRecentChats() {
    const recentsList = document.getElementById('recentsList');
    if (!recentsList) return;

    // Se você tem chatHistory do sistema atual, use ele
    if (recentChats.length === 0) {
        recentsList.innerHTML = `
           <div class="recent-item" style="color: #666; text-align: center; padding: 20px; cursor: default;">
               Nenhuma conversa ainda<br>
               <small>Inicie uma conversa para ver o histórico</small>
           </div>
       `;
    } else {
        recentsList.innerHTML = recentChats.map(chat => `
           <div class="recent-item ${chat.id === currentChatId ? 'current-chat' : ''}" 
                onclick="loadChatFromSidebar('${chat.id}')">
               ${escapeHtml(chat.title)}
           </div>
       `).join('');
    }
}

function updateThinkingStatusInSidebar() {
    const thinkingStatus = document.getElementById('thinkingStatus');
    if (thinkingStatus) {
        thinkingStatus.textContent = currentThinkingMode ? 'Ativado' : 'Desativado';
    }
}

function addChatToRecents(chatTitle, chatId) {
    // Remover se já existe (para mover para o topo)
    recentChats = recentChats.filter(chat => chat.id !== chatId);

    // Adicionar no topo
    recentChats.unshift({
        id: chatId || generateChatId(),
        title: chatTitle,
        timestamp: new Date().toISOString()
    });

    // Limitar a 15 conversas
    if (recentChats.length > 15) {
        recentChats = recentChats.slice(0, 15);
    }

    // Atualizar lista se sidebar estiver aberta
    if (sidebarOpen) {
        loadRecentChats();
    }
}

function loadChatFromSidebar(chatId) {
    // Implementar depois - carregar conversa específica
    currentChatId = chatId;
    loadRecentChats(); // Atualizar visual
    closeClaudeSidebar();
    console.log('Carregando chat:', chatId);
}

function showTitanInfo() {
    const modal = document.getElementById('titanInfoModal');
    const modeIcon = document.getElementById('modeIcon');
    const modeText = document.getElementById('modeText');

    // Atualizar modo atual
    modeIcon.textContent = currentThinkingMode ? '' : '⚡';
    modeText.textContent = currentThinkingMode ? 'Raciocínio Profundo' : 'Resposta Direta';

    // Mostrar modal
    modal.style.display = 'flex';
    closeClaudeSidebar();
}

function closeTitanInfo() {
    const modal = document.getElementById('titanInfoModal');
    modal.style.display = 'none';
}

// Função para gerar ID único
function generateChatId() {
    return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
}

// Função para gerar título da conversa
function generateChatTitle(message) {
    if (!message) return "Nova conversa";

    // Pegar primeiras palavras
    let title = message.substring(0, 40);
    if (message.length > 40) title += "...";

    // Limpar caracteres especiais
    title = title.replace(/[^\w\s\-\.\,\!\?]/g, '');

    return title || "Nova conversa";
}

// ===== DROPDOWN DE CONFIGURAÇÕES =====
let configDropdownOpen = false;

function toggleConfigDropdown() {
    console.log('toggleConfigDropdown chamada');
    const dropdown = document.getElementById('dropdownContent');

    if (!dropdown) {
        console.error('Dropdown não encontrado!');
        return;
    }

    configDropdownOpen = !configDropdownOpen;
    console.log('📱 Dropdown state:', configDropdownOpen);

    if (configDropdownOpen) {
        dropdown.classList.add('show');
        updateDropdownThinkingToggle();
        console.log('Dropdown aberto');
    } else {
        dropdown.classList.remove('show');
        console.log('Dropdown fechado');
    }
}

function toggleConfigDropdownChat() {
    console.log('toggleConfigDropdownChat chamada');
    const dropdown = document.getElementById('dropdownContentChat');

    if (!dropdown) {
        console.error('Dropdown chat não encontrado!');
        return;
    }

    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
    } else {
        dropdown.classList.add('show');
        updateDropdownThinkingToggleChat();
    }
}

function closeConfigDropdown() {
    const dropdown = document.getElementById('dropdownContent');
    if (dropdown) {
        dropdown.classList.remove('show');
    }
    configDropdownOpen = false;
    console.log(' Dropdown fechado');
}

function closeConfigDropdownChat() {
    const dropdown = document.getElementById('dropdownContentChat');
    if (dropdown) {
        dropdown.classList.remove('show');
    }
}

function updateDropdownThinkingToggle() {
    const toggle = document.getElementById('dropdownThinkingToggle');
    if (toggle) {
        if (currentThinkingMode) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
        console.log(' Toggle atualizado:', currentThinkingMode ? 'ATIVO' : 'INATIVO');
    }
}

function updateDropdownThinkingToggleChat() {
    const toggle = document.getElementById('dropdownThinkingToggleChat');
    if (toggle) {
        if (currentThinkingMode) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
    }
}

async function toggleThinkingFromDropdown() {
    console.log(' Alterando thinking mode via dropdown...');
    await toggleThinkingClean();
    updateDropdownThinkingToggle();
    updateDropdownThinkingToggleChat();
}

// Fechar dropdown ao clicar fora
document.addEventListener('click', function (e) {
    const dropdown = document.getElementById('configDropdown');
    const dropdownChat = document.getElementById('configDropdownChat');

    if (dropdown && !dropdown.contains(e.target)) {
        closeConfigDropdown();
    }

    if (dropdownChat && !dropdownChat.contains(e.target)) {
        closeConfigDropdownChat();
    }
});

console.log('Funções do dropdown carregadas!');

function setupThinkingModeClickOutside() {
    // Placeholder para funcionalidade futura
    console.log(' Setup thinking mode click outside configurado');
}

// =================== SISTEMA DE AÇÕES DAS MENSAGENS ===================
function addMessageActions(messageContainer, content, isUser = false) {
    // Só adicionar ações para mensagens do assistente
    if (isUser) return;

    const assistantDiv = messageContainer.querySelector('.assistant-message');
    if (!assistantDiv) return;

    // Verificar se já tem ações (para evitar duplicação)
    if (assistantDiv.querySelector('.message-actions')) return;

    // Pegar o template
    const template = document.getElementById('message-actions-template');
    if (!template) {
        console.error('Template de ações não encontrado!');
        return;
    }

    // Clonar o template
    const actionsClone = template.content.cloneNode(true);
    const actionsContainer = actionsClone.querySelector('.message-actions');

    // Armazenar o conteúdo para uso posterior
    actionsContainer.setAttribute('data-content', content);

    // Adicionar event listeners
    const regenerateBtn = actionsClone.querySelector('.regenerate-btn');
    const likeBtn = actionsClone.querySelector('.like-btn');
    const dislikeBtn = actionsClone.querySelector('.dislike-btn');
    const copyBtn = actionsClone.querySelector('.copy-btn');

    regenerateBtn.addEventListener('click', () => regenerateMessage(regenerateBtn));
    likeBtn.addEventListener('click', () => likeMessage(likeBtn));
    dislikeBtn.addEventListener('click', () => dislikeMessage(dislikeBtn));
    copyBtn.addEventListener('click', () => copyMessage(copyBtn));

    // Adicionar ao DOM
    assistantDiv.appendChild(actionsClone);

    console.log('Ações adicionadas à mensagem');
}

async function regenerateMessage(button) {
    console.log(' Regenerando mensagem...');

    // Animação visual
    button.classList.add('animate');
    setTimeout(() => button.classList.remove('animate'), 300);

    // Pegar a mensagem anterior do usuário para reenviar
    const messageContainer = button.closest('.message');
    const messagesContainer = document.getElementById('chatMessages');
    const messages = Array.from(messagesContainer.querySelectorAll('.message'));
    const currentIndex = messages.indexOf(messageContainer);

    // Procurar a mensagem do usuário anterior
    let userMessage = null;
    for (let i = currentIndex - 1; i >= 0; i--) {
        if (messages[i].classList.contains('user')) {
            const userContent = messages[i].querySelector('.message-content');
            if (userContent) {
                userMessage = userContent.textContent.trim();
                break;
            }
        }
    }

    if (!userMessage) {
        showToast('Não foi possível encontrar a mensagem anterior', 'error');
        return;
    }

    // Processar comando e reenviar
    const finalMessage = addThinkingCommand(userMessage);

    // Remover a mensagem atual do assistente
    messageContainer.remove();

    // Reenviar mensagem
    await sendMessageToServer(finalMessage);
}

function likeMessage(button) {
    console.log('👍 Mensagem curtida');

    // Animação e estado visual
    button.classList.add('animate', 'liked');
    setTimeout(() => button.classList.remove('animate'), 300);

    // Remover dislike se existir
    const actionsContainer = button.closest('.message-actions');
    const dislikeBtn = actionsContainer.querySelector('.dislike-btn');
    if (dislikeBtn) {
        dislikeBtn.classList.remove('disliked');
    }

    // Feedback visual
    const textSpan = button.querySelector('.action-btn-text');
    const originalText = textSpan.textContent;
    textSpan.textContent = 'Obrigado!';

    setTimeout(() => {
        textSpan.textContent = originalText;
    }, 2000);

    // Enviar feedback para o servidor
    sendFeedbackToServer('like', button);
}

function dislikeMessage(button) {
    console.log('👎 Mensagem não curtida');

    // Animação e estado visual
    button.classList.add('animate', 'disliked');
    setTimeout(() => button.classList.remove('animate'), 300);

    // Remover like se existir
    const actionsContainer = button.closest('.message-actions');
    const likeBtn = actionsContainer.querySelector('.like-btn');
    if (likeBtn) {
        likeBtn.classList.remove('liked');
    }

    // Feedback visual
    const textSpan = button.querySelector('.action-btn-text');
    const originalText = textSpan.textContent;
    textSpan.textContent = 'Anotado';

    setTimeout(() => {
        textSpan.textContent = originalText;
    }, 2000);

    // Enviar feedback para o servidor
    sendFeedbackToServer('dislike', button);
}

async function copyMessage(button) {
    try {
        // 1. Encontrar o container da mensagem
        const messageContainer = button.closest('.message');
        if (!messageContainer) {
            return; // Falha silenciosa
        }

        // 2. Buscar conteúdo em diferentes lugares
        let textToCopy = '';

        // Tentar .message-content primeiro
        const messageContent = messageContainer.querySelector('.message-content');
        if (messageContent) {
            textToCopy = messageContent.innerText || messageContent.textContent || '';
        }

        // Se não achou, tentar .streaming-content
        if (!textToCopy) {
            const streamingContent = messageContainer.querySelector('.streaming-content');
            if (streamingContent) {
                textToCopy = streamingContent.innerText || streamingContent.textContent || '';
            }
        }

        // Se ainda não achou, pegar tudo da mensagem do assistente
        if (!textToCopy) {
            const assistantMessage = messageContainer.querySelector('.assistant-message');
            if (assistantMessage) {
                const clone = assistantMessage.cloneNode(true);
                const thinkingContainer = clone.querySelector('.thinking-container');
                const messageActions = clone.querySelector('.message-actions');

                if (thinkingContainer) thinkingContainer.remove();
                if (messageActions) messageActions.remove();

                textToCopy = clone.innerText || clone.textContent || '';
            }
        }

        // 3. Se não encontrou nada, sair silenciosamente
        if (!textToCopy || textToCopy.trim().length === 0) {
            return; // Falha silenciosa
        }

        // 4. Limpar o texto
        textToCopy = textToCopy.trim();

        // 5. Copiar - múltiplos métodos
        let copiouSucesso = false;

        // Método 1: Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            try {
                await navigator.clipboard.writeText(textToCopy);
                copiouSucesso = true;
            } catch (clipboardError) {
                // Falha silenciosa, tenta próximo método
            }
        }

        // Método 2: Fallback
        if (!copiouSucesso) {
            try {
                const textarea = document.createElement('textarea');
                textarea.value = textToCopy;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                textarea.style.top = '-9999px';
                document.body.appendChild(textarea);

                textarea.focus();
                textarea.select();

                const copiado = document.execCommand('copy');
                document.body.removeChild(textarea);

                if (copiado) {
                    copiouSucesso = true;
                }
            } catch (execError) {
                // Falha silenciosa
            }
        }

        // 6. Feedback visual MÍNIMO (só no botão)
        if (copiouSucesso) {
            button.classList.add('animate', 'copied');
            setTimeout(() => button.classList.remove('animate'), 300);

            const textSpan = button.querySelector('.action-btn-text');
            if (textSpan) {
                const originalText = textSpan.textContent;
                textSpan.textContent = 'Copiado!';

                setTimeout(() => {
                    textSpan.textContent = originalText;
                    button.classList.remove('copied');
                }, 1500);
            }
        }
        // Se falhou, não faz nada - SILÊNCIO TOTAL

    } catch (error) {
        // SILÊNCIO TOTAL - apenas log interno
        console.error('Erro silencioso:', error);
    }
}

async function sendFeedbackToServer(type, button) {
    try {
        const actionsContainer = button.closest('.message-actions');
        const content = actionsContainer.getAttribute('data-content');

        // Enviar feedback para o servidor
        const response = await fetchAPI('/feedback', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                type: type,
                content: content,
                session_id: sessionId,
                timestamp: new Date().toISOString()
            })
        });

        if (response.ok) {
            console.log(`Feedback ${type} enviado com sucesso`);
        }
    } catch (error) {
        console.warn('Erro ao enviar feedback:', error);
    }
}

// ===== FUNÇÕES DO MODAL PRO =====
function openProModal() {
    const modal = document.getElementById('proModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeProModal() {
    const modal = document.getElementById('proModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function selectPlan(planType) {
    console.log(`Plano selecionado: ${planType}`);

    if (planType === 'annual') {
        showToast('Redirecionando para pagamento anual...', 'success');
    } else {
        showToast('Redirecionando para pagamento mensal...', 'success');
    }

    closeProModal();
}

// Fechar modal clicando fora
document.addEventListener('click', function (e) {
    const modal = document.getElementById('proModal');
    if (modal && e.target === modal) {
        closeProModal();
    }
});


// =================== EXPORTAR FUNÇÕES GLOBAIS ===================
window.toggleConfigDropdown = toggleConfigDropdown;
window.closeConfigDropdown = closeConfigDropdown;
window.toggleThinkingFromDropdown = toggleThinkingFromDropdown;
window.setQuickExample = setQuickExample;
window.toggleSettingsTab = toggleSettingsTab;
window.toggleThinkingClean = toggleThinkingClean;
window.showKeyboardShortcuts = showKeyboardShortcuts;
window.closeModal = closeModal;
window.startNewChat = startNewChat;
window.backToWelcome = backToWelcome;
window.toggleThinking = toggleThinking;
window.cancelCurrentRequest = cancelCurrentRequest;
window.toggleClaudeSidebar = toggleClaudeSidebar;
window.openClaudeSidebar = openClaudeSidebar;
window.closeClaudeSidebar = closeClaudeSidebar;
window.showTitanInfo = showTitanInfo;
window.closeTitanInfo = closeTitanInfo;
window.closeConfigDropdownChat = closeConfigDropdownChat;
window.toggleConfigDropdownChat = toggleConfigDropdownChat;
window.regenerateMessage = regenerateMessage;
window.likeMessage = likeMessage;
window.copyMessage = copyMessage;
window.addMessageActions = addMessageActions;
window.regenerateMessage = regenerateMessage;
window.likeMessage = likeMessage;
window.dislikeMessage = dislikeMessage;
window.copyMessage = copyMessage;
window.addMessageActions = addMessageActions;
window.openProModal = openProModal;
window.closeProModal = closeProModal;
window.selectPlan = selectPlan;

console.log('Sistema de ações das mensagens ATIVO!');
console.log('Titan Chat - Sistema com STREAMING REAL carregado!');