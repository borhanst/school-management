from django.db.models.signals import post_save
from django.dispatch import receiver

from fees.services import create_admission_fee_invoices
from students.models import Student


@receiver(post_save, sender=Student)
def create_student_admission_invoices(sender, instance, created, **kwargs):
    if not created:
        return
    create_admission_fee_invoices(instance)
