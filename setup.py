"""Setup configuration for Macallan RF Performance Tool."""
from setuptools import setup, find_packages

setup(
    name="macallan-rf-perf-tool",
    version="0.1.0",
    description="RF Performance Tool for analyzing S-parameters and compliance testing",
    author="Macallan Engineering",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.13.7",
    install_requires=[
        "PyQt6>=6.6.0",
        "scikit-rf>=0.30.0",
        "numpy>=1.26.0",
        "matplotlib>=3.8.0",
        "pydantic>=2.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.11.0",
            "ruff>=0.1.0",
        ],
    },
)










