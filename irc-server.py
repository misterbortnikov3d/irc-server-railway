import asyncio
import re

class IRCServer:
    def __init__(self, host='127.0.0.1', port=6667):
        self.host = host
        self.port = port
        self.clients = {}  # {writer: nickname}
        self.channels = {'#general': set()}  # {channel: {writer}}

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Клиент подключился: {addr}")

        try:
            # Ожидание NICK и USER
            nickname = None
            while True:
                data = await reader.readline()
                if not data:
                    break
                line = data.decode().strip()
                print(f"Получено: {line}")

                if line.startswith('NICK '):
                    nickname = line.split(' ', 1)[1]
                    self.clients[writer] = nickname
                    self.channels['#general'].add(writer)
                    self.send(writer, f":server 001 {nickname} :Welcome to the IRC server!")
                    self.send_channel('#general', f":{nickname}! JOIN #general")
                elif line.startswith('USER '):
                    pass  # Игнорируем для простоты
                elif nickname:
                    break

            if not nickname:
                return

            # Основной цикл обработки команд
            while True:
                data = await reader.readline()
                if not data:
                    break
                line = data.decode().strip()
                print(f"{nickname}: {line}")

                if line.startswith('JOIN '):
                    channel = line.split(' ', 1)[1]
                    if channel not in self.channels:
                        self.channels[channel] = set()
                    self.channels[channel].add(writer)
                    self.send_channel(channel, f":{nickname}! JOIN {channel}")
                elif line.startswith('PRIVMSG '):
                    parts = re.split(r' +', line, 2)
                    if len(parts) >= 3:
                        target, msg = parts[1], parts[2].lstrip(':')
                        if target.startswith('#'):
                            self.send_channel(target, f":{nickname} PRIVMSG {target} :{msg}")
                        else:
                            # ЛС (упрощённо)
                            for w, n in self.clients.items():
                                if n == target:
                                    self.send(w, f":{nickname} PRIVMSG {target} :{msg}")
                elif line == 'QUIT':
                    break

        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            if writer in self.clients:
                nickname = self.clients[writer]
                for channel in self.channels.values():
                    channel.discard(writer)
                self.send_channel('#general', f":{nickname}! QUIT :Client left")
                del self.clients[writer]
            writer.close()

    def send(self, writer, message):
        writer.write((message + '\r\n').encode())

    def send_channel(self, channel, message):
        if channel in self.channels:
            for writer in self.channels[channel]:
                self.send(writer, message)

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        print(f"Сервер запущен на {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

# Запуск
if __name__ == '__main__':
    server = IRCServer('0.0.0.0', 6667)
    asyncio.run(server.start())
