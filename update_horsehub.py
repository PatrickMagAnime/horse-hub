import os
import json
import subprocess
import shutil

# Konfiguration
RAW_INPUT_FOLDER = 'processed' 
FINAL_OUTPUT_FOLDER = 'sources' 
METADATA_FILE = 'metadata.json'

VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.mpeg', '.ts'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS.union(IMAGE_EXTENSIONS)

# --- FFmpeg Funktionen ---

# Funktion für Videos (NUR WebM Konvertierung)
def run_ffmpeg_video_command(input_path, output_webm_path):
    """Führt FFmpeg-Befehle für WebM-Konvertierung aus (ohne Thumbnail)."""
    # --- 1. WebM Konvertierung (Primär) ---
    webm_command = [
        'ffmpeg', '-i', input_path,
        '-vcodec', 'libvpx-vp9', '-crf', '35', '-b:v', '0', 
        '-an',                        # Audio entfernen
        '-y',
        output_webm_path
    ]
    try:
        subprocess.run(webm_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"WebM-Fehler bei {os.path.basename(input_path)}")
        return False
    except FileNotFoundError:
        print("FEHLER: FFmpeg nicht gefunden.")
        return False
    return True

# NEUE Funktion für Bilder (Konvertierung zu WebP)
def run_ffmpeg_image_command(input_path, output_webp_path):
    """Konvertiert Bilder (JPG, PNG) zu WebP."""
    
    # -q:v 80 ist eine gute Qualität/Kompromiss für WebP
    image_command = [
        'ffmpeg',
        '-i', input_path,
        '-vcodec', 'libwebp',
        '-q:v', '80',
        '-y',
        output_webp_path
    ]
    try:
        subprocess.run(image_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        print(f"WebP-Konvertierungsfehler bei {os.path.basename(input_path)}")
        return False
    except FileNotFoundError:
        print("FEHLER: FFmpeg nicht gefunden.")
        return False

# --- Hauptfunktion ---

def main():
    if not os.path.exists(FINAL_OUTPUT_FOLDER):
        os.makedirs(FINAL_OUTPUT_FOLDER)
        
    if not os.path.exists(RAW_INPUT_FOLDER):
        print(f"ACHTUNG: Der Rohdaten-Ordner '{RAW_INPUT_FOLDER}' existiert nicht. Es gibt nichts zu verarbeiten.")
        os.makedirs(RAW_INPUT_FOLDER)
        return 

    # 2. Existierende Metadata laden (Unverändert)
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"tags": ["funny", "cute"], "assignments": {}, "files": []}
    else:
        data = {"tags": ["funny", "cute"], "assignments": {}, "files": []}
    
    if "assignments" not in data: data["assignments"] = {}

    
    # 3. Dateien verarbeiten
    final_files = [] 
    raw_files_list = os.listdir(RAW_INPUT_FOLDER)

    # Statistik-Zähler für kompakte Ausgabe
    stats = {
        'videos': {'added': 0, 'updated': 0},
        'images': {'added': 0, 'updated': 0},
        'gifs': {'added': 0, 'updated': 0},
    }
    deleted_count = 0

    if not raw_files_list:
        print(f"Der Rohdaten-Ordner '{RAW_INPUT_FOLDER}' ist leer.")

    
    for filename in raw_files_list:
        input_path = os.path.join(RAW_INPUT_FOLDER, filename)
        
        if os.path.isdir(input_path) or filename.startswith('.'):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            # Ignoriere unbekannte Dateitypen (keine laute Ausgabe)
            continue

        base_name = os.path.splitext(filename)[0]
        
        if ext in VIDEO_EXTENSIONS:
            # Video Verarbeitung: Generiere NUR WebM
            
            output_webm_filename = base_name + '.webm'
            # output_thumb_filename wurde entfernt
            
            output_webm_path = os.path.join(FINAL_OUTPUT_FOLDER, output_webm_filename)
            # output_thumb_path wurde entfernt
            
            # Überprüfe die Änderungszeit
            needs_processing = True
            if os.path.exists(output_webm_path):
                if os.path.getmtime(output_webm_path) >= os.path.getmtime(input_path):
                    needs_processing = False

            if needs_processing:
                # Kurze Ausgabe: welche Datei gerade verarbeitet wird
                print(f"Verarbeite Video: {filename}")
                # unterscheide neu vs. update
                was_existing = os.path.exists(output_webm_path)
                if run_ffmpeg_video_command(input_path, output_webm_path):
                    final_files.append(output_webm_filename)
                    # Counters: erhöht werden weiter unten
                    if was_existing:
                        stats['videos']['updated'] += 1
                    else:
                        stats['videos']['added'] += 1
            else:
                final_files.append(output_webm_filename)
                
        elif ext in IMAGE_EXTENSIONS:
            # Bild Verarbeitung
            
            if ext in {'.jpg', '.jpeg', '.png'}:
                # Konvertiere JPG/PNG zu WebP
                output_webp_filename = base_name + '.webp'
                output_webp_path = os.path.join(FINAL_OUTPUT_FOLDER, output_webp_filename)
                
                # Überprüfe die Änderungszeit
                needs_processing = True
                if os.path.exists(output_webp_path):
                    if os.path.getmtime(output_webp_path) >= os.path.getmtime(input_path):
                        needs_processing = False
                if needs_processing:
                    print(f"Verarbeite Bild: {filename}")
                    was_existing = os.path.exists(output_webp_path)
                    if run_ffmpeg_image_command(input_path, output_webp_path):
                        final_files.append(output_webp_filename)
                        if was_existing:
                            stats['images']['updated'] += 1
                        else:
                            stats['images']['added'] += 1
                else:
                    final_files.append(output_webp_filename)
                    
            elif ext in {'.gif', '.webp'}:
                # GIFs und bereits vorhandene WebP-Dateien nur kopieren
                output_path = os.path.join(FINAL_OUTPUT_FOLDER, filename)
                
                needs_copy = (not os.path.exists(output_path)) or (os.path.getmtime(input_path) > os.path.getmtime(output_path))
                if needs_copy:
                    if ext == '.gif':
                        print(f"Kopiere GIF: {filename}")
                    else:
                        print(f"Kopiere Bild/WebP: {filename}")
                    was_existing = os.path.exists(output_path)
                    shutil.copy2(input_path, output_path)
                    if ext == '.gif':
                        if was_existing:
                            stats['gifs']['updated'] += 1
                        else:
                            stats['gifs']['added'] += 1
                    else:
                        # treat .webp in this bucket as images
                        if was_existing:
                            stats['images']['updated'] += 1
                        else:
                            stats['images']['added'] += 1

                final_files.append(filename)

    # 4. Cleanup alter verarbeiteter Dateien im FINAL_OUTPUT_FOLDER
    
    files_in_output = os.listdir(FINAL_OUTPUT_FOLDER)
    for processed_file in files_in_output:
        # Lösche alte verarbeitete Dateien, die nicht mehr in final_files sind.
        if os.path.isfile(os.path.join(FINAL_OUTPUT_FOLDER, processed_file)) and processed_file not in final_files:
             os.remove(os.path.join(FINAL_OUTPUT_FOLDER, processed_file))
             deleted_count += 1


    # 5. Metadaten abgleichen und speichern (Unverändert)
    final_files.sort()
    data["files"] = final_files
    
    orphaned_assignments = [f for f in data["assignments"] if f not in final_files]
    for orphan in orphaned_assignments:
        del data["assignments"][orphan]

    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Kompakte Zusammenfassung
    print(f"\nVerarbeitung abgeschlossen. Gesamt-Ausgabedateien: {len(final_files)}")
    print(f"Hinzugefügt:  Videos {stats['videos']['added']}, Bilder {stats['images']['added']}, GIFs {stats['gifs']['added']}")
    print(f"Aktualisiert: Videos {stats['videos']['updated']}, Bilder {stats['images']['updated']}, GIFs {stats['gifs']['updated']}")
    if deleted_count:
        print(f"Gelöschte alte Dateien: {deleted_count}")
    print("Die HTML-Seite lädt jetzt aus dem '/sources' Ordner.")


if __name__ == "__main__":
    main()