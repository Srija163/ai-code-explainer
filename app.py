from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

SUPPORTED_LANGUAGES = ["Python"]


# --------- Simple rule-based explainer (NO EXECUTION) ----------
def explain_line(line: str):
    s = line.strip()
    if not s:
        return "Empty line."

    if s.startswith("#"):
        return "This is a comment for explanation/documentation."

    if s.startswith("import ") or s.startswith("from "):
        return "Imports modules/libraries needed for the program."

    if s.startswith("def "):
        return "Defines a function (reusable block of code)."

    if s.startswith("class "):
        return "Defines a class (blueprint for objects)."

    if s.startswith(("if ", "elif ")):
        return "Checks a condition and runs the block only if the condition is true."

    if s == "else:" or s.startswith("else:"):
        return "Runs this block when previous if/elif conditions are false."

    if s.startswith("for "):
        return "Starts a loop that repeats for each item in a sequence."

    if s.startswith("while "):
        return "Starts a loop that repeats while the condition remains true."

    if s.startswith("return "):
        return "Returns a value from the function and stops its execution."

    if s.startswith("print(") or s.startswith("print "):
        return "Displays output to the user."

    if "input(" in s:
        return "Takes input from the user (keyboard)."

    if re.search(r"^\w+\s*=\s*.+", s):
        return "Assigns a value/expression to a variable."

    if s.startswith(("break", "continue")):
        return "Controls the loop flow (break stops loop, continue skips to next iteration)."

    if s.startswith(("try:", "except", "finally")):
        return "Handles errors using try/except to prevent program crashing."

    # fallback
    return "General statement/expression. It performs an operation or calls a function."


def basic_complexity_estimate(code_lines):
    """
    Very basic:
    - count loop nesting level using indentation + keywords for/while
    - estimate O(n^k) where k = max nesting
    """
    max_nesting = 0
    stack = []  # store indentation levels for loops

    for raw in code_lines:
        line = raw.rstrip("\n")
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        # pop loops that ended
        while stack and indent <= stack[-1]:
            stack.pop()

        if s.startswith("for ") or s.startswith("while "):
            stack.append(indent)
            max_nesting = max(max_nesting, len(stack))

    if max_nesting == 0:
        return "Time: O(1) to O(n) depending on operations (no explicit loops detected).", "Space: O(1) (basic estimate)."
    if max_nesting == 1:
        return "Time: O(n) (single loop detected).", "Space: O(1) to O(n) depending on stored data."
    if max_nesting == 2:
        return "Time: O(n^2) (nested loops detected).", "Space: O(1) to O(n) depending on stored data."
    return f"Time: O(n^{max_nesting}) (max loop nesting = {max_nesting}).", "Space: O(1) to O(n) depending on stored data."


def generate_summary(code: str):
    lines = code.splitlines()
    s = code

    has_func = bool(re.search(r"^\s*def\s+\w+\s*\(", s, re.MULTILINE))
    has_class = bool(re.search(r"^\s*class\s+\w+", s, re.MULTILINE))
    has_if = bool(re.search(r"^\s*if\s+", s, re.MULTILINE))
    has_loop = bool(re.search(r"^\s*(for|while)\s+", s, re.MULTILINE))
    has_input = "input(" in s
    has_print = "print(" in s

    parts = []
    if has_class: parts.append("uses classes")
    if has_func: parts.append("defines functions")
    if has_loop: parts.append("uses loops")
    if has_if: parts.append("uses conditions")
    if has_input: parts.append("takes user input")
    if has_print: parts.append("prints output")

    if not parts:
        overall = "This code contains basic statements. It may compute a result or call functions."
    else:
        overall = "This code " + ", ".join(parts) + "."

    t, sp = basic_complexity_estimate(lines)

    return overall, t, sp


def generate_suggestions(code: str):
    sug = []
    if "\t" in code:
        sug.append("Use consistent indentation (prefer 4 spaces instead of tabs).")
    if re.search(r"\bprint\s*\(", code) and not re.search(r"if __name__\s*==\s*['\"]__main__['\"]", code):
        sug.append("For bigger programs, consider adding a main block: if __name__ == '__main__':")
    if re.search(r"^\s*from\s+\S+\s+import\s+\*", code, re.MULTILINE):
        sug.append("Avoid 'import *' because it makes code less readable. Import specific names instead.")
    if re.search(r"\bsum\s*=\s*", code):
        sug.append("Avoid naming variables like 'sum' because it overrides Python built-in sum().")
    if len(code.splitlines()) > 60:
        sug.append("Consider breaking the code into smaller functions for better readability.")
    if not sug:
        sug.append("Looks good. Add comments and test with sample inputs to confirm correctness.")
    return sug[:5]


@app.route("/")
def home():
    return render_template("index.html", languages=SUPPORTED_LANGUAGES)


@app.route("/explain", methods=["POST"])
def explain():
    data = request.json or {}
    code = (data.get("code") or "").strip()
    language = data.get("language") or "Python"

    if not code:
        return jsonify({"ok": False, "message": "Please paste your code."}), 400

    if language != "Python":
        return jsonify({"ok": False, "message": "Currently only Python is supported in this demo."}), 400

    lines = code.splitlines()

    line_by_line = []
    for i, raw in enumerate(lines, start=1):
        line_by_line.append({
            "line_no": i,
            "code": raw,
            "explain": explain_line(raw)
        })

    overall, time_c, space_c = generate_summary(code)
    suggestions = generate_suggestions(code)

    return jsonify({
        "ok": True,
        "output": {
            "overall": overall,
            "time_complexity": time_c,
            "space_complexity": space_c,
            "line_by_line": line_by_line,
            "suggestions": suggestions
        }
    })


if __name__ == "__main__":
    app.run(debug=True)