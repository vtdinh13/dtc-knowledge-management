import pandas as pd
import streamlit as st
import tiktoken
import tiktoken.model


def get_tiktoken_models() -> list[str]:
    return sorted(tiktoken.model.MODEL_TO_ENCODING.keys())


def get_encoding_name(model_name: str) -> str:
    return tiktoken.model.MODEL_TO_ENCODING[model_name]


def count_tokens(text: str, model_name: str) -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(text))


def main() -> None:
    st.set_page_config(
        page_title="Token Calculation",
        layout="wide",
    )

    st.title("Token Calculation")
    models = get_tiktoken_models()

    with st.sidebar:
        st.header("Model")
        selected_model = st.selectbox(
            "Select a tiktoken model",
            models,
            index=models.index("gpt-5") if "gpt-5" in models else 0,
        )

        encoding_name = get_encoding_name(selected_model)
        

    document_text = st.text_area(
        "Document text",
        height=420,
        placeholder="Paste your document here...",
    )

    token_count = count_tokens(document_text, selected_model) if document_text else 0
    word_count = len(document_text.split()) if document_text else 0
    character_count = len(document_text)

    col1, col2, col3 = st.columns(3)
    col1.metric("Tokens", f"{token_count:,}")
    col2.metric("Words", f"{word_count:,}")
    col3.metric("Characters", f"{character_count:,}")

    st.divider()

    with st.expander("Compare token count across all tiktoken models"):
        if not document_text:
            st.info("Paste document text above to compare models.")
        else:
            rows = []

            for model in models:
                rows.append(
                    {
                        "model": model,
                        "encoding": get_encoding_name(model),
                        "token_count": count_tokens(document_text, model),
                    }
                )

            df = pd.DataFrame(rows).sort_values(
                ["encoding", "model"],
                ignore_index=True,
            )

            st.dataframe(df, use_container_width=True)

            st.download_button(
                "Download comparison CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="token_count_comparison.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()