import json
from pathlib import Path
from html import escape

import streamlit as st
import streamlit.components.v1 as components


RESULTS_DIR = Path(__file__).parent / "../results_module1_per_video_so"


def load_notes(filepath: Path) -> dict:
    with filepath.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_mermaid(diagram: str) -> None:
    html = f"""
    <div class="mermaid">
    {escape(diagram)}
    </div>

    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
      mermaid.initialize({{ startOnLoad: true }});
    </script>
    """
    components.html(html, height=420, scrolling=True)


def render_block(block: dict) -> None:
    block_type = block.get("type")

    if block_type == "text":
        st.write(block.get("content", ""))

    elif block_type == "bullet_list":
        for item in block.get("items", []):
            st.markdown(f"- {item}")

    elif block_type == "code":
        st.code(
            block.get("code", ""),
            language=block.get("language", "python"),
        )

  
    elif block_type == "mermaid":
        st.markdown("**Diagram**")
        render_mermaid(block.get("diagram", ""))
        with st.expander("Mermaid source"):
            st.code(block.get("diagram", ""), language="mermaid")
    else:
        st.json(block)


def render_notes(notes: dict) -> None:
    st.title(notes.get("title", "Course Notes"))

    st.header("Overview")
    st.write(notes.get("overview", ""))

    st.header("Key Concepts")
    for concept in notes.get("key_concepts", []):
        with st.expander(concept.get("title", "Untitled concept"), expanded=True):
            description = concept.get("description")
            if description:
                st.write(description)

            for point in concept.get("bullet_points", []):
                st.markdown(f"- {point}")

    st.header("Detailed Explanations")
    for section in notes.get("detailed_explanations", []):
        st.subheader(section.get("title", "Untitled section"))

        for block in section.get("blocks", []):
            render_block(block)

    st.header("Key Takeaways")
    for takeaway in notes.get("key_takeaway", []):
        st.markdown(f"- {takeaway}")

    st.header("Project Ideas")
    for idea in notes.get("project_ideas", []):
        st.markdown(f"- {idea}")

    st.header("Useful Timestamps")
    timestamps = notes.get("timestamps", [])

    if not timestamps:
        st.info("No timestamps available.")
        return

    for item in timestamps:
        with st.expander(
            f"{item.get('start_time', '')}-{item.get('end_time', '')}: {item.get('concept', '')}"
        ):
            learning_value = item.get("learning_value")
            if learning_value:
                st.markdown(f"**Learning value:** {learning_value}")

            explanation = item.get("explanation")
            if explanation:
                st.markdown(f"**Explanation:** {explanation}")

            if item.get("screenshot_recommended"):
                st.markdown("**Screenshot recommended:** Yes")
                st.markdown(f"**Visual to capture:** {item.get('visual_to_capture', '')}")
                st.markdown(f"**Reason:** {item.get('screenshot_reason', '')}")
                st.markdown(
                    f"**Suggested notes location:** {item.get('suggested_notes_location', '')}"
                )
                st.markdown(f"**Suggested caption:** {item.get('suggested_caption', '')}")
            else:
                st.markdown("**Screenshot recommended:** No")


def main() -> None:
    st.set_page_config(
        page_title="Course Notes Viewer",
        layout="wide",
    )

    st.sidebar.title("Course Notes")

    files = sorted(RESULTS_DIR.glob("*.json"))

    if not files:
        st.error(f"No JSON files found in {RESULTS_DIR}")
        return

    selected_file = st.sidebar.selectbox(
        "Select a notes file",
        files,
        format_func=lambda path: path.stem.replace("llm_response_", ""),
    )

    notes = load_notes(selected_file)

    with st.sidebar:
        st.divider()
        st.caption("Selected file")
        st.code(str(selected_file))

        st.download_button(
            label="Download JSON",
            data=json.dumps(notes, indent=2),
            file_name=selected_file.name,
            mime="application/json",
        )

    tab_notes, tab_screenshots, tab_raw = st.tabs(
        ["Notes", "Screenshot Candidates", "Raw JSON"]
    )

    with tab_notes:
        render_notes(notes)

    with tab_screenshots:
        st.header("Screenshot Candidates")

        candidates = [
            item
            for item in notes.get("timestamps", [])
            if item.get("screenshot_recommended")
        ]

        if not candidates:
            st.info("No screenshot candidates were recommended.")

        for item in candidates:
            st.subheader(
                f"{item.get('start_time', '')}-{item.get('end_time', '')}: "
                f"{item.get('concept', '')}"
            )
            st.markdown(f"**Visual to capture:** {item.get('visual_to_capture', '')}")
            st.markdown(f"**Reason:** {item.get('screenshot_reason', '')}")
            st.markdown(
                f"**Suggested notes location:** {item.get('suggested_notes_location', '')}"
            )
            st.markdown(f"**Suggested caption:** {item.get('suggested_caption', '')}")
            st.divider()

    with tab_raw:
        st.json(notes)


if __name__ == "__main__":
    main()