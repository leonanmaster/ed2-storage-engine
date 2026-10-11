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
* Comando verify: Varre o arquivo `heap.db` em busca de registros truncados, valores inválidos e inconsistências estruturais, produzindo um relatório com status, contagem de registros, tombstones e erros.
* Comando describe: Exibe uma descrição da engine, sua arquitetura e os autores do projeto.

## 🔎 Verificação de Integridade

O comando `verify` faz uma varredura estrutural do arquivo `heap.db` para garantir que o log binário ainda está consistente, mesmo em um banco append-only.

A lógica funciona assim:

1. Abre o arquivo em modo binário e percorre byte a byte em sequência.
2. Lê o cabeçalho de cada registro: `key` (8 bytes) + `value_size` (4 bytes).
3. Confirma se há bytes suficientes para completar o cabeçalho e o payload esperado.
4. Lê o valor correspondente e tenta decodificar em UTF-8.
5. Contabiliza registros válidos, tombstones e tamanho total do arquivo.
6. Gera um relatório final com `status`, número de registros, tombstones e erros detectados.

### O que é validado

- Arquivo `heap.db` existe e está acessível.
- O cabeçalho do registro é completo (`12 bytes`).
- O payload informado no cabeçalho realmente existe no arquivo.
- O valor do payload pode ser decodificado como UTF-8.
- O banco não apresenta truncamento ou corrupção de bytes estruturais.

### Como o verificador captura erros

O comando usa um varredor sequencial e, quando encontra algo inconsistente, registra a falha em vez de ignorá-la. Exemplos comuns:

- `Registro truncado em offset X: cabeçalho incompleto.`
  - O arquivo terminou antes de o cabeçalho completo ser lido.
- `Registro truncado em offset X: valor esperado N, lidos M bytes.`
  - O compromisso do registro diz que há `N` bytes no valor, mas o arquivo acabou antes disso.
- `Registro inválido em offset X: payload não é UTF-8 válido.`
  - O conteúdo gravado não corresponde a texto UTF-8 esperado pela engine.

### Exemplo de execução bem-sucedida

```bash
python3 engine.py verify --data-dir ./dados
```

Saída esperada:

```text
=== RELATÓRIO DE INTEGRIDADE ===
Arquivo: dados/heap.db
Status: OK
Tamanho: 237 bytes
Registros encontrados: 9
Registros válidos: 6
Tombstones: 3
Chaves duplicadas: 7
Erros detectados: 0
Nenhum problema estrutural detectado.
```

### Exemplo de arquivo corrompido

Se o `heap.db` for gerado com um payload menor do que o tamanho declarado no cabeçalho, o verificador identifica o problema imediatamente:

```text
=== RELATÓRIO DE INTEGRIDADE ===
Arquivo: dados_corrupt/heap.db
Status: ERROR
Tamanho: 15 bytes
Registros encontrados: 1
Registros válidos: 0
Tombstones: 0
Chaves duplicadas: 0
Erros detectados: 1
Detalhes:
- Registro truncado em offset 0: valor esperado 5, lidos 3 bytes.
```

Esse mecanismo é importante porque o sistema é um log de append-only: não é suficiente apenas verificar se o arquivo existe; também precisamos garantir que cada segmento do log ainda representa um registro válido e íntegro.

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