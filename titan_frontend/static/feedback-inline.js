// ===== SISTEMA DE FEEDBACK INTEGRADO =====

let currentFeedbackType = 'geral';

// ===== ABRIR MODAL =====
function openFeedbackModal() {
    document.getElementById('feedbackModal').style.display = 'flex';
    
    // Reset form
    document.getElementById('feedbackForm').reset();
    document.getElementById('feedbackType').value = 'geral';
    updateCharCounter();
    
    // Focus no primeiro campo
    setTimeout(() => {
        document.getElementById('feedbackTitleInput').focus();
    }, 300);
    
    console.log('💬 Modal de feedback aberto');
}

// ===== FECHAR MODAL =====
function closeFeedbackModal() {
    document.getElementById('feedbackModal').style.display = 'none';
    console.log('❌ Modal de feedback fechado');
}

// ===== SELECIONAR TIPO =====
function selectFeedbackType(tipo) {
    currentFeedbackType = tipo;
    document.getElementById('feedbackType').value = tipo;
    
    // Atualizar visual
    document.querySelectorAll('.feedback-type-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    document.querySelector(`[data-type="${tipo}"]`).classList.add('selected');
    
    // Atualizar título
    const titles = {
        'bug': 'Reportar Bug',
        'melhoria': 'Sugestão de Melhoria', 
        'problema': 'Problema de Uso',
        'resposta': 'Resposta Incorreta'
    };
    
    const icons = {
        'bug': '🐛',
        'melhoria': '💡',
        'problema': '⚠️', 
        'resposta': '🤖'
    };
    
    document.getElementById('feedbackTitle').textContent = titles[tipo];
    document.getElementById('feedbackIcon').textContent = icons[tipo];
    
    console.log(`🎯 Tipo selecionado: ${tipo}`);
}

// ===== CONTADOR DE CARACTERES =====
function updateCharCounter() {
    const textarea = document.getElementById('feedbackDescription');
    const counter = document.getElementById('descriptionCount');
    
    if (textarea && counter) {
        const count = textarea.value.length;
        counter.textContent = count;
        
        if (count > 900) {
            counter.style.color = '#ef4444';
        } else if (count > 800) {
            counter.style.color = '#f59e0b';
        } else {
            counter.style.color = '#6b7280';
        }
    }
}

// ===== ENVIAR FEEDBACK =====
async function submitFeedback() {
    const title = document.getElementById('feedbackTitleInput').value.trim();
    const description = document.getElementById('feedbackDescription').value.trim();
    
    if (!title || !description) {
        alert('Título e descrição são obrigatórios!');
        return;
    }
    
    const submitBtn = document.getElementById('submitFeedbackBtn');
    submitBtn.innerHTML = '<span class="spinner"></span> Enviando...';
    submitBtn.disabled = true;
    
    try {
        const feedbackData = {
            tipo: currentFeedbackType,
            titulo: title,
            categoria: 'geral',
            prioridade: 'media',
            descricao: description,
            passos_reproducao: document.getElementById('feedbackSteps').value.trim(),
            url_atual: window.location.href,
            timestamp: new Date().toISOString(),
            user_agent: navigator.userAgent,
            thinking_mode: document.body.classList.contains('thinking-theme')
        };
        
        console.log('📤 Enviando feedback real para servidor:', feedbackData);
        
        // ✅ CÓDIGO REAL - NÃO MAIS SIMULAÇÃO
        const response = await fetchAPI('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(feedbackData)
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'sucesso') {
            // Sucesso real
            document.getElementById('feedbackBody').innerHTML = `
                <div style="text-align: center; padding: 40px 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
                    <h3 style="color: var(--primary-color); margin-bottom: 12px;">Feedback enviado!</h3>
                    <p>Obrigado por nos ajudar a melhorar o Titan!</p>
                    <div style="background: var(--primary-rgba-1); border: 1px solid var(--primary-rgba-3); 
                               border-radius: 8px; padding: 12px; margin: 20px 0; font-family: monospace;">
                        <strong>ID:</strong> ${result.feedback_id}
                    </div>
                    <p style="color: #9ca3af; font-size: 12px;">
                        Feedback salvo com sucesso no servidor!
                    </p>
                </div>
            `;
        } else {
            alert('Erro ao enviar: ' + (result.erro || 'Erro desconhecido'));
        }
        
        // Auto-fechar após 3 segundos
        setTimeout(() => {
            closeFeedbackModal();
        }, 3000);
        
    } catch (error) {
        console.error('❌ Erro:', error);
        alert('Erro: ' + error.message);
    }
    
    submitBtn.innerHTML = '<span class="btn-icon">📤</span> Enviar Feedback';
    submitBtn.disabled = false;
}

// ===== EVENT LISTENERS =====
document.addEventListener('DOMContentLoaded', function() {
    // Contador de caracteres
    const textarea = document.getElementById('feedbackDescription');
    if (textarea) {
        textarea.addEventListener('input', updateCharCounter);
    }
    
    // Fechar com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeFeedbackModal();
        }
    });
    
    // Fechar clicando fora
    document.getElementById('feedbackModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeFeedbackModal();
        }
    });
    
    console.log('💬 Sistema de feedback integrado carregado!');
});