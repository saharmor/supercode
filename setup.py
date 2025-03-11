from setuptools import setup, find_packages

setup(
    name="supercursor",
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
            "supercursor=super_cursor.main:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Voice-controlled Mac application for Cursor IDE",
    keywords="voice, control, cursor, ide, mac",
    python_requires=">=3.7",
)