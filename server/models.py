import os
import subprocess
import sys

from urllib.parse import ParseResult, urljoin

from django.db import models
from django.conf import settings
from django.urls import reverse_lazy

import docker
import docker.errors

import requests

from core.models import Warehouse

clients_cache = {}


def get_server_object_model(object_type=None):
    if object_type is None:
        object_type = settings.SERVER_OBJECT_TYPE

    if object_type == "warehouse":
        return Warehouse

    return None


def get_server_object(object_type=None, object_id=None):
    if object_type is None:
        object_type = settings.SERVER_OBJECT_TYPE

    if object_id is None:
        object_id = settings.SERVER_OBJECT_ID

    model = get_server_object_model(object_type=object_type)
    return model.objects.get(pk=object_id)


class Server(models.Model):
    SERVER_TYPES = tuple(
        zip(
            settings.SERVER_TYPES,
            tuple(
                server_type.replace("_", " ") for server_type in settings.SERVER_TYPES
            ),
        )
    )

    SUBPROCESS = "subprocess"
    DOCKER = "docker"

    BACKENDS = ((SUBPROCESS, SUBPROCESS), (DOCKER, DOCKER))

    DOWN = "down"
    UP = "up"

    STATUSES = ((DOWN, DOWN), (UP, UP))

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=SERVER_TYPES)
    object_id = models.CharField(max_length=255)

    backend = models.CharField(max_length=255, choices=BACKENDS, default=SUBPROCESS)
    scheme = models.CharField(max_length=255)
    netloc = models.CharField(max_length=255)
    healthcheck_path = models.CharField(
        max_length=255, default=reverse_lazy("server:health"), blank=True
    )
    kill_path = models.CharField(
        max_length=255, default=reverse_lazy("server:kill"), blank=True
    )

    wanted_status = models.CharField(max_length=255, choices=STATUSES, default=UP)
    last_known_status = models.CharField(
        max_length=255, choices=STATUSES, default=DOWN, editable=False
    )

    def get_hostname(self):
        return ParseResult(
            scheme=self.scheme,
            netloc=self.netloc,
            path="",
            params="",
            query="",
            fragment="",
        ).geturl()

    def check_health(self):
        if self.scheme in ("http", "https"):
            url = urljoin(self.get_hostname(), self.healthcheck_path)

            try:
                requests.get(url)
            except requests.ConnectionError:
                self.last_known_status = self.DOWN
            else:
                self.last_known_status = self.UP
            return self.save(update_fields=("last_known_status",))

        raise NotImplementedError(repr(self.scheme))

    def start(self):
        if self.backend == self.SUBPROCESS:
            env = os.environ.copy()
            env.update(
                {"SERVER_OBJECT_TYPE": self.type, "SERVER_OBJECT_ID": self.object_id}
            )
            return subprocess.Popen(
                [
                    sys.executable,
                    os.path.join(settings.BASE_DIR, "manage.py"),
                    "runserver",
                    self.netloc,
                ],
                env=env,
            )
        elif self.backend == self.DOCKER:
            if "docker" not in clients_cache:
                client = docker.from_env()
                clients_cache["docker"] = client
            else:
                client = clients_cache["docker"]
            env = os.environ.copy()
            env.update(
                {"SERVER_OBJECT_TYPE": self.type, "SERVER_OBJECT_ID": self.object_id}
            )
            name = "autonomousdomain_{name}".format(name=self.name.lower().replace(' ', '_'))
            port = int(self.netloc.rsplit(':', 1)[1])

            try:
                image = client.images.list(
                    filters={"label": "name=autonomousdomain_server"},
                )[0]
            except IndexError:
                image = client.images.build(
                    path=settings.BASE_DIR,
                    labels={"name": "autonomousdomain_server"},
                    rm=True,
                    forcerm=True,
                )[0]

            try:
                return client.containers.get(name)
            except docker.errors.NotFound:
                return client.containers.run(
                    image.id,
                    "python manage.py runserver {netloc}".format(netloc=self.netloc),
                    detach=True,
                    name=name,
                    ports={'{port}/tcp'.format(port=port): port},
                    volumes={settings.BASE_DIR: {'bind': '/mnt', 'mode': 'rw'}},
                    working_dir='/mnt',
                    environment=env,
                    network_mode='host',
                )

        raise NotImplementedError(self.backend)

    def kill(self):
        if self.backend in (self.SUBPROCESS, self.DOCKER):
            if self.scheme in ("http", "https"):
                kill_url = urljoin(self.get_hostname(), self.kill_path)

                try:
                    requests.get(kill_url)
                except Exception:
                    return True
                return False

            raise NotImplementedError(self.scheme + " for " + self.backend)

        raise NotImplementedError(self.backend)

    def __str__(self):
        return self.name
