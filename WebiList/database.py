import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOSCOW = timezone(timedelta(hours=3))
WEBINARS = [
    ('react-start', 'React с нуля: первый интерактивный интерфейс',
     'Анна Орлова', 'Frontend', '2026-09-24 16:00:00'),
    ('api-design', 'Проектирование API, которым приятно пользоваться',
     'Михаил Ветров', 'Backend', '2026-09-27 15:30:00'),
    ('career', 'Портфолио разработчика: что показать работодателю',
     'Елена Смирнова', 'Карьера', '2026-10-01 17:00:00'),
]


class ValidationError(ValueError):
    """Ошибка ввода, которую можно показать пользователю."""


class Database:
    def __init__(self, path=None):
        path = Path(path) if path is not None else ROOT / 'data' / 'webinars.db'
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys = ON')
        try:
            if not self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='participants'"
            ).fetchone():
                self.connection.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
            self.seed()
        except Exception:
            self.connection.close()
            raise

    def close(self):
        self.connection.close()

    def seed(self):
        """Начальные данные добавляются один раз; существующие записи сохраняются."""
        with self.connection:
            for key, title, speaker, category, starts_at in WEBINARS:
                if self.connection.execute('SELECT 1 FROM webinars WHERE id=?', (key,)).fetchone():
                    continue
                # Имена спикеров не являются уникальными ключами в предметной области.
                speaker_id = self.connection.execute(
                    'INSERT INTO speakers(name) VALUES (?)', (speaker,)
                ).lastrowid
                self.connection.execute('INSERT OR IGNORE INTO categories(name) VALUES (?)', (category,))
                category_id = self.connection.execute(
                    'SELECT id FROM categories WHERE name=?', (category,)
                ).fetchone()['id']
                self.connection.execute('INSERT INTO webinars VALUES (?, ?, ?, ?, ?)',
                                        (key, title, speaker_id, category_id, starts_at))

    def webinars(self):
        return self.connection.execute('''
            SELECT w.*, s.name AS speaker, c.name AS category
            FROM webinars w JOIN speakers s ON s.id=w.speaker_id
            JOIN categories c ON c.id=w.category_id ORDER BY w.starts_at, w.id
        ''').fetchall()

    def register(self, webinar_id, name, email):
        name, email = name.strip(), email.strip().lower()
        if not 1 <= len(name) <= 120 or any(ord(c) < 32 for c in name):
            raise ValidationError('Имя должно содержать от 1 до 120 символов без управляющих знаков.')
        # Учебная форма поддерживает обычные ASCII-адреса; это не проверка существования почты.
        if (len(email) > 254 or not email.isascii() or
                not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", email)):
            raise ValidationError('Укажите корректный email, например name@example.com.')
        local = email.split('@')[0]
        if len(local) > 64 or local.startswith('.') or local.endswith('.') or '..' in local:
            raise ValidationError('Некорректная часть email до знака @.')
        try:
            # Блокировка записи до чтения предотвращает гонку поиска и создания участника.
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                if not self.connection.execute('SELECT 1 FROM webinars WHERE id=?', (webinar_id,)).fetchone():
                    raise ValidationError('Вебинар не найден.')
                participant = self.connection.execute(
                    'SELECT id, name FROM participants WHERE email=?', (email,)
                ).fetchone()
                if participant:
                    participant_id = participant['id']
                    if self.connection.execute(
                        'SELECT 1 FROM registrations WHERE participant_id=? AND webinar_id=?',
                        (participant_id, webinar_id)
                    ).fetchone():
                        raise ValidationError('Этот email уже зарегистрирован на выбранный вебинар.')
                    if participant['name'] != name:
                        raise ValidationError('Этот email уже связан с другим именем. Укажите прежнее имя.')
                else:
                    participant_id = self.connection.execute(
                        'INSERT INTO participants(name,email) VALUES (?,?)', (name, email)
                    ).lastrowid
                return self.connection.execute(
                    'INSERT INTO registrations(participant_id,webinar_id) VALUES (?,?)',
                    (participant_id, webinar_id)
                ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValidationError('Не удалось зарегистрировать: нарушено ограничение базы данных.') from exc

    def registrations(self, webinar_id=None):
        sql = '''SELECT r.*, p.name, p.email, w.title FROM registrations r
                 JOIN participants p ON p.id=r.participant_id
                 JOIN webinars w ON w.id=r.webinar_id'''
        args = ()
        if webinar_id is not None:
            sql += ' WHERE r.webinar_id=?'
            args = (webinar_id,)
        return self.connection.execute(sql + ' ORDER BY r.id', args).fetchall()

    def set_attendance(self, registration_id, attended):
        if type(attended) is not bool:
            raise ValidationError('Статус должен быть True или False.')
        with self.connection:
            cursor = self.connection.execute(
                'UPDATE registrations SET attended=? WHERE id=?', (int(attended), registration_id)
            )
            if cursor.rowcount != 1:
                raise ValidationError('Регистрация не найдена.')

    def statistics(self):
        return self.connection.execute('''
            SELECT w.id, w.title, COUNT(r.id) AS registered,
                   COALESCE(SUM(r.attended),0) AS attended
            FROM webinars w LEFT JOIN registrations r ON r.webinar_id=w.id
            GROUP BY w.id, w.title ORDER BY w.starts_at, w.id
        ''').fetchall()


def format_date(starts_at):
    return datetime.strptime(starts_at, '%Y-%m-%d %H:%M:%S').replace(
        tzinfo=timezone.utc).astimezone(MOSCOW).strftime('%d.%m.%Y в %H:%M МСК')
