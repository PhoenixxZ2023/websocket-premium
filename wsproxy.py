#!/usr/bin/env python
# encoding: utf-8
import asyncio
import getopt
import hashlib
import socket
import ssl
import sys
import websockets

PASS = ''
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = 80
SSH_PORT = 22  # Default SSH port
BUFLEN = 4096 * 4
TIMEOUT = 60
MSG = ''
COR = '<font color="null">'
FTAG = '</font>'
DEFAULT_HOST = "127.0.0.1"
RESPONSE = (
    "HTTP/1.1 101 Switching Protocols\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n\r\n"
)

def hash_password(password):
    # You can use a better hashing algorithm (e.g., bcrypt) for stronger security
    return hashlib.sha256(password.encode()).hexdigest()

class Server:
    def __init__(self, host, port, ssh_port):
        self.host = host
        self.port = port
        self.ssh_port = ssh_port
        self.threads = []
        self.threadsLock = asyncio.Lock()
        self.logLock = asyncio.Lock()

    async def handle_connection(self, websocket, path):
        try:
            client_buffer = await websocket.recv()
            host_port = self.find_header(client_buffer, 'X-Real-Host')

            if not host_port:
                host_port = DEFAULT_HOST

            split = self.find_header(client_buffer, 'X-Split')

            if split:
                await websocket.recv(BUFLEN)

            if host_port:
                passwd = self.find_header(client_buffer, 'X-Pass')

                if len(PASS) != 0 and passwd == PASS:
                    await self.method_CONNECT(host_port, websocket)
                elif len(PASS) != 0 and passwd != PASS:
                    await websocket.send('HTTP/1.1 400 WrongPass!\r\n\r\n')
                elif host_port.startswith('127.0.0.1') or host_port.startswith('localhost'):
                    await self.method_CONNECT(host_port, websocket)
                else:
                    await websocket.send('HTTP/1.1 403 Forbidden!\r\n\r\n')
            else:
                print('- No X-Real-Host!')
                await websocket.send('HTTP/1.1 400 NoXRealHost!\r\n\r\n')
        except Exception as e:
            print("Error:", e)
        finally:
            await websocket.close()

    async def method_CONNECT(self, path, websocket):
        print('CONNECT', path)
        target = await self.connect_target(path)
        await websocket.send(RESPONSE)

        try:
            while True:
                data = await websocket.recv()
                if data:
                    await target.send(data)
        except:
            pass
        finally:
            target.close()

    async def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i + 1:])
            host = host[:i]
        else:
            if host.startswith('wss'):
                port = 443
            else:
                port = 80

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        target = await websockets.connect(f"{host}:{port}", ssl=context)
        return target

    @staticmethod
    def find_header(head, header):
        aux = head.find(header + ': ')

        if aux == -1:
            return ''

        aux = head.find(':', aux)
        head = head[aux + 2:]
        aux = head.find('\r\n')

        if aux == -1:
            return ''

        return head[:aux]

def print_usage():
    print('Use: proxy.py -p <port>')
    print('       proxy.py -b <ip> -p <porta>')
    print('       proxy.py -b 0.0.0.0 -p 22')

def parse_args(argv):
    global LISTENING_ADDR
    global LISTENING_PORT
    global SSH_PORT
    
    try:
        opts, args = getopt.getopt(argv, "hb:p:s:", ["bind=", "port=", "sshport="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit()
        elif opt in ("-b", "--bind"):
            LISTENING_ADDR = arg
        elif opt in ("-p", "--port"):
            LISTENING_PORT = int(arg)
        elif opt in ("-s", "--sshport"):
            SSH_PORT = int(arg)

def print_menu():
    print("1. Habilitar Proxy WebSocket")
    print("2. Desabilitar Proxy WebSocket")
    print("3. Configurar senha do Proxy WebSocket")
    print("4. Sair")

def main_menu(server):
    while True:
        print_menu()
        choice = input("Digite sua escolha: ")

        if choice == "1":
            asyncio.get_event_loop().run_until_complete(start_server)
            print("Proxy WebSocket habilitado.")
        elif choice == "2":
            print("Desabilitando Proxy WebSocket.")
            server.close()
            break
        elif choice == "3":
            global PASS
            new_pass = input("Digite a nova senha: ")
            PASS = hash_password(new_pass)
            print("Senha do Proxy WebSocket configurada com sucesso.")
        elif choice == "4":
            print("Saindo do programa.")
            server.close()
            break
        else:
            print("Escolha inválida. Por favor, tente novamente.")

if __name__ == '__main__':
    parse_args(sys.argv[1:])
    server = Server(LISTENING_ADDR, LISTENING_PORT, SSH_PORT)
    start_server = websockets.serve(server.handle_connection, LISTENING_ADDR, LISTENING_PORT)

    main_menu(server)
