from setuptools import setup, find_packages

setup(
    name="aicp-core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "msgpack>=1.0.7",
        "cryptography>=41.0.0",
        "pynacl>=1.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "pylint>=2.17.0",
        ]
    },
    python_requires=">=3.10",
)
