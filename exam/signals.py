from datetime import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver

from exam.models import Test


@receiver(post_save, sender=Test)
def auto_close_test(sender, instance, **kwargs):
    if instance.deadline < timezone.now():
        # logic to auto close the test
        pass
