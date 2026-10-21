from enum import Enum


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationType(str, Enum):
    NEW_REQUEST = "NEW_REQUEST"
    REQUEST_APPROVED = "REQUEST_APPROVED"
    REQUEST_REJECTED = "REQUEST_REJECTED"


class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


class CoordinatorRole(str, Enum):
    LECTURER = "LECTURER"
    AC = "AC"


class AccountRole(str, Enum):
    ADMIN = "ADMIN"
    FA = "FA"
    LECTURER = "LECTURER"
    AC = "AC"
    STUDENT = "STUDENT"
