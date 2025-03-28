document.addEventListener('DOMContentLoaded', function() {
    let tipoBuzzSelecionado = null;
    let musicaSelecionadaId = null;

    // Selecionar tipo de Buzz
    document.querySelectorAll('.buzz-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove a seleção de todos os botões
            document.querySelectorAll('.buzz-btn').forEach(b => {
                b.classList.remove('active', 'border-dark');
            });
            
            // Adiciona seleção ao botão clicado
            this.classList.add('active', 'border-dark');
            tipoBuzzSelecionado = this.id.replace('buzz', '').toLowerCase();
            
            showAlert(`Buzz ${tipoBuzzSelecionado} selecionado. Agora clique em uma música.`, 'info');
        });
    });

    // Selecionar música
    document.querySelectorAll('.musica-row').forEach(row => {
        row.addEventListener('click', function() {
            musicaSelecionadaId = this.dataset.musicaId;
            
            // Remove a seleção de todas as linhas
            document.querySelectorAll('.musica-row').forEach(r => {
                r.classList.remove('selecionada');
            });
            
            // Adiciona seleção à linha clicada
            this.classList.add('selecionada');
        });
    });

    // Aplicar Buzz
    document.querySelectorAll('.btn-aplicar-buzz').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            
            if (!tipoBuzzSelecionado) {
                showAlert('Selecione um tipo de Buzz primeiro', 'warning');
                return;
            }
            
            if (!musicaSelecionadaId) {
                showAlert('Selecione uma música clicando nela', 'warning');
                return;
            }

            aplicarBuzz();
        });
    });

    function aplicarBuzz() {
        showAlert('Processando seu Buzz...', 'info');
        
        fetch('/comprar_buzz', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tipo_buzz: tipoBuzzSelecionado,
                musica_id: musicaSelecionadaId
            }),
        })
        .then(response => {
            if (!response.ok) throw new Error('Erro na rede');
            return response.json();
        })
        .then(data => {
            if (data.sucesso) {
                showAlert(data.mensagem, 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showAlert(data.mensagem, 'danger');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            showAlert('Falha ao conectar com o servidor', 'danger');
        });
    }

    function showAlert(mensagem, tipo) {
        const alertDiv = document.getElementById('mensagem');
        alertDiv.innerHTML = `
            <div class="alert alert-${tipo} alert-dismissible fade show">
                ${mensagem}
                <button type="button" class="close" onclick="this.parentElement.style.display='none'">
                    <span>&times;</span>
                </button>
            </div>
        `;
        alertDiv.style.display = 'block';
    }
});