from setuptools import setup

def get_requirements():
    with open("requirements.txt", "r") as req:
        requires = req.readlines()
    return [req.strip() for req in requires]


setup(
    name='vmaker',
    version='1.0.0',
    description='',
    url='https://github.com/delatars/vmaker',
    author='Aleksandr Morokov',
    author_email='morocov.ap.muz@gmail.com',
    license='BSD',
    packages=['vmaker', "vmaker.init", "vmaker.plugins", "vmaker.utils"],
    # install_requires=get_requirements(),
    entry_points={
        'console_scripts': ['vmaker=vmaker.main:entry'],
    }
)