from django.core.management.base import BaseCommand, CommandError

from integrations.email.smtp import send_text_email


class Command(BaseCommand):
    help = "Send one explicit SMTP smoke-test email without printing credentials."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient address")

    def handle(self, *args, **options):
        try:
            send_text_email(
                subject="IT Job Portal SMTP test",
                message="SMTP delivery from the IT Job Portal backend succeeded.",
                recipients=[options["to"]],
            )
        except Exception as exc:
            raise CommandError(f"SMTP test failed: {type(exc).__name__}") from exc
        self.stdout.write(self.style.SUCCESS("SMTP accepted the test message."))
