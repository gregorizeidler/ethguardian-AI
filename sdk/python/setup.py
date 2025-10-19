"""Setup script for EthGuardian Python SDK"""

from setuptools import setup, find_packages

setup(
    name="ethguardian",
    version="1.0.0",
    description="Python SDK for EthGuardian AI-Powered Ethereum AML & Forensics Platform",
    author="EthGuardian Team",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)

