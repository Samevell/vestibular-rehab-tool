import json

path = r"C:\Users\Samvel\.cursor\projects\c-Users-Samvel-Desktop-Ycheba-disertatsia-new-trainer-new-int-1\agent-transcripts\8085057f-10f9-42b4-8dc2-7ce67b0c9031\8085057f-10f9-42b4-8dc2-7ce67b0c9031.jsonl"
text = None
with open(path, encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        if obj.get("role") == "user":
            msg = obj["message"]["content"][0]["text"]
            if r"\section{Модуль персонализированной калибровки}" in msg:
                text = msg
                break

if text is None:
    raise SystemExit("LaTeX source not found in transcript")

if text.startswith("<user_query>"):
    text = text[len("<user_query>") :]
if text.endswith("</user_query>"):
    text = text[: -len("</user_query>")]

start2 = text.index(r"\section{Модуль персонализированной калибровки}")
start3 = text.index(r"\section{Актуальность разработки модуля рекомендаций")
bib = text.index(r"\bibitem{mediapipe_pose}")

part2 = text[start2:start3].rstrip() + "\n"
part3_raw = text[start3:bib].rstrip() + "\n"

marker = (
    "На основании этого выбора в следующем подразделе описывается\n"
    "метод решения задачи рекомендации параметров."
)
dup_start = (
    "Для задачи рекомендации параметров в разрабатываемом тренажёре\n"
    "существенны четыре ограничения:"
)
next_section = r"\subsection{Метод решения задачи рекомендации параметров}"

idx_marker = part3_raw.index(marker)
idx_dup = part3_raw.index(dup_start, idx_marker)
idx_next = part3_raw.index(next_section, idx_dup)
part3 = part3_raw[: idx_marker + len(marker)] + "\n\n" + part3_raw[idx_next:]

out2 = r"c:\Users\Samvel\Desktop\Ycheba\disertatsia\new\trainer_new_int_1\dissertation_body_part2.tex"
out3 = r"c:\Users\Samvel\Desktop\Ycheba\disertatsia\new\trainer_new_int_1\dissertation_body_part3.tex"
with open(out2, "w", encoding="utf-8", newline="\n") as f:
    f.write(part2)
with open(out3, "w", encoding="utf-8", newline="\n") as f:
    f.write(part3)

print("part2 lines:", part2.count("\n"))
print("part3 lines:", part3.count("\n"))
