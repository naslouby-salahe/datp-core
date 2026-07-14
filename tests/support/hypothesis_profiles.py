import os

from hypothesis import settings

settings.register_profile(
    "ci",
    max_examples=100,
    deadline=400,
    derandomize=True,
)
settings.register_profile(
    "dev",
    max_examples=25,
    deadline=400,
    derandomize=False,
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))
