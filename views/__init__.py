"""
Views package — exports all PySide6 widget classes.
"""

from .landing import LandingWidget
from .login import LoginWidget
from .home import HomeWidget
from .data_explorer import DataExplorerWidget
from .learn import LearnWidget
from .progress import ProgressWidget
from .quiz_center import QuizCenterWidget

__all__ = [
    "LandingWidget",
    "LoginWidget",
    "HomeWidget",
    "DataExplorerWidget",
    "LearnWidget",
    "ProgressWidget",
    "QuizCenterWidget",
]
