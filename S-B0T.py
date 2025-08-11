import discum
import json
import logging
import threading
import time
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import re
import discum.start
import os
print('S-B0T - discord self bot')
time.sleep(1)
print('frizzylow programs ( •̀ .̫ •́ )✧')
time.sleep(2)
# Настройка логирования
logger = logging.getLogger('DiscordSelfBot')
logger.setLevel(logging.INFO)

# Форматтер для логов
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Файловый обработчик (всегда активен)
file_handler = logging.FileHandler('selfbot.log', encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Консольный обработчик (изначально отключен)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler_active = False

# Глобальные переменные для управления режимами
DEBUG_MODE = False
TOKEN = ""
DISCORD_TOKEN = ""
app = Flask(__name__)
app.secret_key = 'supersecretkey'
bot_instance = None
token_file = "discord_token.txt"

# Устанавливаем уровень по умолчанию для всех логгеров
logging.basicConfig(level=logging.WARNING)


def toggle_debug_mode(enable):
    """Включает или выключает режим отладки"""
    global DEBUG_MODE, console_handler_active

    if enable == DEBUG_MODE:
        return

    DEBUG_MODE = enable

    if enable:
        # Включение отладки
        # Добавляем консольный обработчик
        if not console_handler_active:
            logger.addHandler(console_handler)
            console_handler_active = True

        # Устанавливаем низкий уровень для всех компонентов
        logger.setLevel(logging.DEBUG)
        for lib in ['werkzeug', 'flask', 'discum', 'requests', 'urllib3']:
            logging.getLogger(lib).setLevel(logging.DEBUG)

        logger.debug("Режим отладки включен")
    else:
        # Выключение отладки
        # Убираем консольный обработчик
        if console_handler_active:
            logger.removeHandler(console_handler)
            console_handler_active = False

        # Восстанавливаем стандартные уровни
        logger.setLevel(logging.INFO)
        for lib in ['werkzeug', 'flask', 'discum', 'requests', 'urllib3']:
            logging.getLogger(lib).setLevel(logging.CRITICAL)  # Изменено на CRITICAL

        # Отключаем логирование werkzeug полностью
        logging.getLogger('werkzeug').handlers = []
        logging.getLogger('werkzeug').propagate = False

        logger.info("Режим отладки выключен")


# Изначально выключаем режим отладки
toggle_debug_mode(False)


def load_token_from_file():
    """Загружает токен из файла, если он существует"""
    global TOKEN
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                TOKEN = f.read().strip()
                logger.info(f"Токен загружен из файла {token_file}")
        except Exception as e:
            logger.error(f"Ошибка загрузки токена: {e}")
    return TOKEN


def save_token_to_file(token):
    """Сохраняет токен в файл"""
    try:
        with open(token_file, 'w') as f:
            f.write(token)
        logger.info(f"Токен сохранен в файл {token_file}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения токена: {e}")
        return False


def update_token(new_token):
    """Обновляет токен и перезапускает бота"""
    global TOKEN, bot_instance

    # Останавливаем текущего бота
    if bot_instance and bot_instance.is_running:
        bot_instance.stop()

    # Сохраняем новый токен
    TOKEN = new_token
    save_token_to_file(TOKEN)

    # Пытаемся запустить бота с новым токеном
    bot_instance = DiscordSelfBot(TOKEN)
    if bot_instance.validate_token():
        if bot_instance.start():
            logger.info("Бот успешно запущен с новым токеном")
            return True
        logger.error("Ошибка запуска бота")
    else:
        logger.error("Неверный токен")
    return False


def console_command_handler():
    """Обработчик консольных команд"""
    while True:
        try:
            command = input("> ").strip().lower()

            if command == "/token":
                print("Введите токен Discord:")
                token = input().strip()
                if token:
                    if update_token(token):
                        print("✓ Токен успешно обновлен и бот запущен! http://127.0.0.1:5000/")
                    else:
                        print("✗ Ошибка: неверный токен или проблема с запуском")
                else:
                    print("✗ Отмена: пустой токен")

            elif command == "/file":
                print("Введите путь к файлу с токеном:")
                file_path = input().strip()
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            token = f.read().strip()
                        if token:
                            if update_token(token):
                                print("✓ Токен успешно загружен из файла и бот запущен!")
                            else:
                                print("✗ Ошибка: неверный токен или проблема с запуском")
                        else:
                            print("✗ Файл пуст")
                    except Exception as e:
                        print(f"✗ Ошибка чтения файла: {e}")
                else:
                    print("✗ Файл не существует")

            elif command == "/start":
                global bot_instance
                if not bot_instance or not bot_instance.is_running:
                    if TOKEN:
                        bot_instance = DiscordSelfBot(TOKEN)
                        if bot_instance.start():
                            print("✓ Бот успешно запущен!")
                        else:
                            print("✗ Ошибка запуска бота")
                    else:
                        print("✗ Токен не установлен. Используйте /token или /file")
                else:
                    print("✗ Бот уже запущен")

            elif command == "/stop":
                if bot_instance and bot_instance.is_running:
                    bot_instance.stop()
                    bot_instance = None
                    print("✓ Бот остановлен")
                else:
                    print("✗ Бот не запущен")

            elif command == "/status":
                if bot_instance and bot_instance.is_running:
                    status = bot_instance.get_status()
                    print("\nТекущий статус бота:")
                    print(f"• Статус: {status['status']}")
                    print(f"• Сообщений: {status['message_count']}")
                    print(f"• Друзей: {status['friend_count']}")
                    print(f"• Время работы: {status['uptime']}")
                else:
                    print("✗ Бот не запущен")

            elif command == "/debug on":
                toggle_debug_mode(True)
                print("✓ Режим отладки ВКЛЮЧЕН")

            elif command == "/debug off":
                toggle_debug_mode(False)
                print("✓ Режим отладки ВЫКЛЮЧЕН")

            elif command == "/debug status":
                print(f"Режим отладки: {'ВКЛЮЧЕН' if DEBUG_MODE else 'ВЫКЛЮЧЕН'}")

            elif command == "/help":
                print("\nДоступные команды:")
                print("/start      - запустить бота")
                print("/stop       - остановить бота")
                print("/token      - ввести новый токен")
                print("/file       - загрузить токен из файла")
                print("/status     - показать статус бота")
                print("/debug on   - включить режим отладки")
                print("/debug off  - выключить режим отладки")
                print("/debug status - показать состояние режима отладки")
                print("/help       - показать эту справку")
                print('------------------------------------------------')
                print('Ссылка панели управления: http://127.0.0.1:5000/')

            else:
                print("✗ Неизвестная команда. Введите /help для списка команд")

        except Exception as e:
            print(f"✗ Ошибка обработки команды: {e}")

# Запускаем обработчик команд в отдельном потоке
threading.Thread(target=console_command_handler, daemon=True).start()

# Загружаем токен при старте программы
load_token_from_file()


class DiscordSelfBot:
    def __init__(self, token):
        self.token = token or DISCORD_TOKEN
        self.bot = None
        self.user_data = {}
        self.friends = []
        self.blocked = []
        self.guilds = []
        self.dm_channels = []
        self.active_conversation = None
        self.conversation_history = {}
        self.is_running = False
        self.gateway_thread = None
        self.message_count = 0
        self.start_time = datetime.now()
        self.status = "online"
        self.friends_updated = False
        self.requests_updated = False
        self.dms_updated = False
        self.guilds_updated = False

        # Настройки автоответчика
        self.auto_responder_settings = {
            'enabled': False,
            'mode': 'simple',
            'simple': {
                'message': 'Привет! Я сейчас занят, отвечу позже.',
                'delay': 60
            },
            'ai': {
                'api_key': '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',
                'system_prompt': 'Ты обычный пользователь Discord. Твоя задача вести себя как реальный человек, общающийся в Discord-чате. Не упоминай, что ты — искусственный интеллект или бот. Используй естественный стиль общения, делай небольшие ошибки, выражай эмоции и личные мнения. Отвечай коротко или подробно в зависимости от ситуации, избегай формальных или технических объяснений. Не раскрывай свою природу и не говори о своих возможностях или ограничениях. Веди диалог так, как бы это делал обычный пользователь Discord. Не используй слишком много смайликов или приставвку (а) и подобные если ты не знаешь какой у него пол. Не зацикливайся на старых сообщениях или тексте не упоминай предыдущеии сообщения следуй только новому тексту/сообщение, про старые забудь. Отвечай только на новые! Не используй смайлики максимум одно на сообщение и то только 20 процентов на то что они будут в сообщение. не используй термины и знаки применания пиши допускай изредка ошибки максимум один два знака на сообщение и без смайликов очень редко. Не используй знки препинание пиши бекз них!! Твой ник: menkun. Можешь использовать маты и все такое пиши понятныек, если тебя обызывают обзывай в ответ. предложение не кринжовые.',
                'model': '@preset/deepseek'
            }
        }
        self.friend_requests = []  # Входящие заявки
        self.friend_request_settings = {
            'auto_accept': False,
            'auto_reject': False
        }
        # Отслеживание активности
        self.last_activity = {}
        self.response_timers = {}

    def validate_token(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self.user_data = response.json()
                return True
            return False
        except Exception:
            return False

    def fetch_all_data(self):
        self.fetch_friends()
        self.fetch_blocked()
        self.fetch_guilds()
        self.fetch_dm_channels()
        self.fetch_friend_requests()  # Добавлено получение заявок

    def get_status(self):
        """Возвращает текущий статус бота"""
        status = "Online" if self.is_running else "Offline"

        # Вычисляем время работы
        uptime = "00:00:00"
        if self.is_running:
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        return {
            "status": status,
            "message_count": self.message_count,
            "friend_count": len(self.friends),
            "uptime": uptime
        }

    def fetch_friend_requests(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me/relationships",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                relationships = response.json()
                self.friend_requests = [user for user in relationships if user['type'] == 3]  # type=3 - входящие заявки
        except Exception as e:
            logger.error(f"Error fetching friend requests: {e}")
        self.requests_updated = True
    def accept_friend_request(self, user_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.put(
                f"https://discord.com/api/v9/users/@me/relationships/{user_id}",
                headers=headers,
                json={"type": 1},  # type=1 - друзья
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_friend_requests()
                self.fetch_friends()
                return True
            return False
        except Exception:
            return False

    def reject_friend_request(self, user_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.delete(
                f"https://discord.com/api/v9/users/@me/relationships/{user_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_friend_requests()
                return True
            return False
        except Exception:
            return False

    def set_friend_request_auto_settings(self, auto_accept, auto_reject):
        self.friend_request_settings['auto_accept'] = auto_accept
        self.friend_request_settings['auto_reject'] = auto_reject
    def fetch_friends(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me/relationships",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                friends_data = response.json()
                self.friends = [user['user'] for user in friends_data if user['type'] == 1]
        except Exception as e:
            logger.error(f"Error fetching friends: {e}")
        self.friends_updated = True
    def fetch_blocked(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me/relationships",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                relationships = response.json()
                self.blocked = [user['user'] for user in relationships if user['type'] == 2]
        except Exception as e:
            logger.error(f"Error fetching blocked users: {e}")

    def fetch_guilds(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me/guilds",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self.guilds = response.json()
        except Exception as e:
            logger.error(f"Error fetching guilds: {e}")
        self.guilds_updated = True
    def fetch_dm_channels(self):
        try:
            headers = {"Authorization": self.token}
            response = requests.get(
                "https://discord.com/api/v9/users/@me/channels",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self.dm_channels = response.json()
                # Preload conversation history for each DM
                for channel in self.dm_channels:
                    if channel['type'] == 1:  # DM channel
                        self.get_conversation_history(channel['id'])
        except Exception as e:
            logger.error(f"Error fetching DM channels: {e}")


    def get_conversation_history(self, channel_id, limit=50):
        try:
            if channel_id not in self.conversation_history:
                self.conversation_history[channel_id] = []

            headers = {"Authorization": self.token}
            params = {"limit": limit}
            if self.conversation_history[channel_id]:
                params["before"] = self.conversation_history[channel_id][-1]['id']

            response = requests.get(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                new_messages = response.json()
                # Filter out existing messages
                existing_ids = {msg['id'] for msg in self.conversation_history[channel_id]}
                new_messages = [msg for msg in new_messages if msg['id'] not in existing_ids]

                # Add to history and sort by timestamp
                self.conversation_history[channel_id].extend(new_messages)
                self.conversation_history[channel_id].sort(key=lambda x: x['timestamp'])

                return new_messages
            return []
        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return []

    def start(self):
        if not self.validate_token():
            return False
        try:
            self.bot = discum.Client(token=self.token, log=False)
            self.fetch_all_data()
            self.is_running = True
            self.start_time = datetime.now()

            @self.bot.gateway.command
            def on_event(resp):
                try:
                    if resp.event.ready_supplemental:
                        logger.info("Connected to Discord!")

                    if resp.event.message:
                        self.handle_message(resp.parsed.auto())

                    # Обработка событий отношений
                    if resp.event.ready:
                        self.fetch_friends()
                        self.fetch_blocked()

                    # Обработка выхода с сервера
                    if resp.event.guild_deleted:
                        self.fetch_guilds()

                    if resp.event.relationship_add:
                        request_data = resp.parsed.auto()
                        if request_data.get('type') == 3:  # Входящая заявка
                            bot_instance.fetch_friend_requests()
                            # Авто-обработка если включена
                            if bot_instance.friend_request_settings['auto_accept']:
                                bot_instance.accept_friend_request(request_data['id'])
                            elif bot_instance.friend_request_settings['auto_reject']:
                                bot_instance.reject_friend_request(request_data['id'])

                                # Обработка изменений в друзьях

                                # Обработка изменений в друзьях
                                if resp.event.relationship_add or resp.event.relationship_remove:
                                    self.fetch_friends()
                                    self.fetch_blocked()
                                    self.fetch_friend_requests()

                                # Обработка изменений в чатах
                                if resp.event.message or resp.event.channel_create or resp.event.channel_delete:
                                    self.fetch_dm_channels()

                                # Обработка изменений на серверах
                                if resp.event.guild_create or resp.event.guild_delete:
                                    self.fetch_guilds()

                except Exception as e:
                    logger.error(f"Event handler error: {e}", exc_info=True)

            self.gateway_thread = threading.Thread(target=self.bot.gateway.run, kwargs={"auto_reconnect": True})
            self.gateway_thread.daemon = True
            self.gateway_thread.start()
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Start error: {e}")
            return False

    def handle_message(self, message):
        try:
            # Skip own messages
            author = message.get('author', {})
            if author.get('id') == self.user_data.get('id'):
                return

            self.message_count += 1
            channel_id = message['channel_id']
            author_id = author.get('id')
            current_time = time.time()

            # Обновляем время последней активности
            self.last_activity[author_id] = current_time

            # Add message to conversation history
            if channel_id in self.conversation_history:
                if not any(msg['id'] == message['id'] for msg in self.conversation_history[channel_id]):
                    self.conversation_history[channel_id].append(message)
                    if len(self.conversation_history[channel_id]) > 200:
                        self.conversation_history[channel_id] = self.conversation_history[channel_id][-100:]

            # Проверяем автоответчик
            if self.auto_responder_settings['enabled']:
                # Проверяем что это DM
                if any(ch for ch in self.dm_channels if ch['id'] == channel_id and ch['type'] == 1):
                    logger.info(f"Auto-responder triggered by {author.get('username')}")

                    # Отменяем предыдущий таймер для этого пользователя
                    if author_id in self.response_timers:
                        self.response_timers[author_id].cancel()

                    if self.auto_responder_settings['mode'] == 'simple':
                        delay = self.auto_responder_settings['simple']['delay']
                        if delay > 0:
                            timer = threading.Timer(
                                delay,
                                self._send_delayed_response,
                                [channel_id, author_id]
                            )
                            timer.start()
                            self.response_timers[author_id] = timer
                            logger.info(f"Scheduled response in {delay} seconds for {author.get('username')}")
                        else:
                            self.send_message(
                                channel_id,
                                self.auto_responder_settings['simple']['message']
                            )
                            logger.info(f"Sent immediate response to {author.get('username')}")

                    elif self.auto_responder_settings['mode'] == 'ai':
                        threading.Thread(
                            target=self._send_ai_response,
                            args=(channel_id, message)
                        ).start()

        except Exception as e:
            logger.error(f"Auto-responder error: {e}")

    def _send_delayed_response(self, channel_id, author_id):
        """Отправляет отложенный ответ если не было активности"""
        try:
            current_time = time.time()
            last_active = self.last_activity.get(author_id, 0)

            if current_time - last_active < self.auto_responder_settings['simple']['delay']:
                logger.info(f"User was active, skipping response to {author_id}")
                return

            self.send_message(
                channel_id,
                self.auto_responder_settings['simple']['message']
            )
            logger.info(f"Sent delayed response to {author_id}")

        except Exception as e:
            logger.error(f"Delayed response error: {e}")
        finally:
            if author_id in self.response_timers:
                del self.response_timers[author_id]

    def _send_ai_response(self, channel_id, message):
        """Генерирует ответ через OpenRouter API только на последнее сообщение"""
        try:
            user_message = message.get('content', '')
            author_id = message.get('author', {}).get('id')

            if author_id == self.user_data.get('id'):
                return

            # Форматируем сообщения для OpenRouter
            formatted_messages = []

            # Добавляем системный промпт
            system_prompt = self.auto_responder_settings['ai']['system_prompt']
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            # Добавляем ТОЛЬКО последнее сообщение пользователя
            formatted_messages.append({
                "role": "user",
                "content": user_message
            })

            # Конфигурация запроса к OpenRouter
            api_key = self.auto_responder_settings['ai']['api_key']
            model = self.auto_responder_settings['ai']['model']
            url = "https://openrouter.ai/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": 512,
                "temperature": 0.7
            }

            if model == "@preset/deepseek":
                payload = {
                    "model": model,
                    "messages": formatted_messages,
                    "max_tokens": 512,
                    "temperature": 0.7,
                    "transforms": ["middle-out"]
                }

            # Отправляем запрос к API
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
                return

            # Обрабатываем ответ
            response_data = response.json()
            ai_response = response_data['choices'][0]['message']['content'].strip()

            if ai_response:
                self.send_message(channel_id, ai_response)
                logger.info(f"AI response sent to {message.get('author', {}).get('username')}")
                logger.info(f"User message: {user_message[:50]}...")
                logger.info(f"AI response: {ai_response[:50]}...")
            else:
                logger.warning("Empty response from OpenRouter API")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request error: {e}")
        except Exception as e:
            logger.error(f"AI response error: {e}")

    def send_message(self, channel_id, message):
        try:
            response = self.bot.sendMessage(channel_id, message)
            return response.status_code == 200
        except Exception:
            return False

    def remove_friend(self, user_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.delete(
                f"https://discord.com/api/v9/users/@me/relationships/{user_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_friends()
                return True
            return False
        except Exception:
            return False

    def block_user(self, user_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.put(
                f"https://discord.com/api/v9/users/@me/relationships/{user_id}",
                headers=headers,
                json={"type": 2},
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_blocked()
                return True
            return False
        except Exception:
            return False

    def unblock_user(self, user_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.delete(
                f"https://discord.com/api/v9/users/@me/relationships/{user_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_blocked()
                return True
            return False
        except Exception:
            return False

    def add_friend(self, username, discriminator):
        try:
            headers = {"Authorization": self.token, "Content-Type": "application/json"}
            payload = {"username": username, "discriminator": discriminator}
            response = requests.post(
                "https://discord.com/api/v9/users/@me/relationships",
                headers=headers,
                json=payload,
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_friends()
                return True
            return False
        except Exception:
            return False

    def leave_guild(self, guild_id):
        try:
            headers = {"Authorization": self.token}
            response = requests.delete(
                f"https://discord.com/api/v9/users/@me/guilds/{guild_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 204:
                self.fetch_guilds()
                return True
            return False
        except Exception:
            return False

    def set_status(self, status):
        try:
            headers = {"Authorization": self.token, "Content-Type": "application/json"}
            payload = {"status": status}
            response = requests.patch(
                "https://discord.com/api/v9/users/@me/settings",
                headers=headers,
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                self.status = status
                return True
            return False
        except Exception:
            return False

    def create_dm(self, user_id):
        try:
            response = self.bot.createDM([user_id]).json()
            if 'id' in response:
                channel_id = response['id']
                self.dm_channels.append({
                    'id': channel_id,
                    'type': 1,
                    'recipients': [{
                        'id': user_id,
                        'username': next((f['username'] for f in self.friends if f['id'] == user_id), "Unknown")
                    }]
                })
                if channel_id not in self.conversation_history:
                    self.conversation_history[channel_id] = []
                return channel_id
            return None
        except Exception:
            return None

    def send_to_all_friends(self, message):
        results = []
        for friend in self.friends:
            channel_id = next((c['id'] for c in self.dm_channels
                               if any(r['id'] == friend['id'] for r in c.get('recipients', []))), None)

            if not channel_id:
                channel_id = self.create_dm(friend['id'])

            if channel_id:
                success = self.send_message(channel_id, message)
                results.append({
                    "user_id": friend['id'],
                    "username": friend['username'],
                    "success": success
                })
        return results

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self.bot and hasattr(self.bot, 'gateway'):
                try:
                    self.bot.gateway.close()
                    if self.gateway_thread:
                        self.gateway_thread.join(timeout=2.0)
                except Exception as e:
                    logger.error(f"Stop error: {e}")


@app.route('/')
def index():
    return render_template('index.html', bot=bot_instance)


# Добавьте в Flask роуты
@app.route('/api/has_updates')
def api_has_updates():
    if not bot_instance or not bot_instance.is_running:
        return jsonify(has_updates=False)

    return jsonify({
        'friends': bot_instance.friends_updated,
        'friend_requests': bot_instance.requests_updated,
        'dm_channels': bot_instance.dms_updated,
        'guilds': bot_instance.guilds_updated
    })
@app.route('/start', methods=['POST'])
def start_bot():
    global bot_instance
    if not bot_instance or not bot_instance.is_running:
        bot_instance = DiscordSelfBot(TOKEN)
        if bot_instance.start():
            return jsonify(success=True, message="Bot started successfully!")
        return jsonify(success=False, message="Failed to start bot")
    return jsonify(success=False, message="Bot is already running")


@app.route('/stop', methods=['POST'])
def stop_bot():
    if bot_instance and bot_instance.is_running:
        bot_instance.stop()
        return jsonify(success=True, message="Bot stopped")
    return jsonify(success=False, message="Bot not running")


@app.route('/api/friends')
def api_friends():
    if bot_instance and bot_instance.is_running:
        return jsonify({
            "friends": bot_instance.friends,
            "blocked": bot_instance.blocked
        })
    return jsonify({"friends": [], "blocked": []})


@app.route('/api/guilds')
def api_guilds():
    if bot_instance and bot_instance.is_running:
        return jsonify(bot_instance.guilds)
    return jsonify([])


@app.route('/api/dm_channels')
def api_dm_channels():
    if bot_instance and bot_instance.is_running:
        return jsonify(bot_instance.dm_channels)
    return jsonify([])


@app.route('/api/conversation/<channel_id>')
def api_conversation(channel_id):
    if bot_instance and bot_instance.is_running:
        bot_instance.active_conversation = channel_id
        session['active_conversation'] = channel_id

        messages = bot_instance.conversation_history.get(channel_id, [])
        formatted_messages = []
        for msg in messages:
            author = msg.get('author', {})
            formatted_messages.append({
                'id': msg['id'],
                'author': f"{author.get('username', 'Unknown')}#{author.get('discriminator', '0000')}",
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp', ''),
                'is_self': author.get('id') == bot_instance.user_data.get('id')
            })
        return jsonify(messages=formatted_messages)
    return jsonify(messages=[])


@app.route('/api/new_messages/<channel_id>')
def get_new_messages(channel_id):
    if bot_instance and bot_instance.is_running:
        last_id = request.args.get('last_id', '0')
        try:
            last_id = int(last_id)
        except:
            last_id = 0

        if channel_id not in bot_instance.conversation_history:
            return jsonify([])

        new_messages = []
        for msg in bot_instance.conversation_history[channel_id]:
            try:
                msg_id = int(msg['id'])
            except:
                continue
            if msg_id > last_id:
                author = msg.get('author', {})
                new_messages.append({
                    'id': msg['id'],
                    'author': f"{author.get('username', 'Unknown')}#{author.get('discriminator', '0000')}",
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp', ''),
                    'is_self': author.get('id') == bot_instance.user_data.get('id')
                })

        return jsonify(new_messages)
    return jsonify([])


@app.route('/send_message', methods=['POST'])
def send_message():
    if bot_instance and bot_instance.is_running:
        channel_id = request.form['channel_id']
        message = request.form['message']
        if bot_instance.send_message(channel_id, message):
            new_message = {
                'id': f"temp_{int(time.time() * 1000)}",
                'content': message,
                'author': {
                    'id': bot_instance.user_data['id'],
                    'username': bot_instance.user_data['username'],
                    'discriminator': bot_instance.user_data['discriminator']
                },
                'timestamp': datetime.utcnow().isoformat(),
                'channel_id': channel_id
            }
            if channel_id in bot_instance.conversation_history:
                bot_instance.conversation_history[channel_id].append(new_message)
            return jsonify(success=True, message=new_message)
    return jsonify(success=False)


@app.route('/api/auto_responder_settings')
def api_auto_responder_settings():
    if bot_instance and bot_instance.is_running:
        return jsonify(bot_instance.auto_responder_settings)
    return jsonify({})


@app.route('/save_auto_responder_settings', methods=['POST'])
def save_auto_responder_settings():
    if bot_instance and bot_instance.is_running:
        data = request.json
        bot_instance.auto_responder_settings = {
            'enabled': data.get('enabled', False),
            'mode': data.get('mode', 'simple'),
            'simple': {
                'message': data.get('simple_message', ''),
                'delay': int(data.get('simple_delay', 60))
            },
            'ai': {
                'api_key': data.get('ai_api_key', ''),
                'system_prompt': data.get('ai_system_prompt', ''),
                'model': data.get('ai_model', '@preset/deepseek')
            }
        }
        return jsonify(success=True)
    return jsonify(success=False)


@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        if bot_instance.remove_friend(user_id):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/block_user', methods=['POST'])
def block_user():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        if bot_instance.block_user(user_id):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/unblock_user', methods=['POST'])
def unblock_user():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        if bot_instance.unblock_user(user_id):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/add_friend', methods=['POST'])
def add_friend():
    if bot_instance and bot_instance.is_running:
        username = request.form['username']
        discriminator = request.form['discriminator']
        if bot_instance.add_friend(username, discriminator):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/create_dm', methods=['POST'])
def create_dm():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        channel_id = bot_instance.create_dm(user_id)
        if channel_id:
            return jsonify(success=True, channel_id=channel_id)
    return jsonify(success=False)


@app.route('/leave_guild', methods=['POST'])
def leave_guild():
    if bot_instance and bot_instance.is_running:
        guild_id = request.form['guild_id']
        if bot_instance.leave_guild(guild_id):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/set_status', methods=['POST'])
def set_status():
    if bot_instance and bot_instance.is_running:
        status = request.form['status']
        if bot_instance.set_status(status):
            return jsonify(success=True)
    return jsonify(success=False)


@app.route('/save_token', methods=['POST'])
def save_token():
    global DISCORD_TOKEN, bot_instance

    data = request.json
    new_token = data.get('token', '').strip()

    if not new_token:
        return jsonify(success=False, message="Пустой токен")

    if bot_instance and bot_instance.is_running:
        bot_instance.stop()
        bot_instance = None

    DISCORD_TOKEN = new_token
    temp_bot = DiscordSelfBot(DISCORD_TOKEN)
    if temp_bot.validate_token():
        bot_instance = temp_bot
        if bot_instance.start():
            return jsonify(success=True, message="Токен сохранен и бот запущен!")
        return jsonify(success=False, message="Ошибка запуска бота")
    return jsonify(success=False, message="Неверный токен")


@app.route('/api/current_token')
def api_current_token():
    return jsonify(token=DISCORD_TOKEN if DISCORD_TOKEN else "")


@app.route('/send_to_all', methods=['POST'])
def send_to_all():
    if bot_instance and bot_instance.is_running:
        message = request.form['message']
        results = bot_instance.send_to_all_friends(message)
        return jsonify(success=True, results=results)
    return jsonify(success=False)


@app.route('/api/status')
def api_status():
    if bot_instance:
        status_data = bot_instance.get_status()
        return jsonify(status_data)
    return jsonify({
        "status": "Offline",
        "message_count": 0,
        "friend_count": 0,
        "uptime": "00:00:00"
    })

@app.route('/api/friend_requests')
def api_friend_requests():
    if bot_instance and bot_instance.is_running:
        return jsonify(bot_instance.friend_requests)
    return jsonify([])

@app.route('/api/accept_friend_request', methods=['POST'])
def api_accept_friend_request():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        if bot_instance.accept_friend_request(user_id):
            return jsonify(success=True)
    return jsonify(success=False)

@app.route('/api/reject_friend_request', methods=['POST'])
def api_reject_friend_request():
    if bot_instance and bot_instance.is_running:
        user_id = request.form['user_id']
        if bot_instance.reject_friend_request(user_id):
            return jsonify(success=True)
    return jsonify(success=False)

@app.route('/api/set_friend_request_auto_settings', methods=['POST'])
def api_set_friend_request_auto_settings():
    if bot_instance and bot_instance.is_running:
        auto_accept = request.form.get('auto_accept', 'false') == 'true'
        auto_reject = request.form.get('auto_reject', 'false') == 'true'
        bot_instance.set_friend_request_auto_settings(auto_accept, auto_reject)
        return jsonify(success=True)
    return jsonify(success=False)

@app.route('/api/friend_request_settings')
def api_friend_request_settings():
    if bot_instance and bot_instance.is_running:
        return jsonify(bot_instance.friend_request_settings)
    return jsonify({'auto_accept': False, 'auto_reject': False})


# Добавьте в Flask роуты
@app.route('/api/reset_updates', methods=['POST'])
def api_reset_updates():
    if not bot_instance or not bot_instance.is_running:
        return jsonify(success=False)

    data = request.json
    if 'friends' in data:
        bot_instance.friends_updated = False
    if 'friend_requests' in data:
        bot_instance.requests_updated = False
    if 'dm_channels' in data:
        bot_instance.dms_updated = False
    if 'guilds' in data:
        bot_instance.guilds_updated = False

    return jsonify(success=True)


if __name__ == "__main__":
    # Отключаем логирование Flask по умолчанию
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True
    print('Flask запущен! Панель управление доступна. /help - справка')
    # Запускаем Flask без режима отладки
    app.run(debug=False, use_reloader=False)
