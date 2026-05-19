#!/usr/bin/env python3
"""Run the full agentic workflow with per-node trace and RAG smoke test; save outputs."""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows console: avoid UnicodeEncodeError when agents print LLM output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config
from src.main import load_sample_data, prepare_input, save_report
from src.graph.main_graph import main_workflow
from src.orchestrations.obd2_orchestration import obd2_orchestration
from src.orchestrations.writer_orchestration import writer_orchestration
from src.tools.rag_tool import retrieve_for_codes, retrieve_with_reflection


class Tee:
    """Write to multiple streams."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> None:
        for s in self.streams:
            if s is sys.stdout or s is sys.stderr:
                s.write(data)
            else:
                s.write(data.encode("utf-8", errors="replace").decode("utf-8"))
            s.flush()

    def flush(self) -> None:
        for s in self.streams:
            s.flush()


def _rag_section(codes: List[str], make: str) -> str:
    lines = ["## RAG knowledge base", ""]
    try:
        from src.rag.knowledge_base import knowledge_base

        stats = knowledge_base.get_stats()
        lines.append(f"- Total chunks: {stats.get('total_chunks')}")
        lines.append(f"- DTC chunks: {stats.get('dtc')}")
        lines.append(f"- Manual chunks: {stats.get('manual')}")
        lines.append(f"- Hybrid: {stats.get('hybrid_enabled')} | Rerank: {stats.get('rerank_enabled')}")
        lines.append("")
        lines.append("### Per-code retrieval (exact + hybrid + rerank + cosine)")
        for code in codes:
            q = f"OBD2 code {code} diagnostic trouble code meaning causes repair"
            r = retrieve_with_reflection.invoke({"query": q, "top_k": config.RAG_TOP_K})
            lines.append(f"#### {code}")
            lines.append(f"- Reflection sufficient: {r.get('is_sufficient')}")
            lines.append(f"- Score: {r.get('score', 0):.3f}")
            lines.append(f"- Documents: {r.get('document_count', 0)}")
            for hit in r.get("hits") or []:
                lines.append(
                    f"- Rank {hit.get('rank')}: cosine={hit.get('cosine_similarity')} "
                    f"rerank={hit.get('rerank_score')} bm25={hit.get('bm25_score')} "
                    f"chunk_id={hit.get('chunk_id')}"
                )
                if hit.get("query_vector_preview"):
                    lines.append(f"  - query_vec preview: {hit.get('query_vector_preview')}")
                if hit.get("doc_vector_preview"):
                    lines.append(f"  - doc_vec preview: {hit.get('doc_vector_preview')}")
            preview = (r.get("content") or "")[:1200]
            lines.append("")
            lines.append("```")
            lines.append(preview.strip() or "(empty)")
            lines.append("```")
            lines.append("")
        lines.append("### retrieve_for_codes (batch)")
        batch = retrieve_for_codes(codes, make=make, filter_by_type=True)
        lines.append("```")
        lines.append((batch or "(empty)")[:2000])
        lines.append("```")
    except Exception as exc:
        lines.append(f"RAG error: {exc}")
        lines.append("```")
        lines.append(traceback.format_exc())
        lines.append("```")
    return "\n".join(lines)


def _format_node_update(node: str, update: Dict[str, Any] | None) -> str:
    lines = [f"### Node: `{node}`", ""]
    if not update:
        lines.append("_(no state update)_")
        lines.append("")
        return "\n".join(lines)
    for key, val in update.items():
        if key == "messages":
            lines.append(f"- **messages**: {len(val)} message(s)")
            continue
        if isinstance(val, str):
            preview = val[:2000] + ("..." if len(val) > 2000 else "")
            lines.append(f"- **{key}** ({len(val)} chars):")
            lines.append("")
            lines.append("```")
            lines.append(preview)
            lines.append("```")
        elif isinstance(val, (list, dict)):
            text = json.dumps(val, default=str, indent=2)[:3000]
            lines.append(f"- **{key}**:")
            lines.append("```json")
            lines.append(text)
            lines.append("```")
        else:
            lines.append(f"- **{key}**: {val}")
    lines.append("")
    return "\n".join(lines)


def _stream_graph(name: str, graph, state: Dict[str, Any], sections: List[str]) -> Dict[str, Any]:
    sections.append(f"## Subgraph: {name}")
    sections.append("")
    final: Dict[str, Any] = {}
    for chunk in graph.stream(state, stream_mode="updates"):
        for node, update in chunk.items():
            sections.append(_format_node_update(node, update))
            final.update(update)
    return final


def main() -> int:
    if not config.OPENAI_API_KEY:
        print("ERROR: Set OPENAI_API_KEY / BIGMODEL_API_KEY in .env", file=sys.stderr)
        return 2

    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_dir / f"workflow_trace_{ts}.log"
    md_path = output_dir / f"workflow_trace_{ts}.md"

    log_buffer = StringIO()
    tee = Tee(sys.stdout, log_buffer)

    old_stdout = sys.stdout
    sys.stdout = tee

    md_parts: List[str] = [
        "# Agentic workflow run trace",
        "",
        f"**Started:** {datetime.now().isoformat()}",
        f"**Model:** {config.LLM_MODEL}",
        f"**RAG_TOP_K:** {config.RAG_TOP_K} | **RAG_RETRIEVE_K:** {getattr(config, 'RAG_RETRIEVE_K', '?')}",
        "",
    ]

    try:
        print("Loading sample OBD2 data...")
        input_data = load_sample_data()
        state = prepare_input(input_data)
        codes = [c.get("code", "") for c in state["obd2_data"].get("diagnostic_codes", [])]
        make = getattr(state["car_metadata"], "car_name", "Toyota").split()[0]

        md_parts.append(_rag_section(codes, make))
        md_parts.append("")

        # --- Main graph (stream top-level nodes) ---
        md_parts.append("## Main workflow graph")
        md_parts.append("")
        print("\n" + "=" * 60)
        print("MAIN WORKFLOW (streaming nodes)")
        print("=" * 60 + "\n")

        result: Dict[str, Any] = {}
        for chunk in main_workflow.stream(state, stream_mode="updates"):
            for node, update in chunk.items():
                print(f"\n>>> Main node completed: {node}")
                md_parts.append(_format_node_update(f"main/{node}", update))
                if update:
                    result.update(update)

        # If stream missed nested detail, ensure we have final invoke fields
        if not result.get("final_report"):
            print("\nRe-invoking for final state merge...")
            result = main_workflow.invoke(state)

        final_report = result.get("final_report", "")
        obd2_analysis = result.get("obd2_analysis", "")

        md_parts.extend([
            "## Final outputs",
            "",
            "### OBD2 analysis (excerpt)",
            "```",
            (obd2_analysis or "(none)")[:4000],
            "```",
            "",
            "### Final report",
            "",
            final_report or "(none)",
            "",
        ])

        if final_report and not str(final_report).startswith("ERROR"):
            txt_path = save_report(final_report, result.get("user_id", "user_001"))
            md_parts.append(f"**Report file:** `{txt_path}`")
            print(f"\nReport saved to: {txt_path}")

        md_parts.append(f"\n**Finished:** {datetime.now().isoformat()}")

    except Exception as exc:
        print(f"\nWorkflow failed: {exc}")
        traceback.print_exc()
        md_parts.append(f"\n## ERROR\n\n```\n{traceback.format_exc()}\n```")
        sys.stdout = old_stdout
        log_path.write_text(log_buffer.getvalue(), encoding="utf-8")
        md_path.write_text("\n".join(md_parts), encoding="utf-8")
        print(f"\nPartial logs: {log_path}\n{md_path}")
        return 1

    sys.stdout = old_stdout
    log_path.write_text(log_buffer.getvalue(), encoding="utf-8")
    md_path.write_text("\n".join(md_parts), encoding="utf-8")

    print(f"\nTrace log:  {log_path}")
    print(f"Trace markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
