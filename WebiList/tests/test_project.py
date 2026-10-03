import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import Database, ValidationError, format_date


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.db'
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_seed_and_timezone(self):
        self.assertEqual(len(self.db.webinars()), 3)
        self.assertEqual(format_date(self.db.webinars()[0]['starts_at']), '24.09.2026 в 19:00 МСК')

    def test_persistence_and_idempotent_seed(self):
        rid = self.db.register('react-start', 'Иван', 'ivan@example.com')
        self.db.set_attendance(rid, True)
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(len(self.db.webinars()), 3)
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM speakers').fetchone()[0], 3)
        self.assertEqual(self.db.registrations()[0]['attended'], 1)

    def test_duplicate_normalization(self):
        self.db.register('react-start', ' Иван ', ' IVAN@EXAMPLE.COM ')
        with self.assertRaises(ValidationError):
            self.db.register('react-start', 'Иван', 'ivan@example.com')
        self.assertEqual(len(self.db.registrations()), 1)
        self.assertEqual(self.db.registrations()[0]['email'], 'ivan@example.com')

    def test_same_participant_multiple_webinars(self):
        self.db.register('react-start', 'Иван', 'ivan@example.com')
        self.db.register('career', 'Иван', 'ivan@example.com')
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM participants').fetchone()[0], 1)
        self.assertEqual(len(self.db.registrations('career')), 1)

    def test_conflicting_name_does_not_overwrite(self):
        self.db.register('react-start', 'Иван', 'ivan@example.com')
        with self.assertRaises(ValidationError):
            self.db.register('career', 'Пётр', 'ivan@example.com')
        self.assertEqual(self.db.registrations()[0]['name'], 'Иван')
        self.assertEqual(len(self.db.registrations()), 1)

    def test_validation(self):
        for email in ['a', '@a.com', 'a@@b.com', 'a b@c.com', '.a@b.com', 'a..b@c.com', 'a@-b.com']:
            with self.subTest(email=email), self.assertRaises(ValidationError):
                self.db.register('react-start', 'Иван', email)
        for name in ['', '   ', 'a' * 121, 'a\nb']:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.db.register('react-start', name, 'ok@example.com')
        self.assertEqual(len(self.db.registrations()), 0)

    def test_unknown_webinar_leaves_no_orphan(self):
        with self.assertRaises(ValidationError):
            self.db.register('missing', 'Иван', 'ivan@example.com')
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM participants').fetchone()[0], 0)

    def test_transaction_rolls_back_new_participant(self):
        self.db.connection.executescript('''CREATE TRIGGER reject_test BEFORE INSERT ON registrations
            BEGIN SELECT RAISE(ABORT, 'test failure'); END;''')
        with self.assertRaises(ValidationError):
            self.db.register('react-start', 'Иван', 'ivan@example.com')
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM participants').fetchone()[0], 0)

    def test_attendance_idempotence_and_removal(self):
        rid = self.db.register('react-start', 'Иван', 'ivan@example.com')
        self.db.set_attendance(rid, True)
        self.db.set_attendance(rid, True)
        self.assertEqual(self.db.registrations()[0]['attended'], 1)
        self.db.set_attendance(rid, False)
        self.assertEqual(self.db.registrations()[0]['attended'], 0)
        with self.assertRaises(ValidationError):
            self.db.set_attendance(999, True)

    def test_statistics_include_empty_webinars(self):
        self.db.register('react-start', 'Иван', 'ivan@example.com')
        rid = self.db.register('react-start', 'Анна', 'anna@example.com')
        self.db.set_attendance(rid, True)
        data = {r['id']: r for r in self.db.statistics()}
        self.assertEqual((data['react-start']['registered'], data['react-start']['attended']), (2, 1))
        self.assertEqual(data['career']['registered'], 0)

    def test_sql_constraints(self):
        self.db.register('react-start', 'Иван', 'ivan@example.com')
        for sql in [
            "INSERT INTO registrations(participant_id,webinar_id) VALUES(999,'react-start')",
            "INSERT INTO registrations(participant_id,webinar_id) VALUES(1,'missing')",
            "INSERT INTO registrations(participant_id,webinar_id) VALUES(1,'react-start')",
            'UPDATE registrations SET attended=2',
            "DELETE FROM webinars WHERE id='react-start'",
        ]:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                with self.db.connection:
                    self.db.connection.execute(sql)
        self.assertEqual(self.db.connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_sql_payload_is_data(self):
        name = "Robert'); DROP TABLE participants; --"
        self.db.register('react-start', name, 'test@example.com')
        self.assertEqual(self.db.registrations()[0]['name'], name)

    def test_cli_registration_attendance_restart(self):
        args = [sys.executable, str(ROOT / 'main.py'), '--db', str(self.path)]
        # Регистрация, установка статуса, статистика и штатный выход.
        result = subprocess.run(args, input='2\n1\nИван\nivan@example.com\n\n4\n1\n1\n\n5\n\n0\n',
                                text=True, capture_output=True, cwd=self.temp.name, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Готово! Регистрация', result.stdout)
        self.assertIn('Записались: 1; посетили: 1', result.stdout)
        result = subprocess.run(args, input='3\n\n0\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ivan@example.com', result.stdout)
        self.assertIn('Посещение: посетил', result.stdout)

    def test_cli_invalid_input_cancel_and_eof(self):
        result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--db', str(self.path)],
                                input='x\n\n2\nabc\n\n2\n0\n\n', text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Неизвестная команда', result.stdout)
        self.assertIn('Нужно ввести целое число', result.stdout)
        self.assertEqual(len(self.db.registrations()), 0)


if __name__ == '__main__':
    unittest.main()
