"""This file should be imported if and only if you want to run the UI locally."""

import base64
import logging
import time
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any

import gradio as gr  # type: ignore
from fastapi import FastAPI
from gradio.themes.utils.colors import slate  # type: ignore
from injector import inject, singleton
from llama_index.core.llms import ChatMessage, ChatResponse, MessageRole
from llama_index.core.types import TokenGen
from pydantic import BaseModel

from qgpt_core.constants import PROJECT_ROOT_PATH
from qgpt_core.di import global_injector
from qgpt_core.open_ai.extensions.context_filter import ContextFilter
from qgpt_core.server.chat.chat_service import ChatService, CompletionGen
from qgpt_core.server.chunks.chunks_service import Chunk, ChunksService
from qgpt_core.server.ingest.ingest_service import IngestService
from qgpt_core.server.recipes.summarize.summarize_service import SummarizeService
from qgpt_core.settings.settings import settings
from qgpt_core.ui.images import logo_svg

logger = logging.getLogger(__name__)

THIS_DIRECTORY_RELATIVE = Path(__file__).parent.relative_to(PROJECT_ROOT_PATH)
# Should be "private_gpt/ui/avatar-bot.ico"
AVATAR_BOT = THIS_DIRECTORY_RELATIVE / "avatar-bot.ico"

UI_TAB_TITLE = "My Private GPT"

SOURCES_SEPARATOR = "<hr>Sources: \n"


class Modes(str, Enum):
    RAG_MODE = "RAG"
    SEARCH_MODE = "Search"
    BASIC_CHAT_MODE = "Basic"
    SUMMARIZE_MODE = "Summarize"


MODES: list[Modes] = [
    Modes.RAG_MODE,
    Modes.SEARCH_MODE,
    Modes.BASIC_CHAT_MODE,
    Modes.SUMMARIZE_MODE,
]


class Source(BaseModel):
    file: str
    page: str
    text: str

    class Config:
        frozen = True

    @staticmethod
    def curate_sources(sources: list[Chunk]) -> list["Source"]:
        curated_sources = []

        for chunk in sources:
            doc_metadata = chunk.document.doc_metadata

            file_name = doc_metadata.get("file_name", "-") if doc_metadata else "-"
            page_label = doc_metadata.get("page_label", "-") if doc_metadata else "-"

            source = Source(file=file_name, page=page_label, text=chunk.text)
            curated_sources.append(source)
            curated_sources = list(
                dict.fromkeys(curated_sources).keys()
            )  # Unique sources only

        return curated_sources


@singleton
class PrivateGptUi:
    @inject
    def __init__(
        self,
        ingest_service: IngestService,
        chat_service: ChatService,
        chunks_service: ChunksService,
        summarizeService: SummarizeService,
    ) -> None:
        self._ingest_service = ingest_service
        self._chat_service = chat_service
        self._chunks_service = chunks_service
        self._summarize_service = summarizeService

        # Cache the UI blocks
        self._ui_block = None

        self._selected_filename = None

        # Initialize system prompt based on default mode
        default_mode_map = {mode.value: mode for mode in Modes}
        self._default_mode = default_mode_map.get(
            settings().ui.default_mode, Modes.RAG_MODE
        )
        self._system_prompt = self._get_default_system_prompt(self._default_mode)

        # Store history for each mode
        self._history_cache = {mode: [] for mode in Modes}

    def _chat(
        self, message: str, history: list[list[str]], mode: Modes, *_: Any
    ) -> Any:
        def yield_deltas(completion_gen: CompletionGen) -> Iterable[str]:
            full_response: str = ""
            stream = completion_gen.response
            for delta in stream:
                if isinstance(delta, str):
                    full_response += str(delta)
                elif isinstance(delta, ChatResponse):
                    full_response += delta.delta or ""
                yield full_response
                time.sleep(0.02)

            if completion_gen.sources:
                full_response += SOURCES_SEPARATOR
                cur_sources = Source.curate_sources(completion_gen.sources)
                sources_text = "\n\n\n"
                used_files = set()
                for index, source in enumerate(cur_sources, start=1):
                    if f"{source.file}-{source.page}" not in used_files:
                        sources_text = (
                            sources_text
                            + f"{index}. {source.file} (page {source.page}) \n\n"
                        )
                        used_files.add(f"{source.file}-{source.page}")
                sources_text += "<hr>\n\n"
                full_response += sources_text
            yield full_response

        def yield_tokens(token_gen: TokenGen) -> Iterable[str]:
            full_response: str = ""
            for token in token_gen:
                full_response += str(token)
                yield full_response

        def build_history(mode: Modes) -> list[ChatMessage]:
            history_messages: list[ChatMessage] = []
            # Get the history for the selected mode
            current_history = self._history_cache.get(mode, [])

            for interaction in current_history:
                history_messages.append(
                    ChatMessage(content=interaction[0], role=MessageRole.USER)
                )
                if len(interaction) > 1 and interaction[1] is not None:
                    history_messages.append(
                        ChatMessage(
                            # Remove content related to sources if necessary
                            content=interaction[1].split(SOURCES_SEPARATOR)[0],
                            role=MessageRole.ASSISTANT,
                        )
                    )

            # Limit the history to a maximum of 20 messages
            return history_messages[:20]

        # Add the new user message to the history for the selected mode
        new_message = ChatMessage(content=message, role=MessageRole.USER)
        self._history_cache[mode].append([message])  # Append the new user message

        all_messages = [*build_history(mode), new_message]

        # If a system prompt is set, add it as a system message
        if self._system_prompt:
            all_messages.insert(
                0,
                ChatMessage(
                    content=self._system_prompt,
                    role=MessageRole.SYSTEM,
                ),
            )

        match mode:
            case Modes.RAG_MODE:
                context_filter = None
                if self._selected_filename:
                    docs_ids = [
                        ingested_document.doc_id
                        for ingested_document in self._ingest_service.list_ingested()
                        if ingested_document.doc_metadata["file_name"] == self._selected_filename
                    ]
                    context_filter = ContextFilter(docs_ids=docs_ids)

                query_stream = self._chat_service.stream_chat(
                    messages=all_messages,
                    use_context=True,
                    context_filter=context_filter,
                )

                # Collect the full response
                full_response = ""
                for delta in yield_deltas(query_stream):
                    full_response = delta

                # Update the history with the bot's response
                self._history_cache[mode][-1].append(full_response)
                yield full_response

            case Modes.BASIC_CHAT_MODE:
                llm_stream = self._chat_service.stream_chat(
                    messages=all_messages,
                    use_context=False,
                )

                # Collect the full response
                full_response = ""
                for delta in yield_deltas(llm_stream):
                    full_response = delta

                # Update the history with the bot's response
                self._history_cache[mode][-1].append(full_response)
                yield full_response


            case Modes.SEARCH_MODE:
    # If a filename is selected, filter the response to include only relevant chunks from that file
                context_filter = None
                if self._selected_filename:
                    docs_ids = [
                        ingested_document.doc_id
                        for ingested_document in self._ingest_service.list_ingested()
                        if ingested_document.doc_metadata["file_name"] == self._selected_filename
                    ]
                    context_filter = ContextFilter(docs_ids=docs_ids)

                # Retrieve the relevant chunks (apply context_filter if necessary)
                response = self._chunks_service.retrieve_relevant(
                    text=message, limit=4, prev_next_chunks=0, context_filter=context_filter
                )

                # Curate the sources
                sources = Source.curate_sources(response)

                # Format the full response with the selected file chunks
                full_response = "\n\n\n".join(
                    f"{index}. **{source.file} (page {source.page})**\n {source.text}"
                    for index, source in enumerate(sources, start=1)
                )

                # Update the history with the bot's response
                self._history_cache[mode][-1].append(full_response)
                yield full_response

            case Modes.SUMMARIZE_MODE:
                context_filter = None
                if self._selected_filename:
                    docs_ids = [
                        ingested_document.doc_id
                        for ingested_document in self._ingest_service.list_ingested()
                        if ingested_document.doc_metadata["file_name"] == self._selected_filename
                    ]
                    context_filter = ContextFilter(docs_ids=docs_ids)

                summary_stream = self._summarize_service.stream_summarize(
                    use_context=True,
                    context_filter=context_filter,
                    instructions=message,
                )

                # Collect the full response
                full_response = ""
                for token in yield_tokens(summary_stream):
                    full_response = token

                # Update the history with the bot's response
                self._history_cache[mode][-1].append(full_response)
                yield full_response

    # On initialization and on mode change, this function set the system prompt
    # to the default prompt based on the mode (and user settings).
    @staticmethod
    def _get_default_system_prompt(mode: Modes) -> str:
        p = ""
        match mode:
            # For query chat mode, obtain default system prompt from settings
            case Modes.RAG_MODE:
                p = settings().ui.default_query_system_prompt
            # For chat mode, obtain default system prompt from settings
            case Modes.BASIC_CHAT_MODE:
                p = settings().ui.default_chat_system_prompt
            # For summarization mode, obtain default system prompt from settings
            case Modes.SUMMARIZE_MODE:
                p = settings().ui.default_summarization_system_prompt
            # For any other mode, clear the system prompt
            case _:
                p = ""
        return p

    @staticmethod
    def _get_default_mode_explanation(mode: Modes) -> str:
        match mode:
            case Modes.RAG_MODE:
                return "Retrieve responses from the uploaded documents. The system trains and generates responses based on the provided documents."
            case Modes.SEARCH_MODE:
                return "Identifies and extract the relevant sections of text from the selected files."
            case Modes.BASIC_CHAT_MODE:
                return "Engage with the LLM using its training data. Files are not considered."
            case Modes.SUMMARIZE_MODE:
                return "Generates a summary of the selected files and provide options to customize the result."
            case _:
                return ""

    def _set_system_prompt(self, system_prompt_input: str) -> None:
        logger.info(f"Setting system prompt to: {system_prompt_input}")
        self._system_prompt = system_prompt_input

    def _set_explanatation_mode(self, explanation_mode: str) -> None:
        self._explanation_mode = explanation_mode

    def _set_current_mode(self, mode: Modes) -> Any:
        self.mode = mode
        self._set_system_prompt(self._get_default_system_prompt(mode))
        self._set_explanatation_mode(self._get_default_mode_explanation(mode))
        interactive = self._system_prompt is not None
        return [
            gr.update(placeholder=self._system_prompt, interactive=interactive),
            gr.update(value=self._explanation_mode),
        ]

    def _list_ingested_files(self) -> list[list[str]]:
        files = set()
        for ingested_document in self._ingest_service.list_ingested():
            if ingested_document.doc_metadata is None:
                # Skipping documents without metadata
                continue
            file_name = ingested_document.doc_metadata.get(
                "file_name", "[FILE NAME MISSING]"
            )
            files.add(file_name)
        return [[row] for row in files]

    def _upload_file(self, files: list[str]) -> None:
        logger.debug("Loading count=%s files", len(files))
        paths = [Path(file) for file in files]

        # remove all existing Documents with name identical to a new file upload:
        file_names = [path.name for path in paths]
        doc_ids_to_delete = []
        for ingested_document in self._ingest_service.list_ingested():
            if (
                ingested_document.doc_metadata
                and ingested_document.doc_metadata["file_name"] in file_names
            ):
                doc_ids_to_delete.append(ingested_document.doc_id)
        if len(doc_ids_to_delete) > 0:
            logger.info(
                "Uploading file(s) which were already ingested: %s document(s) will be replaced.",
                len(doc_ids_to_delete),
            )
            for doc_id in doc_ids_to_delete:
                self._ingest_service.delete(doc_id)

        self._ingest_service.bulk_ingest([(str(path.name), path) for path in paths])

    def _delete_all_files(self) -> Any:
        ingested_files = self._ingest_service.list_ingested()
        logger.debug("Deleting count=%s files", len(ingested_files))
        for ingested_document in ingested_files:
            self._ingest_service.delete(ingested_document.doc_id)
        return [
            gr.List(self._list_ingested_files()),
            gr.components.Button(interactive=False),
            gr.components.Button(interactive=False),
            gr.components.Textbox("All files"),
        ]

    def _delete_selected_file(self) -> Any:
        logger.debug("Deleting selected %s", self._selected_filename)
        # Note: keep looping for pdf's (each page became a Document)
        for ingested_document in self._ingest_service.list_ingested():
            if (
                ingested_document.doc_metadata
                and ingested_document.doc_metadata["file_name"]
                == self._selected_filename
            ):
                self._ingest_service.delete(ingested_document.doc_id)
        return [
            gr.List(self._list_ingested_files()),
            gr.components.Button(interactive=False),
            gr.components.Button(interactive=False),
            gr.components.Textbox("All files"),
        ]

    def _deselect_selected_file(self) -> Any:
        self._selected_filename = None
        return [
            gr.components.Button(interactive=False),
            gr.components.Button(interactive=False),
            gr.components.Textbox("All files"),
        ]

    def _selected_a_file(self, select_data: gr.SelectData) -> Any:
        self._selected_filename = select_data.value
        return [
            gr.components.Button(interactive=True),
            gr.components.Button(interactive=True),
            gr.components.Textbox(self._selected_filename),
        ]

    

    def _build_ui_blocks(self) -> gr.Blocks:
        logger.debug("Creating the UI blocks")
        with gr.Blocks(
            title=UI_TAB_TITLE,
            theme=gr.themes.Soft(primary_hue=slate),
            css="""
            .logo { 
                display:flex;
                background-color: #24135f;
                height: 80px;
                border-radius: 8px;
                align-content: center;
                justify-content: center;
                align-items: center;
            }
            .logo img { height: 90% }
            .contain { display: flex !important; flex-direction: column !important; }
            #component-0, #component-3, #component-10, #component-8  { height: 100% !important; }
            #chatbot { flex-grow: 1 !important; overflow: auto !important;}
            #col { height: calc(100vh - 112px - 16px) !important; }
            hr { margin-top: 1em; margin-bottom: 1em; border: 0; border-top: 1px solid #FFF; }
            .avatar-image { background-color: antiquewhite; border-radius: 2pdisx; }
            .footer { text-align: center; margin-top: 20px; font-size: 18px; display: flex; align-items: center; justify-content: center; background-color: #24135f !important; color: #fff !important;    padding-top: 15px;padding-bottom: 15px; border-radius:4px; }
            .footer-zylon-link { display:flex; margin-left: 5px; text-decoration: auto; color: var(--body-text-color); color: #fff !important;font-style: italic;font-weight: 600;font-size: 18px; }
            .footer-zylon-link:hover { color: #C7BAFF; }
            .footer-zylon-ico { height: 20px; margin-left: 5px; background-color: antiquewhite; border-radius: 2px;} 
            .app.svelte-wpkpf6.svelte-wpkpf6:not(.fill_width) {max-width: 100% !Important}
            span.svelte-1gfkn6j { color: #fff !important ;background-color: #24135f !important}
            label.svelte-1mhtq7j.svelte-1mhtq7j.svelte-1mhtq7j { 
                display: flex;
                align-items: center;
                transition: var(--button-transition);
                cursor: pointer;
                box-shadow: var(--checkbox-label-shadow);
                border: var(--checkbox-label-border-width) solid var(--checkbox-label-border-color);
                border-radius: var(--button-small-radius);
                background: #24135f;
                padding: var(--checkbox-label-padding);
                color: #e8ebf0;
                font-weight: var(--checkbox-label-text-weight);
                font-size: var(--checkbox-label-text-size);
                line-height: var(--line-md);
            }
            button.svelte-button { 
                background-color: #24135f !important; 
                color: #fff !important;
                border: none !important;
                padding: 10px 20px !important;
                border-radius: 4px !important;
                font-size: 16px !important;
                cursor: pointer !important;
                transition: background-color 0.3s ease !important;
            }
            button.svelte-button:hover { 
                background-color: #1e0e
            }
            #dropdown-mode {     
                background-color: #24135f !important;     
                color: #fff !important;     
                border: 1px solid #24135f !important;     
                border-radius: 4px;
                padding: 5px;     
                font-size: 14px; }
            footer.svelte-1rjryqp>.svelte-1rjryqp+.svelte-1rjryqp {
                display: flex !important;
            }
            .show-api.svelte-1rjryqp.svelte-1rjryqp.svelte-1rjryqp {
                display: flex !important;
            }
            div#component-4 { border: 1px solid rgba(0, 0, 0, 0.2);background: #EBEBEB;}
            .primary.svelte-cmf5ev {
                background: #037db6 !important;
                border-radius: 15px !important;
                padding: 0px 6px 0px 6px !important;
                background-color: #D3D3D3;
                text-transform: uppercase;
            }
            .secondary.svelte-cmf5ev {
                background: #12092F !important;
                border-radius: 100px !important;
                color: #fff !important;
                padding: 10px 0px 10px 0px;
            }
            textarea.svelte-1f354aw.svelte-1f354aw {
                background: #ececec;
                height: 5rem !important;
                color: black;
                font-size: 13px;
            }
            .bubble-wrap.svelte-1e1jlin.svelte-1e1jlin.svelte-1e1jlin {
                border: 1px solid #8e8e8e;
                font-style: italic;
                background: #F9F9F9;
            }
            .label.svelte-1oa6fve p.svelte-1oa6fve.svelte-1oa6fve {font-size: 15px;
                font-weight: bold;
                color: #333;}
            gradio-app .gradio-container.gradio-container-4-44-0 .contain #col { height: 100% !important; }
            gradio-app .gradio-container.gradio-container-4-44-0 .contain span.svelte-1gfkn6j { background-color: #fff !important; color: brown !important; left: 35px;}
            div#component-21 button.sm.secondary { background: rgb(74, 81, 142) !important; font-weight: 600 !important}
            div#component-5.svelte-vt1mxs gap { flex-grow: 2.5 !important; }
            th.svelte-1oa6fve.svelte-1oa6fve.svelte-1oa6fve:last-child { background: rgb(43, 62, 87) !important; font-family: sans-serif !important; color:#fff !important }
            tr:nth-child(even) {
                background-color: #f2f2f2 !important;
            }
            tr:hover {
                background-color: #ddd !important;
            }
            gradio-app .gradio-container.gradio-container-4-44-0 .contain .label.svelte-1oa6fve p.svelte-1oa6fve.svelte-1oa6fve {
                text-decoration: underline;
                font-weight:bold;
            }
            #component-7.svelte-vt1mxs.gap { border: 2px solid #d0cece !important; padding: 5px; }
            button#component-8 {
                font-weight: 600;
            }
            .prose.chatbot.md { font-weight: 501 !important }
            
            .toggle-btn {
              position: relative;
              top: 67px;
              left: 260px;
              background-color: #333;
              color: white;
              border: none;
              padding: 8px;
              cursor: pointer;
              font-size: 18px;
              display: flex;
              align-items: center;
              justify-content: center;
              transition: left 0.3s ease;
              border:0.1px solid #8e8e8e;
              background:rgb(36, 19, 95);
              color:#fff;
              padding-top:6px !important;
              left:8px;
              border-radius:6px;
              z-index:999;
            }
            #menu-toggle:checked ~ .toggle-btn {
              left: 70px;
            }
            #component-7.open {
            display: block; /* Show menu when open */
        }

            """
        ) as blocks:
            with gr.Row():
                gr.HTML(f"<div class='logo'/><img src={logo_svg} alt=PrivateGPT></div")
             # Toggle Button
            # with gr.Row():
            #     gr.HTML(
            #         """
            #         <button id="toggleButton" class="toggle-btn">☰</button>
            #         <script>
            #             window.addEventListener('DOMContentLoaded', (event) => {
            #             const toggleButton = document.getElementById('toggleButton');
            #             const menu = document.querySelector('component-7');
            #             alert(menu)
            #             if (toggleButton && menu) {
            #                 toggleButton.addEventListener('click', function () {
            #                     alert('ggggg'); // Confirm button is clicked
                                
            #                     // Toggle the menu display
            #                     if (menu.style.display === 'none' || menu.style.display === '') {
            #                         menu.style.display = 'none';
            #                     } else {
            #                         menu.style.display = 'block';
            #                     }
            #                 });
            #             } else {
            #                 console.error('Toggle button or menu not found!');
            #             }
            #         });
            #     </script>
            #         """
            #     )
            with gr.Row(equal_height=False):
                def toggle_sidebar(is_open):
                    if is_open:
                        return gr.update(visible=True),
                    else:
                        return gr.update(visible=False),
                def get_model_label() -> str | None:
                    """Get model label from llm mode setting YAML.

                    Raises:
                        ValueError: If an invalid 'llm_mode' is encountered.

                    Returns:
                        str: The corresponding model label.
                    """
                    # Get model label from llm mode setting YAML
                    # Labels: local, openai, openailike, sagemaker, mock, ollama
                    config_settings = settings()
                    if config_settings is None:
                        raise ValueError("Settings are not configured.")

                    # Get llm_mode from settings
                    llm_mode = config_settings.llm.mode

                    # Mapping of 'llm_mode' to corresponding model labels
                    model_mapping = {
                        "llamacpp": config_settings.llamacpp.llm_hf_model_file,
                        "openai": config_settings.openai.model,
                        "openailike": config_settings.openai.model,
                        "azopenai": config_settings.azopenai.llm_model,
                        "sagemaker": config_settings.sagemaker.llm_endpoint_name,
                        "mock": llm_mode,
                        "ollama": config_settings.ollama.llm_model,
                        "gemini": config_settings.gemini.model,
                    }

                    if llm_mode not in model_mapping:
                        print(f"Invalid 'llm mode': {llm_mode}")
                        return None

                    return model_mapping[llm_mode]
                model_label = get_model_label()
                if model_label is not None:
                    label_text = (
                        f"LLM: {settings().llm.mode} | Model: {model_label}"
                    )
                else:
                    label_text = f"LLM: {settings().llm.mode}"
                chatbot = gr.Chatbot(
                    label=label_text,
                    show_copy_button=True,
                    elem_id="chatbot",
                    render=False,
                    avatar_images=(None, AVATAR_BOT),
                )
                with gr.Column(scale=3):
                    # Toggle Button for Collapse
                    with gr.Accordion("Sidebar (Click to expand/collapse)", open=False):
                        gr.HTML(
                            """
                            <button id="collapseButton" class="collapse-btn">☰</button>
                            <script>
                                            window.addEventListener('DOMContentLoaded', (event) => {
                                                const collapseButton = document.getElementById('collapseButton');
                                                const leftPanel = document.querySelector('.left-panel');
                            
                                                collapseButton.addEventListener('click', function () {
                                                    if (leftPanel.classList.contains('collapsed')) {
                                                        leftPanel.classList.remove('collapsed');
                                                        collapseButton.innerHTML = '☰';
                                                    } else {
                                                        leftPanel.classList.add('collapsed');
                                                        collapseButton.innerHTML = '▶';
                                                    }
                                                });
                                            });
                            </script>
                                        """
                        )
                        default_mode = self._default_mode
                        mode = gr.Dropdown(
                            choices=[mode.value for mode in MODES],
                            label="Chat Mode",
                            value=default_mode.value,
                            interactive=True,
                            elem_id="dropdown-mode",
                        )
                        explanation_mode = gr.Textbox(
                            placeholder=self._get_default_mode_explanation(default_mode),
                            show_label=False,
                            max_lines=3,
                            interactive=False,
                        )
                        upload_button = gr.components.UploadButton(
                            "Upload File(s)",
                            type="filepath",
                            file_count="multiple",
                            size="sm",
                        )
                        ingested_dataset = gr.List(
                            self._list_ingested_files,
                            headers=["File name"],
                            label="Ingested Files",
                            height=235,
                            interactive=False,
                            render=False,  # Rendered under the button
                        )
                        upload_button.upload(
                            self._upload_file,
                            inputs=upload_button,
                            outputs=ingested_dataset,
                        )
                        ingested_dataset.change(
                            self._list_ingested_files,
                            outputs=ingested_dataset,
                        )
                        ingested_dataset.render()
                        deselect_file_button = gr.components.Button(
                            "De-select selected file", size="sm", interactive=False
                        )
                        selected_text = gr.components.Textbox(
                            "All files", label="Selected for Query or Deletion", max_lines=1
                        )
                        delete_file_button = gr.components.Button(
                            "🗑️ Delete selected file",
                            size="sm",
                            visible=settings().ui.delete_file_button_enabled,
                            interactive=False,
                        )
                        delete_files_button = gr.components.Button(
                            "⚠️ Delete ALL files",
                            size="sm",
                            visible=settings().ui.delete_all_files_button_enabled,
                        )
                        deselect_file_button.click(
                            self._deselect_selected_file,
                            outputs=[
                                delete_file_button,
                                deselect_file_button,
                                selected_text,
                            ],
                        )
                        ingested_dataset.select(
                            fn=self._selected_a_file,
                            outputs=[
                                delete_file_button,
                                deselect_file_button,
                                selected_text,
                            ],
                        )
                        delete_file_button.click(
                            self._delete_selected_file,
                            outputs=[
                                ingested_dataset,
                                delete_file_button,
                                deselect_file_button,
                                selected_text,
                            ],
                        )
                        delete_files_button.click(
                            self._delete_all_files,
                            outputs=[
                                ingested_dataset,
                                delete_file_button,
                                deselect_file_button,
                                selected_text,
                            ],
                        )
                        system_prompt_input = gr.Textbox(
                            placeholder=self._system_prompt,
                            label="System Prompt",
                            lines=2,
                            interactive=True,
                            render=False,
                        )
                        # When mode changes, set default system prompt, and other stuffs
                        mode.change(
                            self._set_current_mode,
                            inputs=mode,
                            outputs=[system_prompt_input, explanation_mode],
                        )
                        mode.change(
                            lambda selected_mode: [
                                [interaction[0], interaction[1] if len(interaction) > 1 else ""]
                                for interaction in self._history_cache.get(Modes(selected_mode), [])
                            ],
                            inputs=mode,
                            outputs=[chatbot],
                        )
                        # On blur, set system prompt to use in queries
                        system_prompt_input.blur(
                            self._set_system_prompt,
                            inputs=system_prompt_input,
                        )

                        

                with gr.Column(scale=7, elem_id="col"):
                    # Determine the model label based on the value of PGPT_PROFILES
                    

                    _ = gr.ChatInterface(
                        self._chat,
                        chatbot=chatbot,
                        additional_inputs=[mode, upload_button, system_prompt_input],
                    )
            with gr.Row():
                avatar_byte = AVATAR_BOT.read_bytes()
                f_base64 = f"data:image/png;base64,{base64.b64encode(avatar_byte).decode('utf-8')}"
                gr.HTML(
                    f"<div class='footer'><a class='footer-zylon-link' href='https://www.QGPT.com/'> Made at QGPT. ©2025 QGPT Payments Inc. <img class='footer-zylon-ico' src='{f_base64}' alt=Zylon></a></div>"
                )

        return blocks

    def get_ui_blocks(self) -> gr.Blocks:
        if self._ui_block is None:
            self._ui_block = self._build_ui_blocks()
        return self._ui_block

    def mount_in_app(self, app: FastAPI, path: str) -> None:
        blocks = self.get_ui_blocks()
        blocks.queue()
        logger.info("Mounting the gradio UI, at path=%s", path)
        gr.mount_gradio_app(app, blocks, path=path, favicon_path=AVATAR_BOT)


if __name__ == "__main__":
    ui = global_injector.get(PrivateGptUi)
    _blocks = ui.get_ui_blocks()
    _blocks.queue()
    _blocks.launch(debug=False, show_api=False)
