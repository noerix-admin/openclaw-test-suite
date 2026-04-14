from setuptools import setup, find_packages

setup(
    name="openclaw-test-suite",
    version="1.0.0",
    description="Testumgebung fuer OpenClaw-Clone Agenten",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "llama-cpp-python>=0.3.0",
        "pytest>=8.0",
        "pytest-asyncio>=0.24",
        "pytest-timeout>=2.3",
        "pyyaml>=6.0",
        "jinja2>=3.1",
        "rich>=13.0",
        "httpx>=0.27",
        "python-dotenv>=1.0",
    ],
)
