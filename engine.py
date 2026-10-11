from pathlib import Path
import struct
import json
import argparse
import sys


def verify_database(data_dir):
    """Varre o arquivo heap.db e gera um relatório de integridade estrutural."""
    caminho = Path(data_dir)
    arquivo_banco = caminho / "heap.db"

    relatorio = {
        "file": str(arquivo_banco),
        "status": "ok",
        "size_bytes": 0,
        "records": 0,
        "valid_records": 0,
        "tombstones": 0,
        "duplicate_keys": 0,
        "errors": [],
        "last_offset": 0,
    }

    if not arquivo_banco.exists():
        relatorio["status"] = "error"
        relatorio["errors"].append("Arquivo heap.db não encontrado.")
        return relatorio

    try:
        with open(arquivo_banco, "rb") as f_banco:
            relatorio["size_bytes"] = arquivo_banco.stat().st_size
            chaves_vistas = set()

            while True:
                offset = f_banco.tell()
                if offset >= relatorio["size_bytes"]:
                    break

                cabecalho = f_banco.read(12)
                if len(cabecalho) == 0:
                    break

                if len(cabecalho) < 12:
                    relatorio["status"] = "error"
                    relatorio["errors"].append(
                        f"Registro truncado em offset {offset}: cabeçalho incompleto."
                    )
                    break

                chave, tamanho_valor = struct.unpack(">QI", cabecalho)
                relatorio["records"] += 1
                relatorio["last_offset"] = offset

                payload = f_banco.read(tamanho_valor)
                if len(payload) != tamanho_valor:
                    relatorio["status"] = "error"
                    relatorio["errors"].append(
                        f"Registro truncado em offset {offset}: valor esperado {tamanho_valor}, "
                        f"lidos {len(payload)} bytes."
                    )
                    break

                try:
                    valor = payload.decode("utf-8")
                except UnicodeDecodeError:
                    relatorio["status"] = "error"
                    relatorio["errors"].append(
                        f"Registro inválido em offset {offset}: payload não é UTF-8 válido."
                    )
                    continue

                if chave in chaves_vistas:
                    relatorio["duplicate_keys"] += 1
                else:
                    chaves_vistas.add(chave)

                if valor == "__TOMBSTONE__":
                    relatorio["tombstones"] += 1
                else:
                    relatorio["valid_records"] += 1

    except OSError as exc:
        relatorio["status"] = "error"
        relatorio["errors"].append(f"Erro ao abrir o arquivo: {exc}")

    if relatorio["errors"] and relatorio["status"] != "warning":
        relatorio["status"] = "error"

    return relatorio


def print_verify_report(relatorio):
    print("=== RELATÓRIO DE INTEGRIDADE ===")
    print(f"Arquivo: {relatorio['file']}")
    print(f"Status: {relatorio['status'].upper()}")
    print(f"Tamanho: {relatorio['size_bytes']} bytes")
    print(f"Registros encontrados: {relatorio['records']}")
    print(f"Registros válidos: {relatorio['valid_records']}")
    print(f"Tombstones: {relatorio['tombstones']}")
    print(f"Chaves duplicadas: {relatorio['duplicate_keys']}")
    print(f"Erros detectados: {len(relatorio['errors'])}")

    if relatorio["errors"]:
        print("Detalhes:")
        for erro in relatorio["errors"]:
            print(f"- {erro}")
    else:
        print("Nenhum problema estrutural detectado.")


def main():
    # Cria o analisador principal
    parser = argparse.ArgumentParser(description="ED2 - Persistent Storage Engine")
    
    # Cria um gerenciador de subcomandos
    subparsers = parser.add_subparsers(dest="command", help="Comandos da engine")
    subparsers.required = True # Obriga o usuário a digitar um comando

    # Configura o comando 'init'
    parser_init = subparsers.add_parser("init", help="Inicializa o diretório de dados")
    parser_init.add_argument("--data-dir", required=True, help="Caminho para os dados")

    # Configura o comando 'run'
    parser_run = subparsers.add_parser("run", help="Executa as operações de leitura/escrita")
    parser_run.add_argument("--data-dir", required=True, help="Caminho para os dados")
    parser_run.add_argument("--input", required=True, help="Arquivo de entrada (JSONL)")
    parser_run.add_argument("--output", required=True, help="Arquivo de saída (JSONL)")

    # Configura o comando 'verify'
    parser_verify = subparsers.add_parser("verify", help="Verifica integridade do banco")
    parser_verify.add_argument("--data-dir", required=True, help="Caminho para os dados")

    # Configura o comando 'describe'
    parser_describe = subparsers.add_parser("describe", help="Mostra informações da engine")

    # Faz a leitura do que foi digitado no terminal
    args = parser.parse_args()

    # Roteamento: direciona para a lógica correta baseada no comando escolhido
    if args.command == "init":
        print(f"[DEBUG] Inicializando engine na pasta: {args.data_dir}")
        caminho = Path(args.data_dir)
        caminho.mkdir(parents=True, exist_ok=True)
        arquivo_banco = caminho / "heap.db"
        arquivo_banco.touch(exist_ok=True)

    elif args.command == "run":
        print(f"[DEBUG] Rodando workload de {args.input} e escrevendo em {args.output}")

        indice = {} # dicionario q funciona como um mapa de heap.db na memoria ram 

        pasta_dados = Path(args.data_dir)
        arquivo_banco = pasta_dados / "heap.db"

        if arquivo_banco.exists():
            print("[DEBUG] Recuperando dados do disco...")
            with open(arquivo_banco, "rb") as f_banco:
                while True:

                    offset = f_banco.tell()
                    cabecalho = f_banco.read(12)

                    if not cabecalho:
                        break

                    chave, tamanho_valor = struct.unpack(">QI", cabecalho)
                    valor_bytes = f_banco.read(tamanho_valor)
                    valor = valor_bytes.decode("utf-8")

                    if valor == "__TOMBSTONE__":
                        indice.pop(chave, None)
                    else:
                        indice[chave] = offset
                        

        with open(args.input, "r", encoding= "utf-8") as arquivo_entrada, \
        open(args.output, "w", encoding= "utf-8") as arquivo_saida:

            for linha in arquivo_entrada:

                operacao = json.loads(linha) # lendo do json
                id_op = operacao["id"]

                if operacao["op"] == "put":
                    chave = operacao["key"]
                    valor = operacao["value"]

                    valor_bytes = valor.encode("utf-8")
                    tamanho_valor = len(valor_bytes)

                    # O método struct.pack(formato, valores) usa caracteres para definir a conversão. Usaremos:
                    # > : Ordem de bytes Big-Endian (padrão de organização de memória comum em arquivos binários).
                    # Q : Unsigned long long (representa o uint64 da chave). 8 bytes
                    # I : Unsigned int (representa os 4 bytes para o tamanho do valor).

                    cabecalho = struct.pack(">QI", chave, tamanho_valor)

                    registro_completo = cabecalho + valor_bytes

                    with open(arquivo_banco, "ab") as f_banco:
                        offset = f_banco.tell() # pega a posição do cursor no fim do arquivo
                        f_banco.write(registro_completo)
                        indice[chave] = offset # salva no dicionario oq foi gravado agr

                    # salvando no arquivo de saida
                    resposta = {"id": id_op, "status": "ok"}
                    arquivo_saida.write(json.dumps(resposta) + "\n")

                elif operacao["op"] == "get": 
                    chave = operacao["key"]

                    if chave not in indice:
                        resposta = {"id": id_op, "status": "not_found"}
                        arquivo_saida.write(json.dumps(resposta) + "\n")

                    else:
                        offset = indice[chave]

                        with open(arquivo_banco, "rb") as f_banco:
                            f_banco.seek(offset) # move o cursor do arquivo para a posição apontada no dicionario de indices
                            cabecalho = f_banco.read(12)
                            _, tamanho_valor = struct.unpack(">QI", cabecalho) # usei o urderscore para o python ignorar o valor da chave lido, uma vez q ja sabemos

                            valor_bytes = f_banco.read(tamanho_valor)
                            valor = valor_bytes.decode("utf-8")

                        resposta = {"id": id_op, "status": "ok", "value": valor}
                        arquivo_saida.write(json.dumps(resposta) + "\n")

                elif operacao["op"] == "delete":
                    chave = operacao["key"]

                    if chave not in indice:
                        resposta = {"id": id_op, "status": "not_found"}
                        arquivo_saida.write(json.dumps(resposta) + "\n")

                    else:
                        del indice[chave]

                        tombstone = "__TOMBSTONE__"
                        tombstone_bytes = tombstone.encode("utf-8")
                        tamanho_tomb_bytes = len(tombstone_bytes)

                        cabecalho = struct.pack(">QI", chave, tamanho_tomb_bytes)

                        deletado_completo = cabecalho + tombstone_bytes

                        with open(arquivo_banco, "ab") as f_banco:
                            f_banco.write(deletado_completo)

                        resposta = {"id": id_op, "status": "ok"}
                        arquivo_saida.write(json.dumps(resposta) + "\n")

    elif args.command == "verify":
        relatorio = verify_database(args.data_dir)
        print_verify_report(relatorio)

        if relatorio["status"] == "error":
            raise SystemExit(1)

    elif args.command == "describe":
        print("=== ED2 Storage Engine ===")
        print("Tipo: Arquivo Heap com índice em memória")
        print("Objetivo: persistência de chave/valor com append-only log")
        print("Operações suportadas: put, get, delete")
        print("Recuperação: reconstrói o índice a partir de heap.db")
        print("Persistência: grava registros em disco em formato binário")
        print("Integridade: suporte a tombstones para exclusões")
        print("Alunos:")
        print("- Leonan Louvem")
        print("- Pedro Duarte")
        print("- Rodrigo Motta")
        print("- Giovane Bahia")

if __name__ == "__main__":
    main()