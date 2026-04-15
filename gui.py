import customtkinter as ctk
from tkinter import filedialog
import threading
from metallum import fetch_lyrics_logic, jellyfin_scan

class MetallumGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Metallum Lyrics Toolkit")
        self.geometry("750x650")
        ctk.set_appearance_mode("dark")

        # UI Header
        self.label = ctk.CTkLabel(self, text="Metal-Archives Lyrics Downloader", font=("Arial", 22, "bold"))
        self.label.pack(pady=20)

        # Einzelsuche Frame
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=10, padx=20, fill="x")
        
        self.band_input = ctk.CTkEntry(self.search_frame, placeholder_text="Band", width=200)
        self.band_input.grid(row=0, column=0, padx=10, pady=10)
        self.song_input = ctk.CTkEntry(self.search_frame, placeholder_text="Song", width=200)
        self.song_input.grid(row=0, column=1, padx=10, pady=10)
        self.btn_search = ctk.CTkButton(self.search_frame, text="Suchen", width=100, command=self.run_single)
        self.btn_search.grid(row=0, column=2, padx=10, pady=10)

        # Output / Log Bereich
        self.textbox = ctk.CTkTextbox(self, width=700, height=350, font=("Consolas", 12))
        self.textbox.pack(pady=10, padx=20)

        # Jellyfin Button
        self.btn_jelly = ctk.CTkButton(self, text="Musik-Bibliothek scannen (Jellyfin)", 
                                        fg_color="#1f538d", hover_color="#14375e", height=40,
                                        command=self.run_jelly)
        self.btn_jelly.pack(pady=20)

    def log_message(self, message):
        # Update sicher aus dem Hintergrund-Thread an die GUI senden
        self.after(0, self._safe_log, message)

    def _safe_log(self, message):
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")

    def run_single(self):
        band, song = self.band_input.get(), self.song_input.get()
        if not band or not song: return
        self.textbox.delete("1.0", "end")
        self.log_message(f"Suche: {band} - {song}...")
        
        def task():
            lyrics = fetch_lyrics_logic(band, song)
            self.log_message("\n" + lyrics if lyrics else "\nKeine Lyrics gefunden.")
        
        threading.Thread(target=task, daemon=True).start()

    def run_jelly(self):
        path = filedialog.askdirectory()
        if path:
            self.textbox.delete("1.0", "end")
            # Starte Scan-Thread mit Callback
            threading.Thread(target=jellyfin_scan, args=(path, self.log_message), daemon=True).start()

if __name__ == "__main__":
    app = MetallumGUI()
    app.mainloop()