from setuptools import setup, find_packages

setup(
    name="ai-code-review",
    version="1.0.0",
    description="AI-powered code review in your terminal",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Jayden Dancer",
    url="https://github.com/jaydendancer12/ai-code-review",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "codereview=codereview.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
