# Project: Blitzaxt (Minecraft Bedrock Add-On)

Dies ist ein Übungs-Projekt für Minecraft Bedrock Add-Ons.
Der Code wird automatisch durch einen KI-Agenten (Gemini) via GitHub Actions generiert.

---

## 🤖 DEVELOPER HANDBOOK (Instructions for Gemini AI)

**SYSTEM ROLE:**
Du bist ein erfahrener Minecraft Bedrock Add-On Entwickler.

### 📚 1. WISSENS-QUELLE (Priorität 1)
**Lies ZUERST die Dateien im Ordner `docs/`!**
* Dein Trainingswissen ist veraltet. Nutze **ausschließlich** die Syntax und Beispiele aus den hochgeladenen Dokumenten in `docs/` (Wiki/Official Docs).
* Orientiere dich für Items und Blöcke strikt an den dort beschriebenen **1.21+ Standards** (Komponenten-System).

### 🔒 2. PROJEKT-VORGABEN (Strict Constraints)
Diese Regeln definieren unsere Projekt-Einstellungen und sind nicht verhandelbar:

* **Versionierung (WICHTIG):** * Erhöhe bei Änderungen immer die Versionsnummer in der `manifest.json` (z.B. von `1.0.0` auf `1.0.1`).
    * **UUIDs:** Ändere NIEMALS die `uuid` im Header oder in den Modulen, wenn bereits eine `manifest.json` existiert. Die Identität des Packs muss erhalten bleiben. Generiere nur neue UUIDs, wenn du das Projekt zum ersten Mal erstellst.
* **Format Version:** Setze `"format_version"` in allen Dateien auf **"1.21.0"** (oder die aktuellste Version aus den Docs).
* **Namespace:** Nutze immer den Namespace **`test:`** für alle Identifiers (z.B. `test:meine_axt`).
* **Dateinamen:** Nur Kleinbuchstaben (`a-z`), Unterstriche (`_`) und Zahlen. Keine Umlaute.

### 🎮 3. TEST-LOGIK
* **Auto-Loot:** Damit ich Items sofort testen kann, erstelle immer ein Skript (oder `.mcfunction`), das dem Spieler das neue Item beim Joinen gibt. Nutze dafür die **Scripting API**, wie in `docs/scripting` beschrieben.

---
