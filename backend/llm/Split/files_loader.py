import json
from pathlib import Path

import PyPDF2
from bs4 import BeautifulSoup
from docx import Document


class FileLoader:
    def _clean_unicode_text(self, text: str) -> str:
        cleaned_chars = []
        for char in text:
            try:
                char.encode("utf-8")
                cleaned_chars.append(char)
            except UnicodeEncodeError:
                continue
        return "".join(cleaned_chars)

    def load_file(self, file_path: str) -> str:
        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".pdf":
            text = self._load_pdf(file_path)
            return text
        elif file_extension in {".docx", ".doc"}:
            text = self._load_word(file_path)
            return text
        elif file_extension == ".md":
            text = self._load_markdown(file_path)
            return text
        elif file_extension == ".txt":
            text = self._load_text(file_path)
            return text
        elif file_extension == ".json":
            text = self._load_json(file_path)
            return text
        elif file_extension == ".html":
            text = self._load_html(file_path)
            return text
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")

    def _load_pdf(self, file_path: str) -> str:
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)

            if pdf_reader.is_encrypted:
                pdf_reader.decrypt("")

            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            return self._clean_unicode_text(text.strip())

    def _load_word(self, file_path: str) -> str:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return self._clean_unicode_text(text.strip())

    def _load_markdown(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return self._clean_unicode_text(content.strip())

    def _load_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return self._clean_unicode_text(content.strip())

    def _load_json(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        def json_to_text(obj, prefix=""):
            if isinstance(obj, dict):
                lines = []
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        lines.append(f"{prefix}{key}:")
                        lines.append(json_to_text(value, prefix + "  "))
                    else:
                        lines.append(f"{prefix}{key}: {value}")
                return "\n".join(lines)
            elif isinstance(obj, list):
                lines = []
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        lines.append(f"{prefix}[{i}]:")
                        lines.append(json_to_text(item, prefix + "  "))
                    else:
                        lines.append(f"{prefix}[{i}]: {item}")
                return "\n".join(lines)
            else:
                return str(obj)

        return self._clean_unicode_text(json_to_text(data))

    def _load_html(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return self._clean_unicode_text("\n".join(lines))
