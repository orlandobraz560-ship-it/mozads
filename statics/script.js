// ==================== FUNÇÕES GLOBAIS ====================

// Mostrar toast notification
function mostrarToast(mensagem, tipo = 'sucesso') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div style="
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${tipo === 'sucesso' ? '#4caf50' : '#f44336'};
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            z-index: 9999;
            animation: fadeInOut 3s;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        ">
            ${mensagem}
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Confirmar ação
function confirmarAcao(mensagem, url) {
    if (confirm(mensagem)) {
        window.location.href = url;
    }
    return false;
}

// Copiar texto
function copiarTexto(texto, mensagem) {
    navigator.clipboard.writeText(texto);
    mostrarToast(mensagem || 'Copiado!', 'sucesso');
}

// Atualizar saldo automático (AJAX)
function atualizarSaldo() {
    fetch('/api/saldo')
        .then(response => response.json())
        .then(data => {
            const saldoElement = document.getElementById('saldo-total');
            const principalElement = document.getElementById('saldo-principal');
            const comissaoElement = document.getElementById('saldo-comissao');
            
            if (saldoElement) saldoElement.innerText = data.total.toFixed(2) + ' MZN';
            if (principalElement) principalElement.innerText = data.saldo_principal.toFixed(2) + ' MZN';
            if (comissaoElement) comissaoElement.innerText = data.saldo_comissao.toFixed(2) + ' MZN';
        })
        .catch(error => console.error('Erro:', error));
}

// Iniciar atualização automática do saldo (a cada 30 segundos)
if (document.getElementById('saldo-total')) {
    setInterval(atualizarSaldo, 30000);
}

// Validar formulário de saque
function validarSaque(input) {
    const valor = parseFloat(input.value);
    const maximo = parseFloat(input.getAttribute('max'));
    const erroElement = document.getElementById('erro-saldo');
    
    if (valor > maximo) {
        input.style.borderColor = 'red';
        if (erroElement) erroElement.innerText = 'Saldo insuficiente!';
        return false;
    } else {
        input.style.borderColor = 'green';
        if (erroElement) erroElement.innerText = '';
        return true;
    }
}

// Mostrar loading no botão
function mostrarLoading(btn, textoOriginal) {
    btn.disabled = true;
    btn.innerHTML = '<span class="loading">⏳</span> Processando...';
    
    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = textoOriginal;
    }, 2000);
}

// Animação fadeInOut
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
        10% { opacity: 1; transform: translateX(-50%) translateY(0); }
        90% { opacity: 1; transform: translateX(-50%) translateY(0); }
        100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
    }
    .loading {
        display: inline-block;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);