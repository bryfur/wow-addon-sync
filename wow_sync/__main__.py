#!/usr/bin/env python3
import tkinter as tk
from async_tkinter_loop import async_mainloop
from wow_sync.ui.main_window import MainWindow


def main():
    root = tk.Tk()
    app = MainWindow(root)
    async_mainloop(root)


if __name__ == "__main__":
    main()
