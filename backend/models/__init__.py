from backend.models.academic_coordinator import AcademicCoordinator
from backend.models.attendance import Attendance
from backend.models.attendance_request import AttendanceRequest
from backend.models.exam import Exam
from backend.models.facility_faculty import FacilityFaculty
from backend.models.iam import Iam
from backend.models.image_asset import ImageAsset
from backend.models.intake import Intake
from backend.models.lecturer import Lecturer
from backend.models.module import Module
from backend.models.module_registration import ModuleRegistration
from backend.models.notification import Notification
from backend.models.program import Program
from backend.models.semester import Semester
from backend.models.student import Student

__all__ = [
    "Iam",
    "Student",
    "Program",
    "Intake",
    "Semester",
    "Lecturer",
    "Module",
    "ModuleRegistration",
    "Attendance",
    "AttendanceRequest",
    "Exam",
    "AcademicCoordinator",
    "FacilityFaculty",
    "ImageAsset",
    "Notification",
]
