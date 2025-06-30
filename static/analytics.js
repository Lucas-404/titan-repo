let autoRefreshInterval;

// Função para carregar dados iniciais
function loadInitialData() {
    // Pegar dados do elemento hidden
    const dataElement = document.getElementById('analytics-data');
    let initialData = {};
    
    if (dataElement) {
        try {
            initialData = JSON.parse(dataElement.textContent);
        } catch (e) {
            console.error('Erro ao parsear dados:', e);
            initialData = { erro: 'Erro ao carregar dados iniciais' };
        }
    }
    
    updateInterface(initialData);
}

// Função para atualizar interface
function updateInterface(data) {
    if (data.erro) {
        showError(data.erro);
        return;
    }

    // Esconder loading e mostrar conteúdo
    const loading = document.getElementById('loading');
    const mainContent = document.getElementById('main-content');
    
    if (loading) loading.style.display = 'none';
    if (mainContent) mainContent.style.display = 'block';

    // Atualizar métricas principais
    updateElement('usuarios-ativos', data.usuarios_ativos);
    updateElement('usuarios-hoje', data.usuarios_hoje);
    updateElement('aprovacao', data.aprovacao);
    updateElement('likes', data.likes);
    updateElement('dislikes', data.dislikes);
    updateElement('uptime', data.uptime_horas);
    updateElement('total-requests', data.total_requests);
    updateElement('total-memorias', data.total_memorias);
    updateElement('cache-efficiency', data.cache_efficiency);

    // Atualizar status indicators
    updateStatusIndicators(data);

    // Atualizar gráficos
    updateActivityChart(data.atividade_horas);
    updateCategoriesChart(data.categorias_top);

    // Atualizar problemas
    updateProblemsSection(data.mensagens_problematicas);

    // Atualizar timestamp
    updateElement('last-update', new Date().toLocaleTimeString('pt-BR'));
}

// Função auxiliar para atualizar elementos
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined && value !== null) {
        element.textContent = value;
    }
}

function updateStatusIndicators(data) {
    const container = document.getElementById('status-indicators');
    if (!container) return;
    
    const sistemaClass = 'dot-green';
    const capacidadeClass = (data.usuarios_ativos || 0) < (data.max_usuarios || 10) ? 'dot-green' : 'dot-yellow';
    
    let satisfacaoClass = 'dot-red';
    const aprovacao = data.aprovacao || 0;
    if (aprovacao > 70) satisfacaoClass = 'dot-green';
    else if (aprovacao > 50) satisfacaoClass = 'dot-yellow';

    container.innerHTML = `
        <div class="status-dot">
            <div class="dot ${sistemaClass}"></div>
            Sistema Online
        </div>
        <div class="status-dot">
            <div class="dot ${capacidadeClass}"></div>
            Capacidade: ${data.usuarios_ativos || 0}/${data.max_usuarios || 10}
        </div>
        <div class="status-dot">
            <div class="dot ${satisfacaoClass}"></div>
            Satisfação: ${aprovacao}%
        </div>
    `;
}

function updateActivityChart(atividadeHoras) {
    const container = document.getElementById('activity-chart');
    if (!container) return;

    const atividade = atividadeHoras || {};
    const valores = Object.values(atividade);
    const maxAtividade = Math.max(...valores, 1);

    let html = '';
    for (let hora = 0; hora < 24; hora++) {
        const horaStr = hora.toString().padStart(2, '0');
        const atividadeHora = atividade[horaStr] || 0;
        const altura = Math.round((atividadeHora * 150) / maxAtividade);

        html += `
            <div class="activity-bar" 
                 style="height: ${altura}px;" 
                 title="${hora}h: ${atividadeHora} ações">
                <div class="hour-label">${horaStr}</div>
            </div>
        `;
    }
    container.innerHTML = html;
}

function updateCategoriesChart(categoriasTop) {
    const container = document.getElementById('categories-list');
    if (!container) return;
    
    if (!categoriasTop || categoriasTop.length === 0) {
        container.innerHTML = `
            <li class="category-item">
                <span>Nenhuma categoria ainda</span>
                <div class="category-bar">
                    <div class="category-fill" style="width: 0%;"></div>
                </div>
                <span>0</span>
            </li>
        `;
        return;
    }

    const maxTotal = categoriasTop[0][1] || 1;
    let html = '';

    categoriasTop.forEach(([categoria, total]) => {
        const largura = Math.round((total * 100) / maxTotal);
        const categoriaNome = categoria ? categoria.charAt(0).toUpperCase() + categoria.slice(1) : 'Sem nome';
        
        html += `
            <li class="category-item">
                <span>${categoriaNome}</span>
                <div class="category-bar">
                    <div class="category-fill" style="width: ${largura}%;"></div>
                </div>
                <span>${total}</span>
            </li>
        `;
    });

    container.innerHTML = html;
}

function updateProblemsSection(mensagensProblematicas) {
    const section = document.getElementById('problems-section');
    const container = document.getElementById('problems-list');
    
    if (!section || !container) return;

    if (!mensagensProblematicas || mensagensProblematicas.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    let html = '';

    mensagensProblematicas.forEach(msg => {
        const timestamp = msg.timestamp ? msg.timestamp.substring(0, 16) : 'Data não disponível';
        const modo = msg.thinking_mode ? 'Thinking Mode' : 'Modo Direto';
        const preview = msg.preview || 'Preview não disponível';

        html += `
            <div class="problem-item">
                <strong>${timestamp}</strong> - ${modo}
                <div class="problem-preview">${escapeHtml(preview)}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(errorMessage) {
    const loading = document.getElementById('loading');
    const mainContent = document.getElementById('main-content');
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');

    if (loading) loading.style.display = 'none';
    if (mainContent) mainContent.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'block';
    if (errorText) errorText.textContent = errorMessage;
}

function refreshData() {
    const btn = document.getElementById('refresh-btn');
    if (btn) btn.classList.add('spinning');
    
    fetch('/analytics/api')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.erro) {
                console.error('Erro da API:', data.erro);
                return;
            }
            
            // ATUALIZAR TODAS AS MÉTRICAS
            updateElement('usuarios-ativos', data.usuarios_ativos || 0);
            updateElement('usuarios-hoje', data.usuarios_hoje || 0);
            updateElement('aprovacao', data.aprovacao || 0);
            updateElement('likes', data.likes || 0);
            updateElement('dislikes', data.dislikes || 0);
            updateElement('uptime', data.uptime_horas || 0);
            updateElement('total-requests', data.total_requests || 0);
            updateElement('total-memorias', data.total_memorias || 0);
            updateElement('cache-efficiency', data.cache_efficiency || 0);
            
            // ATUALIZAR STATUS INDICATORS
            updateStatusIndicators(data);
            
            // ATUALIZAR GRÁFICOS (NOVO!)
            updateActivityChart(data.atividade_horas || {});
            updateCategoriesChart(data.categorias_top || []);
            
            // ATUALIZAR PROBLEMAS (NOVO!)
            updateProblemsSection(data.mensagens_problematicas || []);
            
            // TIMESTAMP
            updateElement('last-update', data.ultimo_update || new Date().toLocaleTimeString('pt-BR'));
            
            console.log('✅ TODOS os dados atualizados!');
        })
        .catch(error => {
            console.error('Erro ao atualizar:', error);
            updateElement('last-update', 'Erro: ' + new Date().toLocaleTimeString('pt-BR'));
        })
        .finally(() => {
            const btn = document.getElementById('refresh-btn');
            if (btn) {
                setTimeout(() => {
                    btn.classList.remove('spinning');
                }, 500);
            }
        });
}

function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(refreshData, 30000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

function initializeAnalytics() {
    loadInitialData();
    startAutoRefresh();
    
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAnalytics);
} else {
    initializeAnalytics();
}