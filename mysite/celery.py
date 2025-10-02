import os
from celery import Celery

# set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

app = Celery("mysite")

# Use Redis as broker
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all apps
app.autodiscover_tasks()
