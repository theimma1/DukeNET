from setuptools import setup, find_packages

setup(
    name="ains-core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "redis>=5.0.0",
        "pydantic>=2.5.0",
        "python-jose[cryptography]>=3.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.7.0",
            "pylint>=2.17.0",
        ]
    },
    python_requires=">=3.10",
)
