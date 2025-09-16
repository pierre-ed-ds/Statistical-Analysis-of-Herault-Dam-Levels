import ttkbootstrap as tb
from app_sur_tkinter import SalagouApp
from app_sur_tkinter import SplashScreen  # ton splash

def main():
    root = tb.Window(themename='flatly')
    root.withdraw()  # cacher la fenêtre principale

    splash = SplashScreen(root, "Chargement…")
    
    # Lancer l'UI principale après 2 secondes
    root.after(2000, lambda: start_app(root, splash))
    root.mainloop()

def start_app(root, splash):
    splash.destroy()
    root.deiconify()
    app = SalagouApp(root)

if __name__ == "__main__":
    main()