# -*- coding: utf-8 -*-
"""Merge dissertation parts and apply structural LaTeX fixes."""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
RAW = BASE / "dissertation_raw.tex"
MERGED = BASE / "dissertation_merged.tex"
OUT = BASE / "dissertation.tex"

PART_FILES = [
    "dissertation_body_part1.tex",
    "dissertation_body_part2.tex",
    "dissertation_body_part3.tex",
]

MERGE_MARKERS = ("MERGE_PART1", "PLACEHOLDER_BODY")


def load_body() -> str:
    body = ""
    for name in PART_FILES:
        path = BASE / name
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        body += path.read_text(encoding="utf-8").rstrip() + "\n\n"
    return body


def merge_raw() -> str:
    if not RAW.exists():
        raise SystemExit(f"Place source at {RAW}")

    header = RAW.read_text(encoding="utf-8")
    marker = next((m for m in MERGE_MARKERS if m in header), None)
    if marker is None:
        raise SystemExit(f"header missing one of {MERGE_MARKERS}")

    before, tail = header.split(marker, 1)
    merged = before + load_body() + tail
    MERGED.write_text(merged, encoding="utf-8")
    return merged


def apply_fixes(text: str) -> tuple[str, list[str]]:
    applied: list[str] = []

    if r"\usepackage{amsmath}" not in text:
        text = text.replace(
            r"\usepackage{multirow}",
            r"\usepackage{multirow}" + "\n"
            r"\usepackage{amsmath}" + "\n"
            r"\usepackage{titlesec}" + "\n"
            r"\titleclass{\subsubsubsection}{straight}[\subsubsection]" + "\n"
            r"\titleformat{\subsubsubsection}{\normalsize\bfseries}{}{0em}{}",
        )
        applied.append("Added amsmath, titlesec for subsubsubsection after multirow")

    new_text, n = re.subn(
        r"\}\s*\n\s*\\vfill\s*%\s*\n\s*\\section\*\{Введение\}",
        r"}\n\n\\newpage\n\n\\section*{Введение}",
        text,
        count=1,
    )
    if n:
        text = new_text
        applied.append("Replaced }\\vfill% before Введение with \\newpage")

    dup_marker = (
        "На основании этого выбора в следующем подразделе описывается\n"
        "метод решения задачи рекомендации параметров.\n\n"
        "Для задачи рекомендации параметров в разрабатываемом тренажёре"
    )
    if dup_marker in text:
        start = text.index(dup_marker) + len(
            "На основании этого выбора в следующем подразделе описывается\n"
            "метод решения задачи рекомендации параметров.\n\n"
        )
        end = text.index(
            r"\subsection{Метод решения задачи рекомендации параметров}", start
        )
        text = text[:start] + text[end:]
        applied.append("Removed duplicate comparison block in part3")

    para_count = len(re.findall(r"\\paragraph\{", text))
    if para_count:
        text = re.sub(r"\\paragraph\{([^}]+)\}", r"\\textbf{\1}", text)
        applied.append(f"Replaced {para_count} \\paragraph{{ with \\textbf{{")

    if r"\label{tab:exercises}" not in text:
        table = r"""
\begin{table}[ht]
\centering
\caption{Сводка упражнений программного комплекса}
\label{tab:exercises}
\begin{tabular}{|c|p{7.5cm}|p{5cm}|}
\hline
№ & Содержание & Контролируемые движения \\
\hline
1 & Захват целей при фиксированной голове & Руки \\
2 & Захват целей, голова в нейтрали & Руки \\
3 & Движущиеся цели & Руки \\
4 & Цели + скорость & Руки \\
5 & Цели + скорость + время & Руки \\
6 & Увеличенное время реакции & Руки \\
7 & Захват при движениях шеи & Руки, шея \\
8 & Смена цвета цели & Руки, шея \\
9 & Смена цвета + скорость & Руки, шея \\
\hline
\end{tabular}
\end{table}
"""
        placeholder = "% таблица из прошлого сообщения — по желанию"
        if placeholder in text:
            text = text.replace(placeholder, table.strip(), 1)
            applied.append("Inserted exercises table at placeholder comment")

    if r"\begin{thebibliography}" not in text:
        text = text.replace(
            r"\bibitem{mediapipe_pose}",
            r"\begin{thebibliography}{99}" + "\n\n" + r"\bibitem{mediapipe_pose}",
            1,
        )
        text = text.rstrip()
        if text.endswith(r"\end{document}"):
            text = text[: -len(r"\end{document}")].rstrip()
        text += "\n\n\\end{thebibliography}\n\n\\end{document}\n"
        applied.append("Wrapped bibliography in thebibliography environment")

    parts = text.split(r"\bibitem{hovareshti2021}")
    if len(parts) > 2:
        text = parts[0] + r"\bibitem{hovareshti2021}" + parts[2]
        applied.append("Removed duplicate short hovareshti2021 bibitem (no DOI)")

    if r"\cite{herdman2014}" in text and r"\bibitem{herdman2014}" not in text:
        insert_after = r"\bibitem{hall2016}"
        herdman = r"""
\bibitem{herdman2014}
Herdman S. J., Hall C. D., Schubert M. C., Das V. E.
Vestibular Rehabilitation //
NeuroRehabilitation. --- 2014. --- Vol.~34, No.~3. --- P.~375--380.
"""
        text = text.replace(insert_after, insert_after + "\n" + herdman.strip(), 1)
        applied.append("Added bibitem{herdman2014} after hall2016")

    if r"\section*{Заключение}" not in text and r"\section{Заключение}" not in text:
        conclusion = r"""
\section*{Заключение}
\addcontentsline{toc}{section}{Заключение}

В работе рассмотрены методы персонализации медицинского тренажёра
для вестибулярной реабилитации в составе программного комплекса
на базе веб-камеры и MediaPipe Pose.

Разработан модуль персонализированной калибровки: трёхэтапный
протокол измеряет досягаемость рук, диапазон движений головы
и эталонное положение пациента; профиль сохраняется и используется
в упражнениях для размещения целей и объективного контроля техники.

Реализован модуль рекомендаций нагрузочных параметров: пороговая
rule-based модель по истории тренировок и базовому назначению врача
предлагает корректировку сложности очередного занятия в пределах
одного шага. Оба модуля интегрированы в интерфейс тренажёра.

Практическая значимость состоит в доступности домашней реабилитации
с учётом индивидуальной анатомии и динамики переносимости нагрузки
между визитами к специалисту.

"""
        text = text.replace(
            r"\begin{thebibliography}{99}",
            conclusion + "\n\\begin{thebibliography}{99}",
            1,
        )
        applied.append("Added conclusion section before bibliography")

    return text, applied


def main() -> int:
    merged = merge_raw()
    print(f"Written: {MERGED} ({len(merged.splitlines())} lines)")

    fixed, applied = apply_fixes(merged)
    OUT.write_text(fixed, encoding="utf-8")
    line_count = len(fixed.splitlines())
    print(f"Written: {OUT} ({line_count} lines)")
    print("\nFixes applied:")
    for item in applied:
        print(f"  - {item}")
    if not applied:
        print("  (none — all fixes already present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
