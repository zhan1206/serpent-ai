"""
SerpentAI Setup Script
支持 pip install . 和 pip install -e .
"""

from setuptools import setup, find_packages
import os

# 读取 README
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# 读取 requirements.txt
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
requirements = []
if os.path.exists(requirements_path):
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                requirements.append(line)

setup(
    name="serpent-ai",
    version="0.1.0",
    author="SerpentAI Team",
    author_email="",
    description="终极自托管企业级AI智能体框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zhan1206/serpent-ai",
    packages=find_packages(exclude=["tests*", "examples*", "docs*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
        ],
        "llama": [
            "llama-cpp-python>=0.2.0",
        ],
        "redis": [
            "redis>=4.5",
        ],
        "neo4j": [
            "neo4j>=5.0",
        ],
        "chromadb": [
            "chromadb>=0.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "serpent=backend.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
