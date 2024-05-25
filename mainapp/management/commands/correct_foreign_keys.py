from django.core.management.base import BaseCommand
from mainapp.models import Cryptocurrency, User
class Command(BaseCommand):
    help = 'Corrects the user_id foreign key in the Cryptocurrency model'

    def handle(self, *args, **options):
        # Get all Cryptocurrency objects
        cryptocurrencies = Cryptocurrency.objects.all()

        for crypto in cryptocurrencies:
            # Check if the user exists
            if not User.objects.filter(id=crypto.user_id).exists():
                # If the user does not exist, update the user_id to a valid id
                # In this example, we're setting it to the id of the first User
                # You should replace this with appropriate logic for your application
                crypto.user_id = User.objects.first().id
                crypto.save()

        self.stdout.write(self.style.SUCCESS('Successfully corrected foreign keys'))