# DBA Tools CLI

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-v3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![PDM](https://img.shields.io/badge/pdm-package%20manager-blueviolet.svg)](https://pdm-project.org/latest/)
[![Database](https://img.shields.io/badge/database-sqlite-green.svg)](https://www.sqlite.org/)

## Description

DBA Tools CLI is a command-line application built with Python v3.12. It serves as a set of tools for Database Administrators (DBAs) and developers working with SQLite databases. The application streamlines common database administration tasks and provides a convenient command-line interface for managing databases efficiently.

## Features

- [ ] Interactive for search environment database server list

## Installation

To install DBA Tools CLI, ensure you have Python v3.12 and PDM installed on your system. Then, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/febridev/DBA-Tools-Cli.git
   cd DBA-Tools-Cli
   ```
2. Install All Dependency:

```bash
   pdm install
```

3. Set .env file for database `serverlist`

```bash
cp env.example .env
```

4. Edit .env put detail database SQLite

5. Usage

```bash
pdm run python -m cli_python.main_menu

```

# License

This project is licensed under the MIT License - see the LICENSE file for details.

# Acknowledgments

Remember to replace placeholders such as `your-username` with your actual GitHub username and update sections like features, commands, and acknowledgments based on your application's specifics.
