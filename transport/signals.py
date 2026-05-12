from django.db.models.signals import post_save
from django.dispatch import receiver

from fees.services import ensure_transport_assignment_invoice
from transport.models import TransportAssignment


@receiver(post_save, sender=TransportAssignment)
def create_transport_fee_invoice(sender, instance, created, **kwargs):
    if not created:
        return
    ensure_transport_assignment_invoice(instance)
