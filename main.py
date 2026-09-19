import os
import sys
from datetime import date

WEBINARS = [
    {
        "id": "react-start",
        "title": "React с нуля: первый интерактивный интерфейс",
        "speaker": "Анна Орлова",
        "category": "Frontend",
        "date": date(2026, 9, 24),
        "time": "19:00",
    },
    {
        "id": "api-design",
        "title": "Проектирование API, которым приятно пользоваться",
        "speaker": "Михаил Ветров",
        "category": "Backend",
        "date": date(2026, 9, 27),
        "time": "18:30",
    },
    {
        "id": "career",
        "title": "Портфолио разработчика: что показать работодателю",
        "speaker": "Елена Смирнова",
        "category": "Карьера",
        "date": date(2026, 10, 1),
        "time": "20:00",
    },
]


registrations = []


# ---------------------------- УТИЛИТЫ ----------------------------

def clear_screen():
    """Очистить экран терминала."""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="Нажмите Enter, чтобы продолжить..."):
    """Пауза перед возвратом в меню."""
    input(f"\n{message}")


def ask(prompt):
    return input(prompt).strip()


def find_webinar(webinar_id):
    for webinar in WEBINARS:
        if webinar["id"] == webinar_id:
            return webinar
    return None


def format_webinar(webinar):
    return f"{webinar['date'].strftime('%d.%m.%Y')} в {webinar['time']}"


def is_valid_email(email):
    return "@" in email and "." in email.split("@")[-1]


def header(title):
    """Красивый заголовок раздела."""
    line = "─" * 50
    print(line)
    print(f"  {title}")
    print(line)


# ---------------------------- ЭКРАНЫ ----------------------------

def screen_webinars():
    clear_screen()
    header("БЛИЖАЙШИЕ ВЕБИНАРЫ")

    if not WEBINARS:
        print("\n  Список вебинаров пуст.")
        print("  Добавьте их в переменную WEBINARS в файле main.py.")
        pause()
        return

    for index, webinar in enumerate(WEBINARS, start=1):
        print(f"\n  {index}. [{webinar['category']}] {webinar['title']}")
        print(f"     Спикер: {webinar['speaker']}")
        print(f"     Когда:  {format_webinar(webinar)}")

    pause()


def screen_register():
    clear_screen()
    header("РЕГИСТРАЦИЯ НА ВЕБИНАР")

    if not WEBINARS:
        print("\n  Нет доступных вебинаров.")
        pause()
        return

    print("\n  Выберите вебинар:\n")
    for index, webinar in enumerate(WEBINARS, start=1):
        print(f"  {index}. {webinar['title']}")
        print(f"     {format_webinar(webinar)}")
    print("  0. Отмена")

    raw = ask("\n  Номер вебинара: ")
    if not raw.isdigit():
        print("\n  Нужно ввести число.")
        pause()
        return

    number = int(raw)
    if number == 0:
        return
    if not (1 <= number <= len(WEBINARS)):
        print("\n  Вебинара с таким номером нет.")
        pause()
        return

    webinar = WEBINARS[number - 1]

    print()
    name = ask("  Введите имя участника: ")
    email = ask("  Введите email: ").lower()

    if not name or not is_valid_email(email):
        print("\n  Регистрация не выполнена: проверьте имя и email.")
        pause()
        return

    for item in registrations:
        if item["webinar_id"] == webinar["id"] and item["email"] == email:
            print("\n  Вы уже зарегистрированы на этот вебинар с указанным email.")
            pause()
            return

    registrations.append({
        "webinar_id": webinar["id"],
        "name": name,
        "email": email,
        "attended": False,
    })

    print(f"\n  Готово! {name}, вы зарегистрированы.")
    print(f"  Вебинар: «{webinar['title']}»")
    print(f"  Дата:    {format_webinar(webinar)}")
    pause()


def screen_registrations():
    clear_screen()
    header("ЗАРЕГИСТРИРОВАННЫЕ УЧАСТНИКИ")

    if not registrations:
        print("\n  Пока никто не зарегистрирован.")
        pause()
        return

    for index, item in enumerate(registrations, start=1):
        webinar = find_webinar(item["webinar_id"])
        title = webinar["title"] if webinar else "—"
        status = "✔ посетил" if item["attended"] else "· не отмечен"
        print(f"\n  {index}. {item['name']}  <{item['email']}>")
        print(f"     Вебинар:   {title}")
        print(f"     Посещение: {status}")

    pause()


def screen_attendance():
    clear_screen()
    header("ОТМЕТКА ПОСЕЩЕНИЯ")

    if not registrations:
        print("\n  Список регистраций пуст.")
        pause()
        return

    print("\n  Выберите участника:\n")
    for index, item in enumerate(registrations, start=1):
        webinar = find_webinar(item["webinar_id"])
        title = webinar["title"] if webinar else "—"
        mark = "[✔]" if item["attended"] else "[ ]"
        print(f"  {index}. {mark} {item['name']} — {title}")
    print("  0. Отмена")

    raw = ask("\n  Номер участника: ")
    if not raw.isdigit():
        print("\n  Нужно ввести число.")
        pause()
        return

    number = int(raw)
    if number == 0:
        return
    if not (1 <= number <= len(registrations)):
        print("\n  Участника с таким номером нет.")
        pause()
        return

    item = registrations[number - 1]
    item["attended"] = not item["attended"]
    status = "посетил" if item["attended"] else "не отмечен"
    print(f"\n  Статус посещения для {item['name']}: {status}.")
    pause()


# ---------------------------- МЕНЮ ----------------------------

def screen_menu():
    clear_screen()
    header("WebiList — регистрация на вебинары")

    print(f"\n  Вебинаров в расписании: {len(WEBINARS)}")
    print(f"  Зарегистрировано:       {len(registrations)}")

    print("\n  1. Показать вебинары")
    print("  2. Зарегистрироваться на вебинар")
    print("  3. Показать зарегистрированных")
    print("  4. Отметить посещение")
    print("  0. Выход")

    return ask("\n  Выберите действие: ")


def main():
    while True:
        choice = screen_menu()

        if choice == "1":
            screen_webinars()
        elif choice == "2":
            screen_register()
        elif choice == "3":
            screen_registrations()
        elif choice == "4":
            screen_attendance()
        elif choice == "0":
            clear_screen()
            print("\n  До встречи!\n")
            sys.exit(0)
        else:
            print("\n  Неизвестная команда.")
            pause()


if __name__ == "__main__":
    main()