#!/usr/bin/env python3
import os
import time
import subprocess

# Configurações
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]  # Alvos de ping para testar conectividade
RETRY_INTERVAL = 1       # Intervalo entre os testes (em segundos)
MAX_RETRY = 5            # Número máximo de tentativas antes de reiniciar a rede
RESTART_CMD = "/etc/init.d/networking restart"  # Comando para reiniciar a rede

def is_connected(targets):
    """Verifica a conectividade com múltiplos alvos usando ping."""
    for target in targets:
        try:
            subprocess.check_output(["ping", "-c", "1", "-W", "1", target], stderr=subprocess.DEVNULL)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Conexão OK com {target}.")
            return True
        except subprocess.CalledProcessError:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Falha ao pingar {target}.")
    return False

def restart_network():
    """Reinicia o serviço de rede."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Reiniciando a rede...")
    os.system(RESTART_CMD)

def main():
    """Função principal para monitorar e corrigir problemas de conexão."""
    fail_count = 0

    print("Monitorando a conexão com a Internet...")
    while True:
        if is_connected(PING_TARGETS):
            fail_count = 0  # Reseta o contador de falhas
        else:
            fail_count += 1
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: Falha na conexão ({fail_count}/{MAX_RETRY}).")

        if fail_count >= MAX_RETRY:
            restart_network()
            fail_count = 0  # Reseta o contador após reiniciar a rede

        time.sleep(RETRY_INTERVAL)

if __name__ == "__main__":
    main()
