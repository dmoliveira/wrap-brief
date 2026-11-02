"""Static shell structure and actual-usage WCAG contrast checks."""

import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"


class Document(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))


def luminance(color: str) -> float:
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.document = Document(cls.html)

    def test_document_has_accessible_landmarks_and_heading_order(self) -> None:
        elements = self.document.elements
        counts = Counter(tag for tag, _ in elements)
        for tag in ("html", "head", "title", "body", "header", "nav", "main", "footer", "h1"):
            self.assertEqual(counts[tag], 1, tag)
        self.assertEqual(
            [tag for tag, _ in elements if re.fullmatch(r"h[1-6]", tag)], ["h1", "h2", "h2"]
        )
        self.assertIn(("html", {"lang": "en"}), elements)
        self.assertIn(("main", {"id": "main", "tabindex": "-1"}), elements)
        self.assertTrue(
            any(tag == "meta" and attrs.get("name") == "viewport" for tag, attrs in elements)
        )

    def test_skip_link_is_first_link_and_all_fragments_exist_once(self) -> None:
        elements = self.document.elements
        ids = [attrs["id"] for _, attrs in elements if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        links = [attrs for tag, attrs in elements if tag == "a"]
        self.assertEqual(links[0]["href"], "#main")
        self.assertEqual(links[0]["class"], "skip-link")
        for attrs in links:
            href = attrs["href"]
            self.assertIsNotNone(href)
            self.assertTrue(href.startswith("#"))
            self.assertIn(href[1:], ids)
            self.assertNotIn("target", attrs)
        for tag, attrs in elements:
            if tag == "section":
                self.assertIn(attrs["aria-labelledby"], ids)
                self.assertEqual(attrs["tabindex"], "-1")

    def test_shell_is_static_local_only_and_has_no_fake_news_or_timestamp(self) -> None:
        elements = self.document.elements
        self.assertEqual(
            [attrs["href"] for tag, attrs in elements if tag == "link"], ["styles.css"]
        )
        self.assertFalse(
            {tag for tag, _ in elements}
            & {"script", "iframe", "img", "form", "time", "article", "style"}
        )
        self.assertNotRegex(
            self.css, r"(?i)@import|url\(|@font-face|animation|transition|overflow\s*:\s*hidden"
        )
        for _, attrs in elements:
            self.assertFalse(any(name.startswith("on") for name in attrs))
            self.assertNotIn("style", attrs)
        self.assertIn("Offline design preview", self.html)
        self.assertIn("No news has been collected or published.", self.html)
        self.assertIn("None enabled", self.html)
        self.assertIn("Not affiliated with", self.html)

    def test_actual_text_and_focus_token_usage_has_sufficient_contrast(self) -> None:
        tokens = dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-f]{6})\s*;", self.css))
        self.assertEqual(
            set(tokens), {"paper", "surface", "ink", "muted", "accent", "tint", "rule"}
        )
        for text in ("ink", "muted", "accent"):
            for background in ("paper", "surface"):
                with self.subTest(text=text, background=background):
                    self.assertGreaterEqual(contrast(tokens[text], tokens[background]), 4.5)
        self.assertGreaterEqual(contrast(tokens["accent"], tokens["tint"]), 4.5)
        for surface in ("paper", "surface"):
            self.assertGreaterEqual(contrast(tokens["accent"], tokens[surface]), 3)

    def test_css_preserves_reflow_focus_and_touch_targets(self) -> None:
        self.assertIn("overflow-wrap: anywhere", self.css)
        self.assertIn("min-height: 44px", self.css)
        self.assertIn("min-width: 44px", self.css)
        self.assertIn("a:focus-visible", self.css)
        self.assertIn("outline: 3px solid var(--accent)", self.css)
        self.assertIn(".skip-link:focus { transform: none; }", self.css)
        self.assertIn("@media (forced-colors: active)", self.css)
        self.assertNotRegex(self.css, r"(?i)(?:min-)?width:\s*[3-9][0-9]{2}px")


if __name__ == "__main__":
    unittest.main()
