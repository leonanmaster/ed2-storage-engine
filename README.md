# 🚧 ED2 - Persistent Storage Engine (Fase 1)

Este documento é de uso estritamente interno da nossa equipe. Serve para nos situarmos sobre o que já foi desenhado, o que está funcionando no código e onde cada um pode pegar para continuar o trabalho da Entrega 1.

## 📌 Arquitetura Escolhida
Optamos por utilizar Python com a estratégia de Arquivo Heap (Log-Structured) + Índice em Memória RAM (estilo Bitcask).
O nosso engine escreve os dados sempre no final do arquivo (append-only) para garantir máxima velocidade de escrita. Na memória RAM, mantemos um dicionário (indice = {}) que guarda a posição exata (offset) de cada chave no disco para permitir buscas diretas e rápidas.

## ✅ O que já está feito e funcionando

* Estrutura Base e CLI: O arquivo engine.py processa os argumentos de terminal (init, run, verify, describe) usando argparse.
* Comando init: Cria o diretório de dados e o arquivo heap.db usando pathlib.
* Comando run -> Operação put: Empacota a chave (uint64) e o tamanho do valor (uint32) em um cabeçalho binário (12 bytes) com struct (>QI). Grava no modo "ab" (append) no fim do disco e salva o offset na RAM.
* Comando run -> Operação get: Consulta o índice na RAM. Se existir, usa f_banco.seek(offset) para pular direto para o byte correto, lê o cabeçalho, descobre o tamanho e lê apenas os bytes do valor (decodificando de utf-8). Se não existir, retorna "not_found".
* Comando run -> Operação delete (Tombstone): Remove a chave da RAM (del indice[chave]) e grava no disco um novo registro no final com o valor especial "__TOMBSTONE__" para invalidar a chave permanentemente.
* Recuperação de Falhas (Recovery): Antes de processar os comandos no 'run', o sistema lê o heap.db inteiro. Reconstrói o índice na RAM com os offsets mais recentes. Se ler um valor "__TOMBSTONE__", apaga a chave da RAM (indice.pop), garantindo a persistência das exclusões.

## ❌ O que falta fazer (Próximos Passos)

* Comando verify: Implementar a lógica de varrer o banco de dados para checar a integridade estrutural do arquivo e gerar o relatório exigido.
* Comando describe: Apenas imprimir as informações da engine e dados do aluno.

## 💻 Como testar o código localmente

1. Ativar o ambiente virtual (Obrigatório antes de rodar o código):
(Nota: O ambiente virtual não vai para o Git, cada membro tem de criar o seu localmente com python3 -m venv .venv).
source .venv/bin/activate

2. Criar um arquivo de teste de gravação (dia1.jsonl):
echo '{"id": 1, "op": "put", "key": 55, "value": "dado importante"}' > dia1.jsonl
echo '{"id": 2, "op": "put", "key": 77, "value": "dado temporario"}' >> dia1.jsonl
echo '{"id": 3, "op": "delete", "key": 77}' >> dia1.jsonl

3. Testar inicialização e gravação:
rm -rf dados
python engine.py init --data-dir ./dados
python engine.py run --data-dir ./dados --input dia1.jsonl --output resultado_dia1.jsonl

4. Criar um arquivo de teste de leitura (dia2.jsonl) para provar a persistência:
echo '{"id": 1, "op": "get", "key": 55}' > dia2.jsonl
echo '{"id": 2, "op": "get", "key": 77}' >> dia2.jsonl

5. Testar a recuperação de falhas (Recovery):
python engine.py run --data-dir ./dados --input dia2.jsonl --output resultado_dia2.jsonl
(O resultado_dia2.jsonl deve mostrar o id 1 como "ok" com o valor, e o id 2 como "not_found").