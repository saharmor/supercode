from setuptools import setup, find_packages

setup(
    name="supersurf",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyaudio",
        "openai-whisper",
        "pynput",
        "pyobjc",
        "rumps",
    ],
    entry_points={
        "console_scripts": [
            "supersurf=super_surf.main:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Voice-controlled Mac application for Windsurf IDE",
    keywords="voice, control, windsurf, ide, mac",
    python_requires=">=3.7",
)