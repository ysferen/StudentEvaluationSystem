from student_evaluation_system.settings import *  # noqa: F403

# Override settings for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
