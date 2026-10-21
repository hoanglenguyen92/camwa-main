from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_students: int
    students_with_present_status: int