from escpos.printer import Network
import textwrap

PRINTER_IP = "192.168.1.245"

LINE_WIDTH = 42

HASH = "#" * LINE_WIDTH
STAR = "*" * LINE_WIDTH

def print_header(p):
    p.set(align="center", font="a", bold=False, width=1, height=1)
    p.text(HASH + "\n")
    p.set(align="center", font="a", bold=True, width=1, height=1)
    p.text("it's not about\n")
    p.set(align="center", font="a", bold=False, width=1, height=1)
    p.text(HASH + "\n")
    p.text("\n")

def print_response(p, response):
    full = "it's not about " + response
    wrapped = textwrap.fill(full, width=LINE_WIDTH)
    indented = "\n".join("  " + line for line in wrapped.split("\n"))
    p.set(align="left", font="a", bold=False, width=1, height=1)
    p.text(indented + "\n")

def print_divider(p):
    p.set(align="center", font="a", bold=False, width=1, height=1)
    p.text(STAR + "\n")

def main():
    p = Network(PRINTER_IP)
    p._raw(b'\x1d\x57\x40\x02')
    ##set paper width
    print_header(p)

    test_responses = [
        "a school where you lived as a teenager",
        "a wall on which there used to be a golden eagle",
        "breads, meats and vegetables",
    ]

    for response in test_responses:
        print_response(p, response)
        p.text("\n")
    p.text("\n")
    print_divider(p)
    p.set(align="center", font="b", bold=False, width=1, height=1)
    p.text("MAR 02, 2026 2:45PM\n")
    p.text(STAR + "\n")
    p.text("\n" * 10)

if __name__ == "__main__":
    main()