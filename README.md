# DBA Tools CLI (TUI Edition)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Textual](https://img.shields.io/badge/framework-Textual-green.svg)](https://textual.textualize.io/)

## Description

**DBA Tools CLI** has evolved into a powerful Textual User Interface (TUI) application designed for Database Administrators and DevOps engineers. Built with Python and the [Textual](https://textual.textualize.io/) framework, it provides a retro-modern interface to manage your daily workflows directly from the terminal.

This tool now utilizes **[uv](https://github.com/astral-sh/uv)** for extremely fast package management and dependency resolution.

## ✨ Features

### 🖥️ SSH Manager (New!)
Manage your SSH connections without leaving the keyboard.
- **Visual Config Management**: Add, Edit, and View hosts stored in your local `~/.ssh/config`.
- **Searchable List**: Quickly filter through hundreds of servers.
- **Smart Launcher**: Connect to servers in a **New Tab** or **New Window** automatically.
    - *Supported Terminals:* Ghostty, iTerm2, Windows Terminal, GNOME Terminal, Apple Terminal.

### 📝 To-Do List
A simple, persistent task manager integrated into your workspace.
- **Auto-save**: Tasks are saved to JSON automatically.
- **Quick Actions**: Add, Delete, and Toggle status with keyboard shortcuts.

### 🗄️ Database IDE (WIP)
- *Coming Soon*: Integrated lightweight SQL client for SQLite and other databases.

## 🚀 Installation

Ensure you have **Python 3.9+** installed. This project uses **uv** for dependency management.

### 1. Install uv
If you haven't installed `uv` yet, run the official installer:

**macOS / Linux:**
```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
