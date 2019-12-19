import time

from django.core.management.base import BaseCommand

from server.models import Server


class Command(BaseCommand):
    help = "Start the object server orchestrator."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Started object server orchestrator."))

        while True:
            self.stdout.write(self.style.SUCCESS("Checking object servers."))

            for server in Server.objects.iterator():
                server.check_health()

                if (
                    server.last_known_status == Server.DOWN
                    and server.wanted_status == Server.UP
                ):
                    server.start()
                    time.sleep(1)
                    server.check_health()
                elif (
                    server.last_known_status == Server.UP
                    and server.wanted_status == Server.DOWN
                ):
                    server.kill()
                    time.sleep(1)
                    server.check_health()
            time.sleep(10)
