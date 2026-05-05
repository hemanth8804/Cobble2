# 🗂 AI File Sorter

Offline AI-powered file organizer. Drag in 20+ files → Gemma 2B reads their content → automatically sorts them into smart folder hierarchies.

---

## How It Works

1. You drop files into the app (PDFs, DOCX, TXT, images, code, spreadsheets...)
2. The app extracts the first ~2000 characters of text from each file
3. Sends that to **Gemma 2B** running locally via **Ollama**
4. Gemma classifies the file into a hierarchy like `History / Ancient / Wars`
5. The app creates folders and copies (or moves) the files accordingly

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Gemma 2B model pulled

---

## Setup (One Time)

### 1. Install Ollama
Download from [https://ollama.com](https://ollama.com) and run it.

### 2. Pull Gemma 2B
```bash
ollama pull gemma2:2b
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
python run.py
```

This opens a browser at `http://localhost:7432` automatically.

---

## Using the App

1. **Drop files** — drag any files into the drop zone, or click to browse
2. **Set output folder** — where sorted files will go (e.g. `C:\Users\You\Sorted`)
3. **Choose options** — copy or move files, model selection
4. **Click Start Sorting** — watch it work file by file
5. **Done** — see the category breakdown and open the output folder

---

## Folder Hierarchy Examples

| File | Result Folder |
|------|--------------|
| `ancient_rome_history.pdf` | `History / Ancient / Roman Empire` |
| `invoice_acme_2024.pdf` | `Finance / Invoices / 2024` |
| `snake_game.py` | `Programming / Python / Games` |
| `chest_xray.jpg` | `Medical / Radiology / Chest` |
| `resume_john.docx` | `Career / Resumes` |
| `dna_research.pdf` | `Science / Biology / Genetics` |

---

## Supported File Types

| Type | Details |
|------|---------|
| PDF | Extracts first 3 pages of text |
| DOCX / DOC | Full paragraph extraction |
| XLSX / XLS | First 20 rows of first 2 sheets |
| PPTX | First 5 slides text |
| TXT, MD, CSV, JSON, HTML | Full text read |
| Code files | .py .js .ts .java .cpp etc. |
| Images | Classified by filename + extension |
| ZIP | Classified by contents list |

---

## CLI Usage (No UI)

```bash
python backend/sorter.py file1.pdf file2.docx notes.txt -o /path/to/output
```

Options:
- `-o / --output` — output directory (required)
- `--model` — Ollama model (default: `gemma2:2b`)
- `--url` — Ollama URL (default: `http://localhost:11434`)
- `--move` — move files instead of copying

---

## Troubleshooting

**Ollama not found**
- Make sure Ollama is running (check system tray or run `ollama serve`)
- Default URL is `http://localhost:11434`

**gemma2:2b not found**
- Run: `ollama pull gemma2:2b`
- Or use another model like `llama3.2:3b`

**Files not sorting correctly**
- Try `gemma2:9b` for better accuracy on complex files
- Check if the file has extractable text (scanned PDFs won't work without OCR)

**Slow performance**
- Gemma 2B is fast (~2-5 seconds per file on most machines)
- For 20 files expect ~1-2 minutes total
- You can run in parallel by editing `sorter.py` to use `ThreadPoolExecutor`

---

## Project Structure

```
ai-file-sorter/
├── run.py               ← Start here
├── requirements.txt
├── backend/
│   ├── server.py        ← Flask web server
│   └── sorter.py        ← AI classification engine
└── frontend/
    └── index.html       ← Web UI
```

---

## License

MIT — use freely, modify as needed.
