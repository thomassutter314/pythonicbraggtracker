import tkinter as tk
from tkinter import filedialog as fd

def userInitPrompt():
    root = tk.Tk()
    root.title("pbt")
    root.geometry("400x400")
    
    def select_dir():
        dirname = fd.askdirectory(title="Select Image Average Directory")
        print(f"Selected directory: {dirname}")
        # Do something with the selected directory here
    
    select_button = tk.Button(root, text="Analyze UED Scan", command=select_dir)
    select_button.pack(padx=10, pady=10)
    
    root.mainloop()


if __name__ == '__main__':
    userInitPrompt()
