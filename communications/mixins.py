from .services import create_notice


class NoticeCreateMixin:
    """Reusable class-based notice creation behavior."""

    def should_create_notice(self):
        return True

    def get_notice_title(self):
        raise NotImplementedError(
            "NoticeCreateMixin requires get_notice_title()."
        )

    def get_notice_content(self):
        raise NotImplementedError(
            "NoticeCreateMixin requires get_notice_content()."
        )

    def get_notice_type(self):
        return "general"

    def get_notice_roles(self):
        return []

    def get_notice_classes(self):
        return []

    def get_notice_posted_by(self):
        return getattr(self.request, "user", None)

    def get_notice_kwargs(self):
        return {}

    def create_notice_from_request(self):
        if not self.should_create_notice():
            return None

        return create_notice(
            title=self.get_notice_title(),
            content=self.get_notice_content(),
            posted_by=self.get_notice_posted_by(),
            notice_type=self.get_notice_type(),
            for_roles=self.get_notice_roles(),
            for_classes=self.get_notice_classes(),
            **self.get_notice_kwargs(),
        )
