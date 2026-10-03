import argparse
import sqlite3
from database import Database, ValidationError, format_date


def ask(prompt):
    return input(prompt).strip()


def header(title):
    print('\n' + '─' * 60 + '\n' + title + '\n' + '─' * 60)


def choose(rows, label):
    """Выбор из выведенного списка, 0 означает отмену."""
    for index, row in enumerate(rows, 1):
        print(f'{index}. {label(row)}')
    if not rows:
        print('Список пуст.')
        return None
    print('0. Отмена')
    raw = ask('Номер: ')
    try:
        number = int(raw)
    except ValueError:
        raise ValidationError('Нужно ввести целое число.')
    if number == 0:
        return None
    if not 1 <= number <= len(rows):
        raise ValidationError('Нет записи с таким номером.')
    return rows[number - 1]


def show_webinars(db):
    header('РАСПИСАНИЕ ВЕБИНАРОВ')
    for item in db.webinars():
        print(f"\n[{item['category']}] {item['title']}\n"
              f"Спикер: {item['speaker']}\nКогда: {format_date(item['starts_at'])}")


def register(db):
    header('РЕГИСТРАЦИЯ НА ВЕБИНАР')
    webinar = choose(db.webinars(), lambda w: f"{w['title']} — {format_date(w['starts_at'])}")
    if webinar is None:
        return
    name, email = ask('Имя участника: '), ask('Email: ')
    registration_id = db.register(webinar['id'], name, email)
    print(f"Готово! Регистрация №{registration_id}: {name.strip()}.\n"
          f"Вебинар: {webinar['title']}\nДата: {format_date(webinar['starts_at'])}")


def show_registrations(db):
    header('ЗАРЕГИСТРИРОВАННЫЕ УЧАСТНИКИ')
    rows = db.registrations()
    if not rows:
        print('Пока никто не зарегистрирован.')
    for row in rows:
        status = 'посетил' if row['attended'] else 'не отмечен'
        print(f"\n№{row['id']}. {row['name']} <{row['email']}>\n"
              f"Вебинар: {row['title']}\nПосещение: {status}")


def attendance(db):
    header('ОТМЕТКА ПОСЕЩЕНИЯ')
    row = choose(db.registrations(), lambda r:
                 f"[{'+' if r['attended'] else ' '}] {r['name']} — {r['title']}")
    if row is None:
        return
    value = ask('1 — посетил, 0 — снять отметку, Enter — отмена: ')
    if value == '':
        return
    if value not in ('0', '1'):
        raise ValidationError('Введите 0 или 1.')
    db.set_attendance(row['id'], value == '1')
    print('Статус сохранён.')


def statistics(db):
    header('СТАТИСТИКА')
    for row in db.statistics():
        print(f"{row['title']}\n  Записались: {row['registered']}; посетили: {row['attended']}")


def main():
    parser = argparse.ArgumentParser(description='WebiList — учебная регистрация на вебинары')
    parser.add_argument('--db', help='Путь к отдельной базе SQLite (необязательно)')
    args = parser.parse_args()
    db = None
    try:
        db = Database(args.db)
        actions = {'1': show_webinars, '2': register, '3': show_registrations,
                   '4': attendance, '5': statistics}
        while True:
            header('WebiList — регистрация на вебинары')
            print('1. Показать вебинары\n2. Зарегистрироваться на вебинар\n'
                  '3. Показать зарегистрированных\n4. Отметить посещение\n'
                  '5. Статистика\n0. Выход')
            choice = ask('Выберите действие: ')
            if choice == '0':
                print('До встречи! Данные сохранены.')
                return 0
            try:
                if choice not in actions:
                    raise ValidationError('Неизвестная команда.')
                actions[choice](db)
            except ValidationError as exc:
                print(f'Ошибка: {exc}')
            except sqlite3.Error:
                print('Не удалось выполнить операцию с базой данных. Попробуйте ещё раз.')
            ask('\nНажмите Enter, чтобы продолжить...')
    except (EOFError, KeyboardInterrupt):
        print('\nРабота завершена. Завершённые операции сохранены.')
        return 0
    except (OSError, sqlite3.Error) as exc:
        print(f'Не удалось открыть базу: {exc}')
        return 1
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    raise SystemExit(main())
