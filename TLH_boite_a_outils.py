import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import random
import json
import os

# Tentative d'importation de Pillow pour la gestion avancée des images (JPG, redimensionnement)
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# --- CONFIGURATION DU THÈME (Inspiré JDR Magie/Tisseur) ---
BG_COLOR = "#1A1A1D"
FG_COLOR = "#C3A95B"
TEXT_COLOR = "#E0E0E0"
ENTRY_BG = "#2D2D30"
ACCENT_COLOR = "#4E1A24"

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Dark.TFrame")

        # Configuration pour adapter la largeur
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # S'adapte à la largeur du canvas (fenêtre)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width)
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            # Ne pas scroller si la touche Contrôle est appuyée (utilisée pour le zoom)
            if event.state & 4:
                return
                
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
            else:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", _on_mousewheel)
        self.canvas.bind_all("<Button-5>", _on_mousewheel)

class RPGAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("THE LAST HERO - Grimoire - Assistant JDR")
        self.geometry("1000x800")
        self.minsize(800, 600)
        self.configure(bg=BG_COLOR)
        
        self.setup_fonts()
        self.apply_theme()
        self.bind_zoom()
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.entries = {}
        self.image_path = None
        
        self.setup_dice_tab()
        self.setup_character_tab()
        self.setup_notes_tab()
        
        # Charger l'état précédent à l'ouverture
        self.load_autosave()

        # Sauvegarde automatique toutes les 10 secondes pendant l'utilisation.
        self._autosave_job = None
        self.schedule_autosave()

        # Intercepter la fermeture de la fenêtre
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_fonts(self):
        self.default_size = 10

        # Conserver les objets Font dans self afin qu'ils restent vivants.
        self.ui_font = tkfont.Font(
            name="UIFont", family="Georgia", size=self.default_size
        )
        self.ui_font_bold = tkfont.Font(
            name="UIFontBold", family="Georgia",
            size=self.default_size, weight="bold"
        )
        self.ui_font_title = tkfont.Font(
            name="UIFontTitle", family="Georgia",
            size=self.default_size + 2, weight="bold", slant="italic"
        )
        self.text_font = tkfont.Font(
            name="TextFont", family="Arial", size=self.default_size
        )
        self.mono_font = tkfont.Font(
            name="MonoFont", family="Consolas", size=self.default_size + 1
        )

    def bind_zoom(self):
        self.bind_all("<Control-MouseWheel>", self.on_zoom)
        self.bind_all("<Control-Button-4>", self.on_zoom)
        self.bind_all("<Control-Button-5>", self.on_zoom)

    def on_zoom(self, event):
        # Détecter la direction du zoom
        if event.num == 4 or event.delta > 0:
            self.default_size += 1
        elif event.num == 5 or event.delta < 0:
            self.default_size -= 1
            
        self.default_size = max(6, min(40, self.default_size)) # Limites de zoom
        
        # Les objets Font sont conservés dans self : ils existent toujours.
        self.ui_font.configure(size=self.default_size)
        self.ui_font_bold.configure(size=self.default_size)
        self.ui_font_title.configure(size=self.default_size + 2)
        self.text_font.configure(size=self.default_size)
        self.mono_font.configure(size=self.default_size + 1)

    def apply_theme(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font="UIFont")
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font="UIFontBold")
        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("TFrame", background=BG_COLOR)
        
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background="#333", foreground=FG_COLOR, font="UIFontBold", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", ACCENT_COLOR)], foreground=[("selected", "#FFF")])
        
        style.configure("TLabelframe", background=BG_COLOR, bordercolor=FG_COLOR)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground=FG_COLOR, font="UIFontTitle")
        
        style.configure("TButton", background=ACCENT_COLOR, foreground="#FFF", font="UIFontBold", borderwidth=0)
        style.map("TButton", background=[("active", "#7a2737")])
        
        style.configure("TCombobox", fieldbackground=ENTRY_BG, background=ENTRY_BG, foreground=TEXT_COLOR)
        style.configure("TSpinbox", fieldbackground=ENTRY_BG, background=ENTRY_BG, foreground=TEXT_COLOR)
        
    def setup_dice_tab(self):
        dice_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(dice_frame, text="1. Lanceur de Dés")
        
        config_frame = ttk.LabelFrame(dice_frame, text=" Configuration du Rituel (Lancer) ", padding=15)
        config_frame.pack(fill="x", pady=10)
        
        ttk.Label(config_frame, text="Nombre :").grid(row=0, column=0, padx=5, pady=5)
        self.num_dice_var = tk.IntVar(value=1)
        ttk.Spinbox(config_frame, from_=1, to=100, textvariable=self.num_dice_var, width=5).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Faces :").grid(row=0, column=2, padx=15, pady=5)
        self.num_faces_var = tk.IntVar(value=20)
        faces_cb = ttk.Combobox(config_frame, textvariable=self.num_faces_var, values=[4, 6, 8, 10, 12, 20, 100], width=5)
        faces_cb.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Motif du jet :").grid(row=0, column=4, padx=15, pady=5)
        self.motive_var = tk.StringVar()
        motive_entry = tk.Entry(config_frame, textvariable=self.motive_var, width=25, bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font="UIFont")
        motive_entry.grid(row=0, column=5, padx=5, pady=5)
        
        btn = ttk.Button(config_frame, text=" 🎲 LANCER LES DÉS ", command=self.roll_dice)
        btn.grid(row=0, column=6, padx=30, pady=5)
        
        res_frame = ttk.LabelFrame(dice_frame, text=" Historique des Destinées ", padding=10)
        res_frame.pack(fill="both", expand=True, pady=10)
        
        self.result_text = tk.Text(res_frame, height=15, state="normal", font="MonoFont", bg=ENTRY_BG, fg="#FFF")
        self.result_text.pack(fill="both", expand=True)
        # On remet en state="disabled" après la création (géré dans load_autosave ou initialisation)
        self.result_text.config(state="disabled")
        
    def roll_dice(self):
        try:
            num = self.num_dice_var.get()
            faces = self.num_faces_var.get()
            if num <= 0 or faces <= 1:
                raise ValueError
        except:
            messagebox.showerror("Erreur Magique", "Les lois de la physique refusent ces valeurs de dés.")
            return
            
        rolls = [random.randint(1, faces) for _ in range(num)]
        total = sum(rolls)
        motive = self.motive_var.get().strip()
        
        res_str = f"► Lancer : {num}d{faces}"
        if motive:
            res_str += f"  [{motive}]"
        res_str += f"""
  Détails : {rolls}
  TOTAL  : {total}
"""
        res_str += "-" * 50 + "\n"
        
        self.result_text.config(state="normal")
        self.result_text.insert("1.0", res_str)
        self.result_text.config(state="disabled")
        self.result_text.see("1.0")
        
    def setup_character_tab(self):
        char_frame = ttk.Frame(self.notebook)
        self.notebook.add(char_frame, text="2. Fiche de Personnage")
        
        btn_frame = ttk.Frame(char_frame)
        btn_frame.pack(fill="x", padx=5, pady=10)
        ttk.Button(btn_frame, text="💾 Sauvegarder", command=self.save_char).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="📂 Charger", command=self.load_char).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🗑️ Réinitialiser (Reset)", command=self.reset_char).pack(side="right", padx=10)
        
        scroll_frame = ScrollableFrame(char_frame)
        scroll_frame.pack(fill="both", expand=True)
        content = scroll_frame.scrollable_frame
        
        # Permettre aux colonnes de s'étendre
        content.columnconfigure(0, weight=1)
        
        row = 0
        
        profile_frame = ttk.LabelFrame(content, text=" Portrait du Tisseur ", padding=10)
        profile_frame.grid(row=row, column=0, sticky="ew", padx=15, pady=10)
        profile_frame.bind("<Configure>", self.on_profile_frame_resize)
        row += 1
        
        self.img_label = tk.Label(profile_frame, text="Aucun portrait sélectionné", bg=BG_COLOR, fg=TEXT_COLOR, font="UIFont")
        self.img_label.pack(pady=5, expand=True)
        
        ttk.Button(profile_frame, text="🖼️ Choisir une image", command=self.load_image).pack(pady=5)
        
        sections = {
            "Identité": ["PRÉNOM", "NOM", "RACE", "TISSEUR", "ALIGNEMENT"],
            "Ressources (Max / Actuel)": ["PV (MAX)", "PV (ACTUEL)", "EM (MAX)", "EM (ACTUEL)", "STABILITÉ TEMPORELLE (MAX)", "STABILITÉ TEMPORELLE (ACTUEL)"],
            "Statistiques Sociales": ["Charisme", "Persuasion", "Intuition", "Négociation", "Apprivoisement", "Chance"],
            "Caractéristiques Principales & Combat": ["Agilité", "Force", "Endurance", "Intelligence", "Précision", "D DU DESTIN", "Vitesse", "Furtivité", "Pilotage", "Perception", "Vitalité", "Psyché", "Force Avalio", "Résistance", "Maitrise des Armes", "Maitrise de la Magie", "Réactivité", "Résilience", "Capacité spéciale"],
            "Magie et Glyphes de Combat": ["MAGIE PRINCIPALE", "AFFINITÉ MAGIQUE", "MAGIE SECONDAIRE", "OFFENSIVE", "DÉFENSIVE", "SOUTIEN", "DISTANCE", "AUTRES GLYPHES"]
        }
        
        text_areas = [
            "HISTORIQUE DU PERSONNAGE", "REGISTRE DE VIE", "ARBRE GÉNÉALOGIQUE", 
            "ALLIÉS ET RELATIONS", "COMPÉTENCES DE NARRATION", "SOUVENIR PRÉCIEUX", 
            "INVENTAIRE", "EQUIPEMENT PRINCIPAL", "FINANCES", "MODIFICATEURS ET FAMILIERS"
        ]
        
        for sec_name, fields in sections.items():
            lf = ttk.LabelFrame(content, text=f" {sec_name} ", padding=10)
            lf.grid(row=row, column=0, sticky="ew", padx=15, pady=10)
            
            # Permet aux colonnes des entrées de s'étendre proportionnellement
            for i in range(6):
                lf.columnconfigure(i, weight=1)
                
            row += 1
            
            for i, field in enumerate(fields):
                r = i // 3
                c = (i % 3) * 2
                ttk.Label(lf, text=field).grid(row=r, column=c, sticky="e", padx=5, pady=5)
                var = tk.StringVar()
                ent = tk.Entry(lf, textvariable=var, bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font="TextFont")
                ent.grid(row=r, column=c+1, sticky="ew", padx=5, pady=5)
                self.entries[field] = var
        
        for ta in text_areas:
            lf = ttk.LabelFrame(content, text=f" {ta} ", padding=10)
            lf.grid(row=row, column=0, sticky="ew", padx=15, pady=10)
            row += 1
            
            text_widget = tk.Text(lf, height=4, font="TextFont", bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, wrap="word")
            text_widget.pack(fill="x", expand=True)
            self.entries[ta] = text_widget
            
    def setup_notes_tab(self):
        notes_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(notes_frame, text="3. Notes")
        
        # Espace plein écran pour les notes
        self.notes_text = tk.Text(notes_frame, font="TextFont", bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, wrap="word")
        self.notes_text.pack(fill="both", expand=True)
        
        # Ajouté aux entrées pour être sauvegardé avec la fiche et l'autosave
        self.entries["__NOTES_LIBRES__"] = self.notes_text
            
    def on_profile_frame_resize(self, event):
        if event.width != getattr(self, "last_profile_width", 0):
            self.last_profile_width = event.width
            # Debounce pour éviter de surcharger le processeur avec trop de redimensionnements
            if hasattr(self, "_resize_timer"):
                self.after_cancel(self._resize_timer)
            self._resize_timer = self.after(150, self.update_profile_image)

    def load_image(self):
        if not HAS_PIL:
            messagebox.showwarning(
                "Module manquant",
                "La bibliothèque 'Pillow' est requise pour afficher des images.\n"
                "Ouvrez votre terminal et tapez : pip install Pillow"
            )
            return
            
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.image_path = path
            self.original_pil_image = Image.open(self.image_path)
            self.update_profile_image()

    def update_profile_image(self):
        if not HAS_PIL:
            return
        if hasattr(self, 'original_pil_image') and self.original_pil_image is not None:
            try:
                img = self.original_pil_image.copy()
                
                # S'adapte à la largeur du LabelFrame parent
                frame_w = getattr(self, "last_profile_width", 500)
                
                # Taille dynamique (max 90% de la largeur, avec un ratio maximum pour ne pas prendre tout l'écran)
                w = int(frame_w * 0.9)
                h = int(w * 0.75)
                
                # Limites minimales et maximales de l'image
                w = max(100, min(w, 1200))
                h = max(100, min(h, 800))
                
                img.thumbnail((w, h))
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo, text="")
            except Exception as e:
                self.img_label.config(image="", text="Erreur de chargement")
        else:
            self.img_label.config(image="", text="Aucun portrait sélectionné")
            
    def reset_char(self):
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir vider TOUTE la fiche de personnage ainsi que les notes ?"):
            for key, widget in self.entries.items():
                if isinstance(widget, tk.StringVar):
                    widget.set("")
                elif isinstance(widget, tk.Text):
                    widget.delete("1.0", tk.END)
            
            self.image_path = None
            self.original_pil_image = None
            self.update_profile_image()
            messagebox.showinfo("Succès", "La fiche a été réinitialisée.")
            
    def save_char(self):
        data = {}
        for key, widget in self.entries.items():
            if isinstance(widget, tk.StringVar):
                data[key] = widget.get()
            elif isinstance(widget, tk.Text):
                data[key] = widget.get("1.0", tk.END).strip()
                
        data["__profile_image__"] = self.image_path
        
        # Obtenir le dossier où se situe le script/logiciel exécuté
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.join(base_dir, "fiche_personnage.json")
        
        file_path = filedialog.asksaveasfilename(initialdir=base_dir, initialfile="fiche_personnage.json", defaultextension=".json", filetypes=[("Fichiers JSON", "*.json")])
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo(
                "Succès",
                f"Grimoire sauvegardé avec succès dans :\n{file_path}"
            )
            
    def load_char(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = filedialog.askopenfilename(initialdir=base_dir, filetypes=[("Fichiers JSON", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for key, value in data.items():
                    if key in self.entries:
                        widget = self.entries[key]
                        if isinstance(widget, tk.StringVar):
                            widget.set(value)
                        elif isinstance(widget, tk.Text):
                            widget.delete("1.0", tk.END)
                            widget.insert("1.0", value)
                            
                self.image_path = data.get("__profile_image__", None)
                if self.image_path and os.path.exists(self.image_path):
                    self.original_pil_image = Image.open(self.image_path)
                else:
                    self.original_pil_image = None
                    self.image_path = None
                    
                self.update_profile_image()
                
                messagebox.showinfo("Succès", "Grimoire chargé avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"Une perturbation magique a eu lieu lors du chargement : {e}")

    def get_autosave_path(self):
        # Ne pas écrire à côté du .exe : avec PyInstaller --onefile,
        # cet emplacement peut être temporaire ou non inscriptible.
        appdata = os.environ.get("APPDATA")
        if appdata:
            save_dir = os.path.join(appdata, "THE_LAST_HERO")
        else:
            save_dir = os.path.join(os.path.expanduser("~"), ".the_last_hero")

        os.makedirs(save_dir, exist_ok=True)
        return os.path.join(save_dir, "grimoire_autosave.json")

    def save_autosave(self):
        data = {
            "dice": {
                "num": self.num_dice_var.get(),
                "faces": self.num_faces_var.get(),
                "motive": self.motive_var.get(),
                "history": self.result_text.get("1.0", tk.END)
            },
            "entries": {},
            "image_path": self.image_path
        }
        
        for key, widget in self.entries.items():
            if isinstance(widget, tk.StringVar):
                data["entries"][key] = widget.get()
            elif isinstance(widget, tk.Text):
                data["entries"][key] = widget.get("1.0", tk.END)
                
        try:
            path = self.get_autosave_path()
            temp_path = path + ".tmp"

            # Écriture atomique pour éviter un JSON partiellement écrit.
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, path)
        except Exception as e:
            print(f"Erreur lors de l'autosave : {e}")

    def schedule_autosave(self):
        # Sauvegarde pendant l'utilisation, toutes les 10 secondes.
        if getattr(self, "_closing", False):
            return

        self.save_autosave()
        self._autosave_job = self.after(10000, self.schedule_autosave)

    def load_autosave(self):
        path = self.get_autosave_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Restaurer les dés
                dice_data = data.get("dice", {})
                self.num_dice_var.set(dice_data.get("num", 1))
                self.num_faces_var.set(dice_data.get("faces", 20))
                self.motive_var.set(dice_data.get("motive", ""))
                
                history = dice_data.get("history", "")
                if history:
                    self.result_text.config(state="normal")
                    self.result_text.delete("1.0", tk.END)
                    self.result_text.insert("1.0", history)
                    self.result_text.config(state="disabled")
                    
                # Restaurer les fiches & notes
                entries_data = data.get("entries", {})
                for key, value in entries_data.items():
                    if key in self.entries:
                        widget = self.entries[key]
                        if isinstance(widget, tk.StringVar):
                            widget.set(value)
                        elif isinstance(widget, tk.Text):
                            widget.delete("1.0", tk.END)
                            widget.insert("1.0", value)
                            
                # Restaurer l'image
                self.image_path = data.get("image_path", None)
                if self.image_path and os.path.exists(self.image_path):
                    self.original_pil_image = Image.open(self.image_path)
                else:
                    self.original_pil_image = None
                    self.image_path = None
                self.update_profile_image()
            except Exception as e:
                print(f"Erreur lors du chargement de l'autosave : {e}")

    def on_close(self):
        self._closing = True

        if getattr(self, "_autosave_job", None) is not None:
            try:
                self.after_cancel(self._autosave_job)
            except tk.TclError:
                pass
            self._autosave_job = None

        # Dernière sauvegarde avant de quitter.
        self.save_autosave()
        self.destroy()

if __name__ == "__main__":
    app = RPGAssistant()
    app.mainloop()
