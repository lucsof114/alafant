from setuptools import setup, find_packages

setup(
    name='Alafant',
    version='0.1.0',
    packages=find_packages(),
    # description='A description of your project',
    # long_description=open('README.md').read(),
    # long_description_content_type='text/markdown',
    author='lucas',
    # author_email='your.email@example.com',
    # url='https://github.com/yourusername/<x>',
    install_requires=[
        'numpy',
        'websockets',
        'pandas',
        'requests',
        'PyYAML'
    ],
    python_requires='>=3.11',
)