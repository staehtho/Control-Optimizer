from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


INPUT_FILE = "batch_results_tf_generation.xlsx"
OUTPUT_FILE_PTN = "table_itae_tf_alt_neu_ptn.tex"
OUTPUT_FILE_PT2 = "table_itae_tf_alt_neu_pt2.tex"
XML_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def column_text(cell: ET.Element) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text_node.text or "" for text_node in cell.findall(".//a:t", XML_NS))

    value_node = cell.find("a:v", XML_NS)
    return "" if value_node is None or value_node.text is None else value_node.text


def load_rows_from_xlsx(xlsx_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(xlsx_path) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(sheet_xml)
    row_nodes = root.find("a:sheetData", XML_NS).findall("a:row", XML_NS)

    headers = [column_text(cell) for cell in row_nodes[0].findall("a:c", XML_NS)]
    rows: list[dict[str, str]] = []

    for row_node in row_nodes[1:]:
        values = [column_text(cell) for cell in row_node.findall("a:c", XML_NS)]
        rows.append(dict(zip(headers, values)))

    return rows


def format_system(system_type: str, param_value: float) -> str:
    if system_type == "PTn":
        return f"PT{int(round(param_value))}"
    if system_type == "PT2":
        return f"PT2, $D={param_value:.1f}$"
    return f"{system_type}, ${param_value}$"


def format_float(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def prepare_rows(rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    required_columns = {"type", "n_or_D", "A", "itae_reference", "itae_new"}
    missing_columns = required_columns.difference(rows[0].keys())
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns in input file: {missing}")

    prepared_rows: list[dict[str, float | str]] = []
    for row in rows:
        itae_old = float(row["itae_reference"])
        itae_new = float(row["itae_new"])
        prepared_rows.append(
            {
                "type": row["type"],
                "n_or_D": float(row["n_or_D"]),
                "A": float(row["A"]),
                "itae_reference": itae_old,
                "itae_new": itae_new,
                "delta_rel_percent": (itae_new - itae_old) / itae_old * 100.0,
            }
        )

    prepared_rows.sort(
        key=lambda row: (
            {"PTn": 0, "PT2": 1}.get(str(row["type"]), 2),
            float(row["n_or_D"]),
            float(row["A"]),
        )
    )

    return prepared_rows


def generate_table(
    prepared_rows: list[dict[str, float | str]],
    *,
    system_type: str,
    caption: str,
    label: str,
) -> str:
    filtered_rows = [row for row in prepared_rows if str(row["type"]) == system_type]

    lines: list[str] = [
        r"\begin{table}[H]",
        r"    \centering",
        f"    \\caption{{{caption}}}",
        f"    \\label{{{label}}}",
        r"    \begin{tabular}{lrrrr}",
        r"        \toprule",
        r"        System & \(A\) & \(\mathrm{ITAE}_{\mathrm{alt}}\) & \(\mathrm{ITAE}_{\mathrm{neu}}\) & \(\Delta_{\mathrm{rel}}\) [\%] \\",
        r"        \midrule",
    ]

    for row in filtered_rows:
        lines.append(
            "        "
            f"{format_system(str(row['type']), float(row['n_or_D']))} & "
            f"{format_float(float(row['A']), digits=0)} & "
            f"{format_float(float(row['itae_reference']))} & "
            f"{format_float(float(row['itae_new']))} & "
            f"{format_float(float(row['delta_rel_percent']), digits=2)} \\\\"
        )

    lines.extend(
        [
            r"        \bottomrule",
            r"    \end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / INPUT_FILE
    output_path_ptn = script_dir / OUTPUT_FILE_PTN
    output_path_pt2 = script_dir / OUTPUT_FILE_PT2

    rows = load_rows_from_xlsx(input_path)
    if not rows:
        raise ValueError("Input file does not contain any data rows.")

    prepared_rows = prepare_rows(rows)
    table_tex_ptn = generate_table(
        prepared_rows,
        system_type="PTn",
        caption=r"Vergleich der ITAE-Werte für PTn-Referenzsysteme mit alter und neuer Behandlung von \(T_f\)",
        label="tab:itae_tf_alt_neu_ptn",
    )
    table_tex_pt2 = generate_table(
        prepared_rows,
        system_type="PT2",
        caption=r"Vergleich der ITAE-Werte für PT2-Referenzsysteme mit alter und neuer Behandlung von \(T_f\)",
        label="tab:itae_tf_alt_neu_pt2",
    )

    output_path_ptn.write_text(table_tex_ptn, encoding="utf-8")
    output_path_pt2.write_text(table_tex_pt2, encoding="utf-8")

    print(f"Written LaTeX table to: {output_path_ptn}")
    print(f"Written LaTeX table to: {output_path_pt2}")


if __name__ == "__main__":
    main()
