import enum


class WeekDay(enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"


class Period(enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"
    P6 = "P6"


class SubjectType(enum.Enum):
    THEORY = "THEORY"
    LAB = "LAB"


class SessionStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AttendanceStatus(enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
