from setuptools import setup, find_packages

setup(
    name="anna-dl",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "urllib3>=1.26.0",
    ],
    entry_points={
        "console_scripts": [
            "anna-dl=anna_dl.cli:main",
            "bookdl=anna_dl.cli:main",
        ],
    },
)
