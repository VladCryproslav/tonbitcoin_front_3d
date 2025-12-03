import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()

from django.test import Client
import timeit

def a():
    c = Client()
    response = c.get(path="/api/roadmap-items/", content_type="text/plain")

print(timeit.timeit(a, number=1))

import requests
def b():
    response = requests.get("http://mine.tbtc.one/api/roadmap-items/")

print(timeit.timeit(b, number=1))