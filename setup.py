from setuptools import setup, find_namespace_packages

setup(
    name="discord-mcp",
    version="0.1.13",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "discord.py>=2.3.2",
        "PyNaCl>=1.5.0",
        "python-dotenv>=1.0.0"
    ],
    entry_points={
        'console_scripts': [
            'discord-mcp=discord_mcp:main',
        ],
    }
)
