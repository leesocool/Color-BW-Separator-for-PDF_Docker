<img src="./serverless_handler/static/favicon.png" alt="Logo" width="100"/>

# Color and Black & White Separator for PDF

This tool separates color and black & white pages from a PDF file into two separate PDF files. It is packaged as a Docker image with a browser-based web UI.

## Languages
<a href="./README-zh_cn.md">简体中文</a>

## Quick Start with Docker

### Option 1 – Docker Compose (recommended)

```bash
docker compose up --build
```

Then open **http://localhost:9000** in your browser.

### Option 2 – Plain Docker

```bash
# Build
docker build -t pdf-separator .

# Run (output files are saved to ./data on the host)
docker run -p 9000:9000 -v "$(pwd)/data:/data" pdf-separator
```

Then open **http://localhost:9000** in your browser.

## Usage

1. **Upload** – Select a PDF file (up to 512 MB) and click *上传文件*.
2. **Process** – Adjust parameters if needed and click *开始处理*. A progress bar shows page-by-page progress.
3. **Download** – Click the download buttons to save the color or black-and-white PDF to your computer.

## Persistent Storage

Processed files are saved inside the container at:

| Path | Contents |
|------|----------|
| `/data/input/` | Uploaded PDFs (deleted automatically after processing) |
| `/data/output/` | Separated PDFs (`{session}_color.pdf`, `{session}_bw.pdf`) |

When using the volume mount (`-v ./data:/data`), all output PDFs are persisted on the host machine under `./data/output/`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Double-sided mode | ✓ | Includes adjacent pages when a color page is detected, so double-sided prints separate correctly. |
| Saturation threshold | 0.35 | Lower = more pages classified as color. |
| Color fraction threshold | 0.001 | Lower = more pages classified as color. |

## Development – Run without Docker

```bash
pip install -r requirements.txt
python serverless_handler/ws_server.py
```

The server listens on `http://0.0.0.0:9000` by default. Override the data directory with the `DATA_DIR` environment variable.

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

