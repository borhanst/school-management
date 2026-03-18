from django.utils import timezone

from .models import Notice


def create_notice(
    title,
    content,
    posted_by=None,
    notice_type="general",
    for_roles=None,
    for_classes=None,
    publish_date=None,
    expiry_date=None,
    is_active=True,
    is_pinned=False,
    attachment=None,
):
    """Create a notice with normalized defaults for shared use."""
    if for_roles is None:
        normalized_roles = []
    elif isinstance(for_roles, str):
        normalized_roles = [for_roles]
    else:
        normalized_roles = list(for_roles)

    notice = Notice.objects.create(
        title=title,
        content=content,
        posted_by=posted_by,
        notice_type=notice_type,
        for_roles=normalized_roles,
        publish_date=publish_date or timezone.now(),
        expiry_date=expiry_date,
        is_active=is_active,
        is_pinned=is_pinned,
        attachment=attachment,
    )

    if for_classes:
        notice.for_classes.set(for_classes)

    return notice
