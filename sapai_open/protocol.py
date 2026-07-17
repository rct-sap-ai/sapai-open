"""Protocol loader. Reads a clinical-trial protocol file and turns it into
plain markdown text.

Supported inputs: .txt / .md (read as-is) and .pdf / .doc / .docx
(converted to markdown via MarkItDown). Converting everything to markdown
means the rest of the pipeline only ever has to deal with one text format,
regardless of what the user uploaded.
"""

from __future__ import annotations

from pathlib import Path

from markitdown import MarkItDown

# Extensions we know how to turn into text.
PLAIN_TEXT_EXTENSIONS = {".txt", ".md"}
CONVERTIBLE_EXTENSIONS = {".pdf", ".doc", ".docx"}


class Protocol:
    """Load a clinical trial protocol from a file into markdown text."""

    def __init__(self, file_path: str):
        if not file_path:
            raise ValueError("file_path must be provided")

        self.file_path = file_path
        suffix = Path(file_path).suffix.lower()

        if suffix in PLAIN_TEXT_EXTENSIONS:
            # Already plain text / markdown - just read it.
            self.protocol_txt = Path(file_path).read_text(encoding="utf-8", errors="replace")
        elif suffix in CONVERTIBLE_EXTENSIONS:
            # PDF / DOC / DOCX - convert to markdown with MarkItDown.
            self.protocol_txt = MarkItDown().convert(file_path).text_content
            # Save the converted markdown next to the original file, for reuse/debugging.
            Path(file_path).with_suffix(".md").write_text(self.protocol_txt, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file extension: {suffix}")

    def save_protocol_txt(self, protocol_txt_path: str) -> None:
        """Save the protocol text as a .md file at the given path."""
        Path(protocol_txt_path).with_suffix(".md").write_text(self.protocol_txt, encoding="utf-8")


def load_protocol_from_upload(uploaded_file) -> str:
    """Read a Streamlit UploadedFile (or any file-like with .read() and .name).

    Returns the protocol text as markdown. Writes to a tempfile internally so
    Protocol() (which expects a path) keeps working uniformly across all
    supported formats.
    """
    import tempfile

    suffix = Path(getattr(uploaded_file, "name", "")).suffix.lower() or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    return Protocol(tmp_path).protocol_txt
