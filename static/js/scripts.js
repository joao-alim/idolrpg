document.addEventListener('DOMContentLoaded', function() {
    let tipoBuzzSelecionado = null;
    let musicaSelecionadaId = null;
    const mensagemElement = document.getElementById('mensagem');

    function mostrarMensagem(texto, tipo = 'success') {
        mensagemElement.textContent = texto;
        mensagemElement.className = `alert alert-${tipo}`;
        mensagemElement.style.display = 'block';
        setTimeout(() => {
            mensagemElement.style.display = 'none';
        }, 3000);
    }

    document.querySelectorAll('.buzz-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            tipoBuzzSelecionado = this.getAttribute('data-tipo');
            
            document.querySelectorAll('.buzz-btn').forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
            
            mostrarMensagem(`Buzz ${tipoBuzzSelecionado} selecionado!`);
        });
    });

    document.querySelectorAll('.musica-row').forEach(row => {
        row.addEventListener('click', function() {
            musicaSelecionadaId = this.getAttribute('data-musica-id');
            
            document.querySelectorAll('.musica-row').forEach(r => {
                r.classList.remove('table-primary');
            });
            
            this.classList.add('table-primary');
            mostrarMensagem(`Música selecionada: ${this.querySelector('strong').textContent}`);
        });
    });

    document.querySelectorAll('.btn-aplicar-buzz').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            
            if (!tipoBuzzSelecionado) {
                mostrarMensagem('Selecione um tipo de Buzz primeiro!', 'danger');
                return;
            }
            
            if (!musicaSelecionadaId) {
                mostrarMensagem('Selecione uma música clicando nela!', 'danger');
                return;
            }

            try {
                const response = await fetch('/comprar_buzz', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tipo_buzz: tipoBuzzSelecionado,
                        musica_id: musicaSelecionadaId
                    }),
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.mensagem || 'Erro no servidor');
                }

                mostrarMensagem(data.mensagem, 'success');
                setTimeout(() => window.location.reload(), 1500);
                
            } catch (error) {
                console.error('Erro:', error);
                mostrarMensagem(error.message || 'Falha na comunicação com o servidor', 'danger');
            }
        });
    });
});