import tkinter
from tkinter import ttk


class LabelEntryPair:
    def get_value(self):
        return self.entry.get()

    def __init__(self, master, label_text, row, column, initial_val):
        self.var = tkinter.StringVar(value=initial_val)
        self.label = ttk.Label(master, text=label_text)
        self.label.grid(row=row, column=column, padx=5, pady=5, sticky="w")
        self.entry = ttk.Entry(master, textvariable=self.var)
        self.entry.grid(row=row, column=column + 1, padx=5, pady=5, sticky="w")
