import student_evaluation_system.settings as base_settings

BASE_DIR = base_settings.BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": base_settings.BASE_DIR / "test_db.sqlite3",
    }
}
