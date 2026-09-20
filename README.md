# ED2 - Persistent Storage Engine (Fase 1)

Este documento é de uso estritamente interno da nossa equipe. Serve para nos situarmos sobre o que já foi desenhado, o que está funcionando no código e onde cada um pode pegar para continuar o trabalho da Entrega 1.

## Arquitetura Escolhida
Optamos por utilizar Python com a estratégia de Arquivo Heap (Log-Structured) + Índice em Memória RAM. 
O nosso engine escreve os dados sempre no final do arquivo (append-only) para garantir máxima velocidade de escrita. Na memória RAM, mantemos um dicionário (indice = {}) que guarda a posição exata (offset) de cada chave no disco para permitir buscas diretas e rápidas.

## O que já está feito e funcionando

* Estrutura Base e CLI: O arquivo engine.py já processa todos os argumentos de terminal exigidos no roteiro (init, run, verify, describe) utilizando a biblioteca nativa argparse.
* Comando init: Já cria o diretório de dados e o arquivo de banco de dados heap.db de forma segura utilizando o módulo pathlib.
* Recuperação de Falhas (Recovery): A engine já é persistente. Quando o comando run inicia, ele verifica se o heap.db existe. Se existir, abre-o em modo de leitura binária ("rb"), lê apenas os cabeçalhos para poupar memória e reconstrói todo o indice na RAM antes de processar novos comandos.
* Comando run -> Operação put: 
  - Lê o arquivo workload.jsonl linha a linha.
  - Transforma a chave (uint64) e o tamanho do valor (uint32) em um cabeçalho binário de 12 bytes usando a biblioteca struct (formato >QI).
  - Grava o cabeçalho e os bytes do valor diretamente no final do arquivo heap.db (modo "ab").
  - Registra a posição da escrita no indice na RAM e escreve o estado "ok" no arquivo de saída.

## O que falta fazer (Próximos Passos)

* Operação get: Precisamos validar se a chave pedida existe no indice. Se existir, temos de usar a função .seek() para saltar o cursor do disco diretamente para o offset guardado e ler os bytes do valor.
* Operação delete: Implementar a estratégia de tombstone (em vez de apagar do meio do arquivo, apenas gravamos um novo registro no final informando que aquela chave foi apagada, e removemos a chave do indice da RAM).
* Comandos de apoio: Colocar as saídas esperadas nos comandos verify e describe.

## Como testar o código localmente

1. Ativar o ambiente virtual (Obrigatório antes de rodar o código):
(Nota: O ambiente virtual não vai para o Git, cada membro tem de criar o seu localmente com python3 -m venv .venv).
source .venv/bin/activate

2. Criar um arquivo de testes falso:
echo '{"id": 1, "op": "put", "key": 10, "value": "primeiro teste"}' > workload.jsonl
echo '{"id": 2, "op": "put", "key": 20, "value": "segundo teste"}' >> workload.jsonl

3. Testar a inicialização e gravação:
python engine.py init --data-dir ./dados
python engine.py run --data-dir ./dados --input workload.jsonl --output resultado.jsonl

4. Testar o Recovery:
Rode exatamente o mesmo comando run acima pela segunda vez. Você notará que o terminal imprime a mensagem [DEBUG] Recuperando dados do disco..., provando que o sistema leu o disco e reconstruiu o índice na memória com sucesso.