"""Vietnamese numbers in words, for the voice tools: text to read ("30/11", "25.000đ", "10%") is spelled out
before the model reads it, and Whisper's digits are spelled out the same way before scoring, so "30 tháng 11"
and "ba mươi tháng mười một" count as the same."""
import re

UNITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
SCALES = [(1_000_000_000, "tỷ"), (1_000_000, "triệu"), (1_000, "nghìn")]


def _tens(n):
    """1–99."""
    if n < 10:
        return UNITS[n]
    t, u = divmod(n, 10)
    head = "mười" if t == 1 else f"{UNITS[t]} mươi"
    if u == 0:
        return head
    tail = {1: "mốt" if t > 1 else "một", 4: "tư" if t > 1 else "bốn", 5: "lăm"}.get(u, UNITS[u])
    return f"{head} {tail}"


def _hundreds(n, inner):
    """0–999; inner: a group after a larger one, read with its hundreds ("không trăm lẻ năm")."""
    h, r = divmod(n, 100)
    if h == 0 and not inner:
        return _tens(r)
    out = f"{UNITS[h]} trăm"
    if r == 0:
        return out
    return f"{out} lẻ {UNITS[r]}" if r < 10 else f"{out} {_tens(r)}"


def number_words(n):
    """A whole number 0 … 999 999 999 999 in words."""
    if n < 10:
        return UNITS[n]
    words, inner = [], False
    for size, name in SCALES:
        if n >= size:
            q, n = divmod(n, size)
            words += [_hundreds(q, inner) if q < 1000 else number_words(q), name]
            inner = True
    if n:
        words.append(_hundreds(n, inner))
    return " ".join(words)


def _num(s):
    return number_words(int(s.replace(".", "")))


def spell_out(text):
    """Dates, money, percents and plain numbers in a sentence spelled out."""
    text = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
                  lambda m: f"ngày {_num(m[1])} tháng {_num(m[2])} năm {_num(m[3])}", text)
    text = re.sub(r"\b(\d{1,2})/(\d{1,2})\b", lambda m: f"{_num(m[1])} tháng {_num(m[2])}", text)
    text = re.sub(r"\b(\d+)\s?[kK]\b", lambda m: f"{_num(m[1])} nghìn", text)
    text = re.sub(r"\b(\d{1,3}(?:\.\d{3})+|\d+)\s?(đ|đồng|VND|vnđ)(?!\w)", lambda m: f"{_num(m[1])} đồng", text)
    text = re.sub(r"\b(\d+)\s?%", lambda m: f"{_num(m[1])} phần trăm", text)
    return re.sub(r"\b\d{1,3}(?:\.\d{3})+\b|\b\d+\b", lambda m: _num(m[0]), text)


if __name__ == "__main__":                    # a quick check: python vi_numbers.py
    for n, want in [(5, "năm"), (10, "mười"), (15, "mười lăm"), (21, "hai mươi mốt"), (24, "hai mươi tư"),
                    (30, "ba mươi"), (105, "một trăm lẻ năm"), (1005, "một nghìn không trăm lẻ năm"),
                    (25000, "hai mươi lăm nghìn"), (2026, "hai nghìn không trăm hai mươi sáu"),
                    (1_200_000, "một triệu hai trăm nghìn")]:
        assert number_words(n) == want, (n, number_words(n), want)
    assert spell_out("từ 30/11") == "từ ba mươi tháng mười một"
    assert spell_out("giá 25.000đ, giảm 10%") == "giá hai mươi lăm nghìn đồng, giảm mười phần trăm"
    assert spell_out("ly 25k") == "ly hai mươi lăm nghìn"
    print("ok")
