from setuptools import setup, find_packages

setup(
    name="python_youtube",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.85.1",
        "uvicorn[standard]==0.19.0",
        "celery==5.2.7",
        "redis==4.3.4",
        "undetected-chromedriver==3.2.1",
        "gevent==22.10.2",
        "psutil==5.9.2",
        "WMI==1.5.1",
        "requests==2.28.1",
        "fake-headers==1.0.2",
        "html5lib==1.1",
        "beautifulsoup4==4.10.0",
        "python-dotenv==0.21.0",
        "pydantic==1.10.2",
        "motor==3.1.1",
        "email-validator==1.1.2",
        "pymongo==4.3.3",
        "tzdata==2023.3",
        "fastapi-utils==0.2.1",
    ],
    description="Your project description here",
    author="Jakgrit",
    author_email="jakgrit@gmail.com",
    url="https://github.com/jakgrit/python-youtube-bot",
    package_data={'': ['.env']}
)
