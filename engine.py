from pathlib import Path
import struct
import json
import argparse
import sys


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
                    indice[chave] = offset
                    f_banco.read(tamanho_valor)

        with open(args.input, "r", encoding= "utf-8") as arquivo_entrada, \
        open(args.output, "w", encoding= "utf-8") as arquivo_saida:

            for linha in arquivo_entrada:

                operacao = json.loads(linha) # lendo do json
                id_op = operacao["id"]

                #TODO
                if operacao["op"] == "put":
                    chave = operacao["key"]
                    valor = operacao["value"]

                    valor_bytes = valor.encode("utf-8")
                    tamanho_valor = len(valor_bytes)

                    # /*O método struct.pack(formato, valores) usa caracteres para definir a conversão. Usaremos:
                    # > : Ordem de bytes Big-Endian (padrão de organização de memória comum em arquivos binários).
                    # Q : Unsigned long long (representa o uint64 da chave).
                    # I : Unsigned int (representa os 4 bytes para o tamanho do valor). */

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
                    pass

                elif operacao["op"] == "delete":
                    pass



    elif args.command == "verify":
        print(f"[DEBUG] Verificando dados na pasta: {args.data_dir}")
    elif args.command == "describe":
        print("Engine ED2 - Fase 1: Arquivo Heap com Índice em Memória")
        print("Aluno: Leonan Louvem")

if __name__ == "__main__":
    main()