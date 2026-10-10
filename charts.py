"""Tiny dependency-free SVG chart renderer (replaces matplotlib in the web port)."""
from xml.sax.saxutils import escape

WIDTH, HEIGHT, PAD = 640, 320, 50
GOLD = "#d4af37"


def _frame(title, ylabel, ymin, ymax, body):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" font-family="Arial, sans-serif">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#1a1a1a"/>',
        f'<text x="{WIDTH / 2}" y="24" fill="{GOLD}" font-size="16" '
        f'text-anchor="middle">{escape(title)}</text>',
        f'<text x="14" y="{HEIGHT / 2}" fill="#ddd" font-size="12" text-anchor="middle" '
        f'transform="rotate(-90 14 {HEIGHT / 2})">{escape(ylabel)}</text>',
        f'<line x1="{PAD}" y1="{HEIGHT - PAD}" x2="{WIDTH - PAD}" y2="{HEIGHT - PAD}" '
        'stroke="#888"/>',
        f'<line x1="{PAD}" y1="{PAD}" x2="{PAD}" y2="{HEIGHT - PAD}" stroke="#888"/>',
        f'<text x="{PAD - 6}" y="{HEIGHT - PAD}" fill="#ddd" font-size="11" '
        f'text-anchor="end">{ymin:g}</text>',
        f'<text x="{PAD - 6}" y="{PAD + 4}" fill="#ddd" font-size="11" '
        f'text-anchor="end">{ymax:g}</text>',
    ]
    parts.extend(body)
    parts.append("</svg>")
    return "".join(parts)


def _y(value, ymin, ymax):
    span = (ymax - ymin) or 1
    return HEIGHT - PAD - (value - ymin) / span * (HEIGHT - 2 * PAD)


def bar_chart_svg(title, labels, values, ylabel="", ymax=100):
    n = max(len(values), 1)
    slot = (WIDTH - 2 * PAD) / n
    body = []
    for i, (label, value) in enumerate(zip(labels, values)):
        x = PAD + i * slot + slot * 0.15
        y = _y(value, 0, ymax)
        body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot * 0.7:.1f}" '
            f'height="{HEIGHT - PAD - y:.1f}" fill="{GOLD}"/>'
        )
        body.append(
            f'<text x="{x + slot * 0.35:.1f}" y="{HEIGHT - PAD + 16}" fill="#ddd" '
            f'font-size="11" text-anchor="middle">{escape(str(label))}</text>'
        )
    return _frame(title, ylabel, 0, ymax, body)


def line_chart_svg(title, labels, values, ylabel="", ymin=0, ymax=None, color=GOLD):
    if ymax is None:
        ymax = max(values) if values else 1
    if ymax == ymin:
        ymax = ymin + 1
    n = len(values)
    step = (WIDTH - 2 * PAD) / max(n - 1, 1)
    points = []
    body = []
    for i, (label, value) in enumerate(zip(labels, values)):
        x = PAD + i * step if n > 1 else WIDTH / 2
        y = _y(value, ymin, ymax)
        points.append(f"{x:.1f},{y:.1f}")
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        body.append(
            f'<text x="{x:.1f}" y="{HEIGHT - PAD + 16}" fill="#ddd" font-size="10" '
            f'text-anchor="end" transform="rotate(-30 {x:.1f} {HEIGHT - PAD + 16})">'
            f'{escape(str(label))}</text>'
        )
    body.insert(0, f'<polyline points="{" ".join(points)}" fill="none" '
                   f'stroke="{color}" stroke-width="2"/>')
    return _frame(title, ylabel, ymin, ymax, body)
