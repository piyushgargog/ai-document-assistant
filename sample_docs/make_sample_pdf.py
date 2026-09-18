"""Dev-only helper: generates a small multi-page demo PDF for local testing.

This is a minimal synthetic sample document, not a real-world document —
it exists purely to exercise the pipeline during development and in
automated tests. For a more realistic demo, see the real-world PDF
validation described in DECISIONS.md and README.md.
"""

import pymupdf

PAGES = [
    "The Solar System\n\n"
    "The Solar System consists of the Sun and the objects that orbit it, "
    "including eight planets, their moons, dwarf planets, asteroids, and "
    "comets. The Sun contains about 99.8% of the Solar System's total mass.",
    "The Inner Planets\n\n"
    "Mercury, Venus, Earth, and Mars are known as the inner or terrestrial "
    "planets. They are relatively small and have rocky surfaces. Earth is "
    "the only known planet to support life, largely due to liquid water and "
    "a stable atmosphere.",
    "The Outer Planets\n\n"
    "Jupiter, Saturn, Uranus, and Neptune are the outer or gas/ice giant "
    "planets. Jupiter is the largest planet in the Solar System, with a "
    "mass more than twice that of all other planets combined. Saturn is "
    "famous for its prominent ring system.",
    "Moons and Exploration\n\n"
    "Many planets have natural satellites called moons. Earth has one moon. "
    "Saturn has over 140 confirmed moons, the most of any planet. Missions "
    "such as Voyager 1 and 2, launched in 1977, have traveled beyond the "
    "Solar System into interstellar space.",
]


def main():
    doc = pymupdf.open()
    for text in PAGES:
        page = doc.new_page()
        rect = pymupdf.Rect(72, 72, page.rect.width - 72, page.rect.height - 72)
        page.insert_textbox(rect, text, fontsize=12)
    doc.save("sample_docs/sample.pdf")
    doc.close()
    print("Wrote sample_docs/sample.pdf")


if __name__ == "__main__":
    main()
