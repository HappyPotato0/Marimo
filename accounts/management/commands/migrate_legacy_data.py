"""
Management command to migrate data from the legacy database (old TimeBooking_* tables)
into the new schema (accounts.*, scheduling.*).

Usage:
    python manage.py migrate_legacy_data

Run this ONCE, after `legacy` database is configured in settings.py and reachable.
Safe to re-run: uses get_or_create where sensible, but best to run only once on a
freshly migrated (empty) `default` database to avoid duplicates.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import (
    TeacherProfile, StudentProfile, TeacherStudent, TeacherLessonDuration,
)
from scheduling.models import (
    TeacherWeekdayAvailability, TeacherDateAvailability, Slot,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Migrate data from legacy database into new schema"

    def handle(self, *args, **options):
        with transaction.atomic():
            self.migrate_users()
            self.migrate_teacher_profiles()
            self.migrate_student_profiles()
            self.migrate_teacher_student()
            self.migrate_lesson_durations()
            self.migrate_weekday_availability()
            self.migrate_date_availability()
            self.migrate_slots()

        self.stdout.write(self.style.SUCCESS("Legacy data migration complete."))

    # ------------------------------------------------------------------
    def migrate_users(self):
        self.stdout.write("Migrating users...")
        count = 0
        for legacy_user in User.objects.using('legacy').all():
            obj, created = User.objects.using('default').get_or_create(
                username=legacy_user.username,
                defaults={
                    'first_name': legacy_user.first_name,
                    'last_name': legacy_user.last_name,
                    'email': legacy_user.email,
                    'password': legacy_user.password,  # already hashed, safe to copy
                    'is_staff': legacy_user.is_staff,
                    'is_active': legacy_user.is_active,
                    'is_superuser': legacy_user.is_superuser,
                    'date_joined': legacy_user.date_joined,
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} users created")

    # ------------------------------------------------------------------
    def migrate_teacher_profiles(self):
        self.stdout.write("Migrating teacher profiles...")
        # raw query on legacy connection since legacy model class doesn't exist anymore
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute('SELECT user_id, bio FROM "TimeBooking_teacherprofile"')
            rows = cursor.fetchall()

        count = 0
        self._teacher_map = {}  # legacy user_id -> new TeacherProfile
        for legacy_user_id, bio in rows:
            legacy_username = self._get_legacy_username(legacy_user_id)
            if not legacy_username:
                continue
            user = User.objects.using('default').filter(username=legacy_username).first()
            if not user:
                continue
            profile, created = TeacherProfile.objects.using('default').get_or_create(
                teacher=user,
                defaults={'bio': bio}
            )
            self._teacher_map[legacy_user_id] = profile
            if created:
                count += 1
        self.stdout.write(f"  -> {count} teacher profiles created")

    def migrate_student_profiles(self):
        self.stdout.write("Migrating student profiles...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute('SELECT user_id, bio FROM "TimeBooking_studentprofile"')
            rows = cursor.fetchall()

        count = 0
        self._student_map = {}  # legacy user_id -> new StudentProfile
        for legacy_user_id, bio in rows:
            legacy_username = self._get_legacy_username(legacy_user_id)
            if not legacy_username:
                continue
            user = User.objects.using('default').filter(username=legacy_username).first()
            if not user:
                continue
            profile, created = StudentProfile.objects.using('default').get_or_create(
                student=user,
                defaults={'bio': bio}
            )
            self._student_map[legacy_user_id] = profile
            if created:
                count += 1
        self.stdout.write(f"  -> {count} student profiles created")

    # ------------------------------------------------------------------
    def migrate_teacher_student(self):
        self.stdout.write("Migrating teacher-student links...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute('SELECT teacher_id, student_id FROM "TimeBooking_teacherstudent"')
            rows = cursor.fetchall()

        count = 0
        for legacy_teacher_id, legacy_student_id in rows:
            teacher = self._teacher_map.get(self._legacy_teacher_user_id(legacy_teacher_id))
            student = self._student_map.get(self._legacy_student_user_id(legacy_student_id))
            if not teacher or not student:
                continue
            _, created = TeacherStudent.objects.using('default').get_or_create(
                teacher=teacher, student=student,
                defaults={'price': 0, 'balance': 0}
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} teacher-student links created")

    def migrate_lesson_durations(self):
        self.stdout.write("Migrating lesson durations...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute('SELECT teacher_id, duration_minutes FROM "TimeBooking_teacherlessonduration"')
            rows = cursor.fetchall()

        count = 0
        for legacy_teacher_id, duration in rows:
            teacher = self._teacher_map.get(self._legacy_teacher_user_id(legacy_teacher_id))
            if not teacher:
                continue
            _, created = TeacherLessonDuration.objects.using('default').get_or_create(
                teacher=teacher, duration_minutes=duration,
                defaults={'coefficient': 1}
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} lesson durations created")

    # ------------------------------------------------------------------
    def migrate_weekday_availability(self):
        self.stdout.write("Migrating weekday availability...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute(
                'SELECT user_id, weekday, start_time, end_time FROM "TimeBooking_teacheravailability"'
            )
            rows = cursor.fetchall()

        count = 0
        for legacy_teacherprofile_id, weekday, start_time, end_time in rows:
            # NB: column is named user_id but actually FKs to TimeBooking_teacherprofile.id
            legacy_user_id = self._legacy_teacher_user_id(legacy_teacherprofile_id)
            teacher = self._teacher_map.get(legacy_user_id)
            if not teacher:
                continue
            _, created = TeacherWeekdayAvailability.objects.using('default').get_or_create(
                teacher=teacher, day_of_week=weekday,
                start_time=start_time, end_time=end_time,
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} weekday availability rows created")

    def migrate_date_availability(self):
        self.stdout.write("Migrating date availability...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute(
                'SELECT user_id, date, start_time, end_time FROM "TimeBooking_teacherdateavailability"'
            )
            rows = cursor.fetchall()

        count = 0
        for legacy_teacherprofile_id, date, start_time, end_time in rows:
            # NB: column is named user_id but actually FKs to TimeBooking_teacherprofile.id
            legacy_user_id = self._legacy_teacher_user_id(legacy_teacherprofile_id)
            teacher = self._teacher_map.get(legacy_user_id)
            if not teacher:
                continue
            _, created = TeacherDateAvailability.objects.using('default').get_or_create(
                teacher=teacher, date=date,
                start_time=start_time, end_time=end_time,
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} date availability rows created")

    # ------------------------------------------------------------------
    def migrate_slots(self):
        self.stdout.write("Migrating slots (skipping 'available' status)...")
        from django.db import connections
        with connections['legacy'].cursor() as cursor:
            cursor.execute(
                '''SELECT teacher_id, student_id, date, start_time, end_time, status, comment
                   FROM "TimeBooking_slot"'''
            )
            rows = cursor.fetchall()

        count = 0
        skipped = 0
        for legacy_teacher_id, legacy_student_id, date, start_time, end_time, status, comment in rows:
            if status == 'available':
                skipped += 1
                continue

            teacher_user_id = self._legacy_teacher_user_id(legacy_teacher_id)
            teacher = self._teacher_map.get(teacher_user_id)
            if not teacher:
                continue
            student = None
            if legacy_student_id:
                student_user_id = self._legacy_student_user_id(legacy_student_id)
                student = self._student_map.get(student_user_id)

            _, created = Slot.objects.using('default').get_or_create(
                teacher=teacher, student=student, date=date,
                start_time=start_time, end_time=end_time,
                defaults={
                    'status': status,  # booked/cancelled/break map 1:1
                    'comment': comment,
                    'paid_status': None,
                    'price': None,
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  -> {count} slots created, {skipped} 'available' slots skipped")

    # ------------------------------------------------------------------
    # Helpers: legacy TeacherProfile.id / StudentProfile.id -> auth_user.id -> username
    def _get_legacy_username(self, legacy_user_id):
        if not hasattr(self, '_legacy_username_cache'):
            self._legacy_username_cache = {}
        if legacy_user_id not in self._legacy_username_cache:
            user = User.objects.using('legacy').filter(id=legacy_user_id).first()
            self._legacy_username_cache[legacy_user_id] = user.username if user else None
        return self._legacy_username_cache[legacy_user_id]

    def _legacy_teacher_user_id(self, legacy_teacherprofile_id):
        """TimeBooking_teacherstudent.teacher_id references TeacherProfile.id, not user_id."""
        if not hasattr(self, '_tp_id_to_user_id'):
            from django.db import connections
            with connections['legacy'].cursor() as cursor:
                cursor.execute('SELECT id, user_id FROM "TimeBooking_teacherprofile"')
                self._tp_id_to_user_id = dict(cursor.fetchall())
        return self._tp_id_to_user_id.get(legacy_teacherprofile_id)

    def _legacy_student_user_id(self, legacy_studentprofile_id):
        """TimeBooking_teacherstudent.student_id references StudentProfile.id, not user_id."""
        if not hasattr(self, '_sp_id_to_user_id'):
            from django.db import connections
            with connections['legacy'].cursor() as cursor:
                cursor.execute('SELECT id, user_id FROM "TimeBooking_studentprofile"')
                self._sp_id_to_user_id = dict(cursor.fetchall())
        return self._sp_id_to_user_id.get(legacy_studentprofile_id)
